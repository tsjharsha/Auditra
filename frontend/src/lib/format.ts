export function pct(value?: number | null, digits = 1) {
  return `${((value ?? 0) * 100).toFixed(digits)}%`;
}

export function money(value?: string | number | null, currency = "INR") {
  if (value === undefined || value === null || value === "") return "-";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `${currency} ${String(value)}`;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(numeric);
}

export function compact(value?: string | number | null) {
  if (value === undefined || value === null || value === "") return "-";
  if (typeof value === "number") return new Intl.NumberFormat("en-IN").format(value);
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat("en-IN").format(numeric) : value;
}

export function ms(value?: number | null) {
  return `${Number(value ?? 0).toFixed(2)} ms`;
}

export function titleCase(value: string) {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function shortId(value?: string | null, length = 18) {
  if (!value) return "-";
  return value.length > length ? `${value.slice(0, length - 1)}...` : value;
}

export function jsonPreview(value: unknown, length = 360) {
  const text = JSON.stringify(value ?? {}, null, 2);
  return text.length > length ? `${text.slice(0, length)}...` : text;
}
