import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "data", "funds-config.json")
OUTPUT_DIR = os.path.join(ROOT_DIR, "public", "data")
HOLDINGS_DIR = os.path.join(OUTPUT_DIR, "holdings")


def disable_proxies():
  for key in ["http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"]:
    os.environ.pop(key, None)
  os.environ["NO_PROXY"] = "*"


def safe_float(value) -> float:
  try:
    if value is None:
      return 0.0
    return float(str(value).replace("%", ""))
  except Exception:
    return 0.0


def safe_str(value) -> str:
  if value is None:
    return ""
  return str(value).strip()


def pick_first_str(payload: dict, keys: List[str]) -> str:
  for key in keys:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
      return value.strip()
  return ""


def load_config() -> List[dict]:
  with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    data = json.load(file)
  return data.get("funds", [])


def request_json(
  url: str,
  params: Optional[dict] = None,
  headers: Optional[dict] = None,
  timeout: int = 12,
  retries: int = 3,
) -> Optional[dict]:
  delay = 0.6
  session = requests.Session()
  try:
    session.get("https://fund.eastmoney.com/", headers=get_eastmoney_headers(), timeout=8)
  except Exception:
    pass
  for attempt in range(retries + 1):
    try:
      final_params = dict(params or {})
      final_params.setdefault("_", int(time.time() * 1000))
      merged_headers = get_eastmoney_headers()
      if headers:
        merged_headers.update(headers)
      resp = session.get(url, params=final_params, headers=merged_headers, timeout=timeout)
      resp.raise_for_status()
      try:
        payload = resp.json()
      except Exception:
        payload = json.loads(resp.text)
      if isinstance(payload, dict) and payload.get("Success") is False:
        raise RuntimeError(payload.get("ErrMsg") or payload.get("ErrorMessage") or "request failed")
      return payload
    except Exception:
      if attempt == retries:
        break
      time.sleep(delay)
      delay *= 1.6
  return None


def parse_jsonp(payload: str) -> Optional[dict]:
  match = re.search(r"jsonpgz\((\{.*\})\);", payload, re.S)
  if not match:
    return None
  try:
    return json.loads(match.group(1))
  except Exception:
    return None


def get_eastmoney_headers() -> dict:
  cookie = os.environ.get("EM_COOKIE", "")
  return {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://fund.eastmoney.com/",
    "Origin": "https://fund.eastmoney.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Connection": "keep-alive",
    "Cookie": cookie,
  }


def fetch_fund_gz(code: str) -> Optional[dict]:
  url = f"https://fundgz.1234567.com.cn/js/{code}.js"
  try:
    resp = requests.get(url, headers=get_eastmoney_headers(), timeout=10)
    resp.raise_for_status()
    return parse_jsonp(resp.text)
  except Exception:
    return None


def find_list_by_key(obj, key: str) -> Optional[list]:
  if isinstance(obj, dict):
    for k, v in obj.items():
      if k == key and isinstance(v, list):
        return v
      found = find_list_by_key(v, key)
      if found is not None:
        return found
  elif isinstance(obj, list):
    for item in obj:
      found = find_list_by_key(item, key)
      if found is not None:
        return found
  return None


def fetch_holdings(code: str) -> Tuple[List[dict], str]:
  url = "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition"
  params_list = [
    {"FCODE": code, "deviceid": "Wap", "plat": "Wap", "product": "EFund", "version": "2.0.0"},
  ]
  json_response = None
  for params in params_list:
    json_response = request_json(url, params=params, headers=get_eastmoney_headers())
    if json_response:
      break
  if not json_response:
    return [], ""
  data_root = json_response.get("data") if isinstance(json_response, dict) else None
  if isinstance(data_root, dict):
    stocks = find_list_by_key(data_root, "fundStocks") or []
    expansion = data_root.get("Expansion") or data_root.get("expansion") or ""
  else:
    stocks = find_list_by_key(json_response, "fundStocks") or []
    expansion = json_response.get("Expansion") if isinstance(json_response, dict) else ""
  if isinstance(expansion, dict):
    expansion = expansion.get("ENDDATE") or expansion.get("DATE") or expansion.get("date") or ""
  return stocks, safe_str(expansion)


