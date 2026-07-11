export type ClassValue = string | number | false | null | undefined;

/** Tiny classnames joiner — filters falsy values and joins with spaces. */
export function cx(...parts: ClassValue[]): string {
  return parts.filter(Boolean).join(" ");
}
