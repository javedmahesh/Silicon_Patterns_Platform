/** Presentation helpers. All accept null/undefined and degrade to an em dash. */

const DASH = "—";

export function fmtScore(n?: number | null, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return DASH;
  return n.toFixed(digits);
}

export function fmtInt(n?: number | null): string {
  if (n === null || n === undefined || Number.isNaN(n)) return DASH;
  return Math.round(n).toLocaleString("en-US");
}

export function fmtMult(n?: number | null): string {
  if (n === null || n === undefined || Number.isNaN(n)) return DASH;
  return `${n.toFixed(2)}×`;
}

export function fmtPct(n?: number | null, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return DASH;
  return `${(n * 100).toFixed(digits)}%`;
}

function parseDate(iso?: string | null): Date | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function fmtDate(iso?: string | null): string {
  const d = parseDate(iso);
  if (!d) return iso?.trim() || DASH;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function fmtDateTime(iso?: string | null): string {
  const d = parseDate(iso);
  if (!d) return iso?.trim() || DASH;
  return d.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtRelative(iso?: string | null): string {
  const d = parseDate(iso);
  if (!d) return iso?.trim() || DASH;
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 0) return fmtDate(iso);
  if (sec < 45) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 7) return `${day}d ago`;
  if (day < 30) return `${Math.round(day / 7)}w ago`;
  if (day < 365) return `${Math.round(day / 30)}mo ago`;
  return `${Math.round(day / 365)}y ago`;
}

/** "PRODUCT_COMPANY" -> "Product company"; leaves short grades (A+, A) intact. */
export function enumLabel(s?: string | null): string {
  if (!s || !s.trim()) return DASH;
  if (s.length <= 2) return s;
  const lower = s.replace(/_/g, " ").toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

/** 1–2 letter monogram from a company name (falls back to domain). */
export function monogram(name?: string | null, domain?: string | null): string {
  const src = (name && name.trim()) || (domain && domain.trim()) || "?";
  const parts = src
    .replace(/^https?:\/\//, "")
    .split(/[\s.\-_]+/)
    .filter(Boolean);
  if (parts.length >= 2) return (parts[0]![0]! + parts[1]![0]!).toUpperCase();
  return src.replace(/[^a-zA-Z0-9]/g, "").slice(0, 2).toUpperCase() || "?";
}

export function domainHref(domain?: string | null): string | null {
  if (!domain || !domain.trim()) return null;
  return /^https?:\/\//.test(domain) ? domain : `https://${domain}`;
}

export function fullName(first?: string | null, last?: string | null): string {
  const n = [first, last].filter((p) => p && p.trim()).join(" ").trim();
  return n || DASH;
}

/** A decision-maker's `location` is sometimes a JSON blob from the LinkedIn
 *  scraper (`{linkedinText, parsed:{text,…}}`) rather than a plain string.
 *  Surface a human-readable place, falling back to the raw value. */
export function cleanLocation(loc?: string | null): string {
  const raw = (loc ?? "").trim();
  if (!raw || raw[0] !== "{") return raw;
  try {
    const o = JSON.parse(raw);
    return (o?.parsed?.text || o?.linkedinText || "").trim();
  } catch {
    return "";
  }
}

export function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

/** Split a comma/semicolon/pipe separated string into trimmed tokens. */
export function splitList(s?: string | null): string[] {
  if (!s) return [];
  return s
    .split(/[,;|]/)
    .map((t) => t.trim())
    .filter(Boolean);
}