def extract_nav_series(payload: dict) -> Tuple[List[dict], List[dict]]:
  unit_series: List[dict] = []
  acc_series: List[dict] = []
  if not payload:
    return unit_series, acc_series
  datas = payload.get("Datas") or payload.get("data") or payload.get("Data") or []
  if isinstance(datas, dict):
    datas = datas.get("Datas") or datas.get("data") or []
  if not isinstance(datas, list):
    datas = []
  for row in datas[:90]:
    if isinstance(row, dict):
      date = safe_str(row.get("FSRQ") or row.get("x"))
      unit = safe_float(row.get("DWJZ") or row.get("y"))
      acc = safe_float(row.get("LJJZ") or row.get("z") or row.get("JZZZL"))
      if date:
        unit_series.append({"date": date, "nav": unit})
        acc_series.append({"date": date, "nav": acc})
    elif isinstance(row, list) and len(row) >= 3:
      unit_series.append({"date": safe_str(row[0]), "nav": safe_float(row[1])})
      acc_series.append({"date": safe_str(row[0]), "nav": safe_float(row[2])})
  return unit_series, acc_series


def fetch_nav_series(code: str) -> Tuple[List[dict], List[dict]]:
  url = "https://fundmobapi.eastmoney.com/FundMApi/FundNetDiagram.ashx"
  params = {
    "FCODE": code,
    "RANGE": "y",
    "deviceid": "Wap",
    "plat": "Wap",
    "product": "EFund",
    "version": "2.0.0",
  }
  json_response = request_json(url, params=params, headers=get_eastmoney_headers())
  if not json_response:
    return [], []
  return extract_nav_series(json_response)


def fetch_fund_base_info(code: str) -> dict:
  url = "https://fundmobapi.eastmoney.com/FundMApi/FundBaseTypeInformation.ashx"
  params = {"FCODE": code, "deviceid": "Wap", "plat": "Wap", "product": "EFund", "version": "2.0.0"}
  json_response = request_json(url, params=params, headers=get_eastmoney_headers())
  return json_response or {}


def fetch_acc_yield_series(code: str) -> List[dict]:
  url = "https://dataapi.1234567.com.cn/dataapi/fund/FundVPageAcc"
  params = {"INDEXCODE": "000300", "CODE": code, "FCODE": code, "RANGE": "y", "deviceid": "Wap", "product": "EFund"}
  json_response = request_json(url, params=params, headers=get_eastmoney_headers())
  series: List[dict] = []
  if not json_response:
    return series
  datas = json_response.get("Data") or json_response.get("Datas") or []
  if isinstance(datas, dict):
    datas = datas.get("Datas") or datas.get("data") or []
  if not isinstance(datas, list):
    datas = []
  for row in datas[:90]:
    if isinstance(row, dict):
      date = safe_str(row.get("FSRQ") or row.get("x"))
      val = safe_float(row.get("ZDF") or row.get("y"))
      if date:
        series.append({"date": date, "value": val})
    elif isinstance(row, list) and len(row) >= 2:
      series.append({"date": safe_str(row[0]), "value": safe_float(row[1])})
  return series


def fetch_market_indices() -> List[dict]:
  url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
  params = {
    "fltt": "2",
    "fields": "f2,f3,f4,f12,f13,f14",
    "secids": "1.000001,0.399006",
  }
  json_response = request_json(url, params=params, headers=get_eastmoney_headers())
  if not json_response:
    return []
  data = json_response.get("data") or {}
  return data.get("diff") or []


def stock_secid(code: str) -> Optional[str]:
  if not code:
    return None
  code = code.strip()
  if code.isdigit() and len(code) == 6:
    if code.startswith("6"):
      return f"1.{code}"
    if code.startswith(("0", "3", "8")):
      return f"0.{code}"
  if code.isdigit() and len(code) == 5:
    return f"116.{code}"
  return None


def fetch_stock_quotes(codes: List[str]) -> Dict[str, dict]:
  result: Dict[str, dict] = {}
  secids = [stock_secid(code) for code in codes]
  secids = [secid for secid in secids if secid]
  if not secids:
    return result
  url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
  params = {
    "fields": "f1,f2,f3,f4,f12,f13,f14,f292",
    "fltt": "2",
    "secids": ",".join(secids),
    "deviceid": "Wap",
    "plat": "Wap",
    "product": "EFund",
    "version": "2.0.0",
    "Uid": "",
  }
  payload = request_json(url, params=params, headers=get_eastmoney_headers())
  if not payload:
    return result
  data = payload.get("data") or {}
  diff = data.get("diff") or []
  for row in diff:
    code = safe_str(row.get("f12"))
    if not code:
      continue
    result[code] = {
      "price": safe_float(row.get("f2")),
      "changePct": safe_float(row.get("f3")),
    }
  return result


