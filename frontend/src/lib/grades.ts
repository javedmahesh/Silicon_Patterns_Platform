export type Grade = "A+" | "A" | "B" | "C";

export const GRADES: Grade[] = ["A+", "A", "B", "C"];

/** Grade-band thresholds mirror config/lead_scoring.json (A+ >=70, A >=50, B >=30). */
export const GRADE_BANDS: Record<Grade, number> = { "A+": 70, A: 50, B: 30, C: 0 };

/** CSS var() for a grade color — use in inline styles / chart fills. */
export function gradeVar(grade?: string | null): string {
  switch (grade) {
    case "A+":
      return "var(--color-grade-aplus)";
    case "A":
      return "var(--color-grade-a)";
    case "B":
      return "var(--color-grade-b)";
    case "C":
      return "var(--color-grade-c)";
    default:
      return "var(--color-fg-subtle)";
  }
}

export function gradeLabel(grade?: string | null): string {
  return grade && grade.trim() ? grade : "—";
}

/** Literal hex per grade — for SVG/Recharts fills (which don't resolve CSS vars). */
export const GRADE_HEX: Record<string, string> = {
  "A+": "#3fb68b",
  A: "#5aa9e6",
  B: "#d2a33b",
  C: "#6b7785",
};

export function gradeHex(grade?: string | null): string {
  return (grade && GRADE_HEX[grade]) || "#6b7785";
}

/** Score (0–100) -> grade var, for coloring score bars when no grade is present. */
export function scoreVar(score?: number | null): string {
  if (score === null || score === undefined) return "var(--color-fg-subtle)";
  if (score >= GRADE_BANDS["A+"]) return "var(--color-grade-aplus)";
  if (score >= GRADE_BANDS.A) return "var(--color-grade-a)";
  if (score >= GRADE_BANDS.B) return "var(--color-grade-b)";
  return "var(--color-grade-c)";
}
