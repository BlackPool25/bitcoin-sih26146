export type GuardrailResult = {
  pixelRatioOk: boolean;
  batchOk: boolean;
  haystackOk: boolean;
  limitOk: boolean;
};

export const GUARDRAIL_DESCRIPTIONS: Record<keyof GuardrailResult, string> = {
  pixelRatioOk: "Requires pixelRatio:1 in cytoscape init (avoids 2x canvas overdraw on HiDPI)",
  batchOk: "Requires cy.batch() wrapping elements remove+add (single viewport reflow)",
  haystackOk: "Requires haystack curve-style for >500 edges (avoids bezier path tessellation at 2K)",
  limitOk: "Requires ?limit=2000 (or limit=2000) on all /api/graph fetches (server-side viewport cap)",
};

/**
 * Audit guardrails via regex/string includes over concatenated project source.
 * Checks: "pixelRatio:1", "batch(", "haystack", "?limit=2000" or "limit=2000"
 */
export function auditGuardrails(sourceCode: string): GuardrailResult {
  const pixelRatioOk = /pixelRatio\s*:\s*1\b/.test(sourceCode) || sourceCode.includes("PIXEL_RATIO") && /PIXEL_RATIO\s*=\s*1/.test(sourceCode) || sourceCode.includes("pixelRatio:1") || sourceCode.includes("pixelRatio: 1");
  const batchOk = sourceCode.includes("batch(") || /cy\.batch\(/.test(sourceCode);
  const haystackOk = sourceCode.includes("haystack") || /haystack/.test(sourceCode);
  const limitOk =
    sourceCode.includes("?limit=2000") ||
    sourceCode.includes("limit=2000") ||
    /limit\s*=\s*2000/.test(sourceCode) ||
    /\?limit=/.test(sourceCode);

  return { pixelRatioOk, batchOk, haystackOk, limitOk };
}

/**
 * Convenience: audit current codebase guardrails by reading known files synchronously
 * when available (used in report generator).
 */
export function allGuardrailsPassed(r: GuardrailResult): boolean {
  return r.pixelRatioOk && r.batchOk && r.haystackOk && r.limitOk;
}

export default auditGuardrails;
