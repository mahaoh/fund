<template>
  <div class="topbar" style="margin-bottom: 12px;">
    <div>
      <div class="badge">30分钟自动更新</div>
      <div class="meta">最后更新：{{ updatedAtText }}</div>
    </div>
    <button class="icon-btn" @click="refresh" aria-label="刷新">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path d="M20 12a8 8 0 1 1-2.34-5.66" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        <path d="M20 4v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>
  </div>
  <div v-if="loading" class="empty glass">正在加载最新数据...</div>
  <div v-else-if="error" class="empty glass">{{ error }}</div>

  <section class="section">
    <div class="grid">
      <div class="glass card">
        <div class="badge">大盘</div>
        <div class="table" style="margin-top: 10px;">
          <div v-for="item in marketCards" :key="item.code" class="row" style="grid-template-columns: 1fr 1fr 1fr;">
            <span>{{ item.name }}</span>
            <span class="mono">{{ formatNumber(item.price, 2) }}</span>
            <span :class="percentClass(item.changePct) + ' mono'">{{ formatSigned(item.changePct, 2) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <h2>基金列表</h2>
    <div v-if="!loading && funds.length === 0" class="empty glass">
      暂无数据，请先运行数据更新脚本或等待 GitHub Actions。
    </div>
    <div class="grid">
      <router-link
        v-for="fund in funds"
        :key="fund.code"
        :to="`/fund/${fund.code}`"
        class="glass card"
      >
        <div class="value">{{ fund.name || "未知基金" }}</div>
        <div class="split">
          <span>持有金额</span>
          <span class="mono">{{ formatNumber(fund.holdingAmount, 2) }}</span>
        </div>
        <div class="split">
          <span>今日估算涨跌</span>
          <span :class="percentClass(fund.estimatedChangePct) + ' mono'">
            {{ formatSigned(fund.estimatedChangePct, 2) }}%
          </span>
        </div>
        <div class="split">
          <span>最新净值</span>
          <span class="mono">{{ formatNumber(fund.latestNav, 4) }} ({{ fund.latestNavDate || "-" }})</span>
        </div>
        <div class="split">
          <span>估算净值</span>
          <span class="mono">{{ formatNumber(fund.estNav, 4) }} ({{ fund.estNavTime || "-" }})</span>
        </div>
      </router-link>
    </div>
  </section>

  <div class="footer-note">
    估算涨跌来源于持仓股票当日涨跌幅加权计算，仅供参考。
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { formatNumber, formatSigned, percentClass } from "../utils/format";

interface FundSummary {
  code: string;
  name: string;
  holdingAmount: number;
  holdingProfit: number;
  estimatedChangePct: number;
  estimatedChangeAmount: number | null;
  holdingsCoverage: number;
  holdingsQuarter: string;
  latestNav: number;
  latestNavDate: string;
  estNav: number;
  estNavTime: string;
  lastUpdate: string;
}

const funds = ref<FundSummary[]>([]);
const market = ref<any[]>([]);
const updatedAt = ref<string>("");
const loading = ref(true);
const error = ref<string | null>(null);
const updatedAtText = computed(() => {
  if (!updatedAt.value) return "-";
  return new Date(updatedAt.value).toLocaleString();
});

const toNumber = (value: unknown) => {
  if (value === null || value === undefined) return 0;
  const cleaned = String(value).replace(/,/g, "");
  const num = Number(cleaned);
  return Number.isFinite(num) ? num : 0;
};

const marketCards = computed(() => {
  const wanted = new Set(["000001", "399006"]);
  return (market.value || [])
    .filter((item) => wanted.has(String(item.f12 ?? item.code)))
    .map((item) => ({
      code: String(item.f12 ?? item.code),
      name: String(item.f14 ?? item.name),
      price: toNumber(item.f2 ?? item.price),
      change: toNumber(item.f4 ?? item.change),
      changePct: toNumber(item.f3 ?? item.changePct),
    }));
});



const loadData = async () => {
  loading.value = true;
  error.value = null;
  try {
    const res = await fetch(`/data/funds.json?ts=${Date.now()}`);
    if (!res.ok) throw new Error("数据拉取失败");
    const data = await res.json();
    funds.value = Array.isArray(data) ? data : data.funds || [];
    if (Array.isArray(data.market)) {
      
      market.value = data.market;
    } else if (Array.isArray(data.market?.diff)) {
      market.value = data.market.diff;
    } else {
      market.value = [];
    }
    updatedAt.value = data.updatedAt || "";
  } catch (err) {
    error.value = err instanceof Error ? err.message : "未知错误";
  } finally {
    loading.value = false;
  }
};

const refresh = () => {
  loadData();
};

loadData();
</script>
