export function currency(value: string | number | null | undefined, compact = false): string {
  const amount = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: compact ? 1 : 2,
    notation: compact ? "compact" : "standard",
  }).format(amount);
}

export function number(value: string | number | null | undefined): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 }).format(Number(value ?? 0));
}

export function percent(value: string | number | null | undefined): string {
  return `${Number(value ?? 0).toFixed(1)}%`;
}

export function label(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}
