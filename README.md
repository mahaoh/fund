# fund

一个基于 Vue 3 + Vite 的基金 H5 看板，数据由 GitHub Actions 每 30 分钟更新一次，前端读取静态 JSON。

## 功能

- 基金列表：展示持有金额、累计收益、今日估算涨跌与收益
- 基金详情：净值走势图（单位/累计/估算可切换）+ 持仓股票涨跌幅与占比
- 手动刷新按钮（前端重新拉取最新 JSON）

## 数据配置

编辑 `data/funds-config.json`：

```json
{
  "funds": [
    {
      "code": "161725",
      "name": "招商中证白酒指数",
      "holdingAmount": 50000,
      "holdingProfit": 3200
    }
  ]
}
```

## 本地开发

```bash
npm install
npm run dev
```

## 本地生成数据

```bash
python3 -m pip install requests
python3 scripts/update_data.py
```

## 数据更新

- GitHub Actions：`.github/workflows/update-data.yml`
- 脚本入口：`scripts/update_data.py`
- 生成数据：`public/data/funds.json`、`public/data/holdings/*.json`

## 数据源

- 估算净值：`https://fundgz.1234567.com.cn/js/<基金代码>.js`
- 持仓、净值走势：`https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition` 与 `FundMNHisNetList`