def main():
  disable_proxies()
  os.makedirs(HOLDINGS_DIR, exist_ok=True)
  funds_config = load_config()
  fallback_names = {item["code"]: item.get("name", "") for item in funds_config}
  last_update = datetime.now().isoformat()

  summaries = []
  market_indices = fetch_market_indices()

  for fund in funds_config:
    code = str(fund["code"])
    holding_shares = float(fund.get("holdingAmount", 0))
    holding_profit = float(fund.get("holdingProfit", 0))

    gz_info = fetch_fund_gz(code) or {}
    base_info = fetch_fund_base_info(code) or {}
    fund_name = (
      safe_str(gz_info.get("name"))
      or pick_first_str(base_info, ["FUNDNAME", "SHORTNAME", "Name", "fundname"])
      or fallback_names.get(code, "")
      or code
    )

    holdings_raw, quarter_label = fetch_holdings(code)
    if not holdings_raw:
      holdings_raw = []

    holdings = []
    coverage = 0.0
    estimated_change_pct = 0.0

    stock_codes = [safe_str(row.get("GPDM")) for row in holdings_raw if safe_str(row.get("GPDM"))]
    stock_quotes = fetch_stock_quotes(stock_codes)

    for row in holdings_raw:
      stock_code = safe_str(row.get("GPDM"))
      weight = safe_float(row.get("JZBL"))
      coverage += weight
      quote = stock_quotes.get(stock_code, {})
      change_pct = safe_float(quote.get("changePct"))
      price = safe_float(quote.get("price"))
      contribution = weight * change_pct / 100
      estimated_change_pct += contribution
      holdings.append(
        {
          "code": stock_code,
          "name": safe_str(row.get("GPJC")),
          "weight": weight,
          "price": price,
          "changePct": change_pct,
          "contributionPct": contribution,
        }
      )

    if gz_info:
      estimated_change_pct = safe_float(gz_info.get("gszzl"))
    dwjz = safe_float(gz_info.get("dwjz")) if gz_info else 0.0
    estimated_change_amount = None
    total_profit = None

    unit_series, acc_series = fetch_nav_series(code)
    acc_yield_series = fetch_acc_yield_series(code)

    est_series = list(unit_series)
    if gz_info and safe_float(gz_info.get("gsz")) > 0:
      est_date = safe_str(gz_info.get("gztime")).split(" ")[0] or datetime.now().date().isoformat()
      if est_series and est_series[-1]["date"] == est_date:
        est_series[-1]["nav"] = safe_float(gz_info.get("gsz"))
      else:
        est_series.append({"date": est_date, "nav": safe_float(gz_info.get("gsz"))})

    detail_payload = {
      "code": code,
      "name": fund_name,
      "holdingsQuarter": quarter_label,
      "holdingsCoverage": round(coverage, 2),
      "estimatedChangePct": round(estimated_change_pct, 3),
      "estimatedChangeAmount": estimated_change_amount,
      "totalProfit": total_profit,
      "holdings": holdings,
      "navSeriesUnit": unit_series,
      "navSeriesAcc": acc_series,
      "navSeriesEst": est_series,
      "accYieldSeries": acc_yield_series,
      "latestNav": dwjz,
      "latestNavDate": safe_str(gz_info.get("jzrq")) if gz_info else "",
      "estNav": safe_float(gz_info.get("gsz")) if gz_info else 0.0,
      "estNavTime": safe_str(gz_info.get("gztime")) if gz_info else "",
      "lastUpdate": last_update,
    }

    with open(os.path.join(HOLDINGS_DIR, f"{code}.json"), "w", encoding="utf-8") as file:
      json.dump(detail_payload, file, ensure_ascii=False, indent=2)

    summaries.append(
      {
        "code": code,
        "name": fund_name,
        "holdingAmount": holding_shares,
        "holdingProfit": holding_profit,
        "estimatedChangePct": round(estimated_change_pct, 3),
        "estimatedChangeAmount": estimated_change_amount,
        "totalProfit": total_profit,
        "holdingsCoverage": round(coverage, 2),
        "holdingsQuarter": quarter_label,
        "latestNav": safe_float(gz_info.get("dwjz")) if gz_info else 0.0,
        "latestNavDate": safe_str(gz_info.get("jzrq")) if gz_info else "",
        "estNav": safe_float(gz_info.get("gsz")) if gz_info else 0.0,
        "estNavTime": safe_str(gz_info.get("gztime")) if gz_info else "",
        "lastUpdate": last_update,
      }
    )

  with open(os.path.join(OUTPUT_DIR, "funds.json"), "w", encoding="utf-8") as file:
    json.dump(
      {"updatedAt": last_update, "funds": summaries, "market": market_indices},
      file,
      ensure_ascii=False,
      indent=2,
    )


if __name__ == "__main__":
  main()
