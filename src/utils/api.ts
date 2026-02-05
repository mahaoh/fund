import axios from "axios";
import { fetchFundGzJsonp } from "./jsonp";

export interface FundGz {
  fundcode: string;
  name: string;
  jzrq: string;
  dwjz: string;
  gsz: string;
  gszzl: string;
  gztime: string;
}

export interface MarketIndex {
  code: string;
  name: string;
  price: number;
  changePct: number;
  change: number;
}

export interface HoldingStock {
  code: string;
  name: string;
  weight: number;
  price: number;
  changePct: number;
}

const baseHeaders = {
  "Accept": "application/json, text/plain, */*",
};

const toNumber = (value: any) => {
  const num = Number(String(value ?? "").replace("%", ""));
  return Number.isFinite(num) ? num : 0;
};

export const getFundGz = async (code: string): Promise<FundGz> => {
  const data = await fetchFundGzJsonp(code);
  return data as FundGz;
};

export const getMarket = async (): Promise<MarketIndex[]> => {
  const res = await axios.get("https://push2.eastmoney.com/api/qt/ulist.np/get", {
    params: {
      fltt: 2,
      fields: "f2,f3,f4,f12,f13,f14",
      secids: "1.000001,0.399006",
      _: Date.now(),
    },
    headers: baseHeaders,
  });
  const diff = res.data?.data?.diff ?? [];
  return diff.map((row: any) => ({
    code: String(row.f12),
    name: String(row.f14),
    price: toNumber(row.f2),
    changePct: toNumber(row.f3),
    change: toNumber(row.f4),
  }));
};

export const getFundHoldings = async (code: string): Promise<HoldingStock[]> => {
  const res = await axios.get("https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition", {
    params: {
      FCODE: code,
      deviceid: "Wap",
      plat: "Wap",
      product: "EFund",
      version: "2.0.0",
      Uid: "",
      _: Date.now(),
    },
    headers: baseHeaders,
  });

  const fundStocks =
    res.data?.Datas?.fundStocks ??[];
  const codes = fundStocks.map((item: any) => String(item.GPDM));
  const quotes = await getStockQuotes(codes);

  return fundStocks.map((item: any) => {
    const code = String(item.GPDM);
    const quote = quotes[code] || { price: 0, changePct: 0 };
    return {
      code,
      name: String(item.GPJC),
      weight: toNumber(item.JZBL),
      price: quote.price,
      changePct: quote.changePct,
    } as HoldingStock;
  });
};

const toSecid = (code: string) => {
  if (/^6\d{5}$/.test(code)) return `1.${code}`;
  if (/^[03]\d{5}$/.test(code)) return `0.${code}`;
  if (/^8\d{5}$/.test(code)) return `0.${code}`;
  if (/^\d{5}$/.test(code)) return `116.${code}`;
  return "";
};

export const getStockQuotes = async (codes: string[]) => {
  const secids = codes.map(toSecid).filter(Boolean).join(",");
  if (!secids) return {} as Record<string, { price: number; changePct: number }>;

  const res = await axios.get("https://push2.eastmoney.com/api/qt/ulist.np/get", {
    params: {
      fields: "f1,f2,f3,f4,f12,f13,f14,f292",
      fltt: 2,
      secids,
      deviceid: "Wap",
      plat: "Wap",
      product: "EFund",
      version: "2.0.0",
      Uid: "",
      _: Date.now(),
    },
    headers: baseHeaders,
  });

  const diff = res.data?.data?.diff ?? [];
  const map: Record<string, { price: number; changePct: number }> = {};
  diff.forEach((row: any) => {
    const code = String(row.f12);
    map[code] = { price: toNumber(row.f2), changePct: toNumber(row.f3) };
  });
  return map;
};

// Net value history removed per requirement.
