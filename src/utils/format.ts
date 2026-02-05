export const formatNumber = (value: number | null | undefined, digits = 2) => {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  if (!Number.isFinite(value)) return "-";
  return value.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
};

export const formatSigned = (value: number, digits = 2) => {
  const sign = value > 0 ? "+" : value < 0 ? "" : "";
  return `${sign}${formatNumber(value, digits)}`;
};

export const percentClass = (value: number) =>
  value >= 0 ? "positive" : "negative";
