<template>
  <section class="glass card">
    <div class="topbar" style="margin-bottom: 8px;">
      <div>
        <div class="badge">{{ detail?.code || code }}</div>
        <div class="value">{{ detail?.name || "加载中" }}</div>
        <div class="meta">披露季度：{{ detail?.holdingsQuarter || "-" }}</div>
      </div>
      <button class="icon-btn" @click="refresh" aria-label="刷新">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M20 12a8 8 0 1 1-2.34-5.66" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M20 4v6h-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <div class="split">
      <span>今日估算涨跌</span>
      <span :class="percentClass(detail?.estimatedChangePct || 0) + ' mono'">
        {{ formatSigned(detail?.estimatedChangePct || 0, 2) }}%
      </span>
    </div>
    <div class="split">
      <span>今日估算收益</span>
      <span :class="percentClass(detail?.estimatedChangeAmount || 0)">
        {{ formatSigned(detail?.estimatedChangeAmount || 0, 2) }} 元
      </span>
    </div>
    <div class="split">
      <span>持仓覆盖率</span>
      <span>{{ formatNumber(detail?.holdingsCoverage || 0, 2) }}%</span>
    </div>
  </section>

  <section class="section">
    <h2>持仓股票</h2>
    <div v-if="loading" class="empty glass">数据加载中...</div>
    <div v-else-if="error" class="empty glass">{{ error }}</div>
    <div v-else class="table">
      <div class="row header">
        <span>股票</span>
        <span>占比</span>
        <span>涨跌幅</span>
      </div>
      <div v-for="stock in detail?.holdings || []" :key="stock.code" class="row">
        <span>{{ stock.name }} ({{ stock.code }})</span>
        <span class="mono">{{ formatNumber(stock.weight, 2) }}%</span>
        <span :class="percentClass(stock.changePct) + ' mono'">
          {{ formatSigned(stock.changePct, 2) }}%
        </span>
      </div>
    </div>
  </section>

  <div class="footer-note">
    数据更新时间：{{ detail?.lastUpdate ? new Date(detail.lastUpdate).toLocaleString() : "-" }}
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { formatNumber, formatSigned, percentClass } from "../utils/format";
// Data will be loaded from static json.

interface HoldingItem {
  code: string;
  name: string;
  weight: number;
  price: number;
  changePct: number;
  contributionPct: number;
}

interface FundDetail {
  code: string;
  name: string;
  holdingsQuarter: string;
  holdingsCoverage: number;
  estimatedChangePct: number;
  estimatedChangeAmount: number;
  holdings: HoldingItem[];
  lastUpdate: string;
}

const props = defineProps<{ code: string }>();
const code = props.code;

const detail = ref<FundDetail | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const loadData = async () => {
  loading.value = true;
  error.value = null;
  try {

    const res = await fetch(`/data/holdings/${code}.json?ts=${Date.now()}`);
    if (!res.ok) throw new Error("详情数据拉取失败");
    const data = await res.json();
    detail.value = {
      code: data.code || code,
      name: data.name || code,
      holdingsQuarter: data.holdingsQuarter || "",
      holdingsCoverage: data.holdingsCoverage || 0,
      estimatedChangePct: data.estimatedChangePct || 0,
      estimatedChangeAmount: data.estimatedChangeAmount || 0,
      holdings: data.holdings || [],
      lastUpdate: data.lastUpdate || new Date().toISOString(),
    };
  } catch (err) {
    error.value = err instanceof Error ? err.message : "未知错误";
  } finally {
    loading.value = false;
  }
};

const refresh = () => loadData();

onMounted(() => {
  loadData();
});
</script>
