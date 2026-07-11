/** Literal hex tokens for Recharts (SVG fills don't resolve CSS custom properties). */
export const CHART = {
  grid: "#1c232c",
  axis: "#262e38",
  tick: "#97a3b2",
  tickFaint: "#5c6878",
  accent: "#4c9aed",
  tooltipBg: "#161b22",
  tooltipBorder: "#262e38",
  text: "#e7ecf2",
} as const;

export const tooltipStyle = {
  background: CHART.tooltipBg,
  border: `1px solid ${CHART.tooltipBorder}`,
  borderRadius: 6,
  fontSize: 12,
  color: CHART.text,
  padding: "6px 8px",
} as const;

export const tooltipLabelStyle = { color: CHART.tick } as const;
