/**
 * Typed fetch wrapper with timeout, JSON handling, and error normalization.
 * Uses native fetch + AbortController.
 */

export const BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ??
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

type ApiFetchInit = RequestInit & {
  /** Override timeout in ms (default 8000). */
  timeoutMs?: number;
};

/**
 * Typed fetch helper.
 * - Aborts after timeoutMs (default 8000ms) via AbortController.
 * - Merges caller-provided AbortSignal (supports rapid-click abort).
 * - Prepends BASE_URL to path.
 * - Sets Content-Type: application/json when body present and no explicit header.
 * - Normalizes error shape {detail} → throws ApiError / Error.
 * - Parses JSON and returns typed result.
 */
export async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T> {
  const timeoutMs = init?.timeoutMs ?? 8000;
  const { timeoutMs: _ignored, ...restInit } = init ?? {};

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  // Bridge external signal → internal controller
  let onExternalAbort: (() => void) | undefined;
  const externalSignal = restInit.signal as AbortSignal | undefined | null;
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      onExternalAbort = () => controller.abort();
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  const url = `${BASE_URL}${path}`;

  const headers = new Headers(restInit.headers as HeadersInit | undefined);
  // Default JSON content type for non-GET with body, without overriding caller headers
  if (!headers.has("Content-Type") && restInit.body != null) {
    headers.set("Content-Type", "application/json");
  }
  // Always request JSON
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }

  try {
    const response = await fetch(url, {
      ...restInit,
      headers,
      signal: controller.signal,
    });

    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");

    let body: unknown = null;
    if (isJson) {
      const text = await response.text();
      if (text.length > 0) {
        try {
          body = JSON.parse(text) as unknown;
        } catch {
          // Malformed JSON on error path — treat as text detail
          body = { detail: text };
        }
      }
    } else {
      // Non-JSON: read as text for error detail, otherwise ignore
      const text = await response.text().catch(() => "");
      if (text) body = { detail: text };
    }

    if (!response.ok) {
      const detail =
        body != null && typeof body === "object" && "detail" in (body as Record<string, unknown>)
          ? String((body as Record<string, unknown>).detail)
          : `Request failed with status ${response.status}`;
      throw new ApiError(response.status, detail);
    }

    // 204 No Content
    if (response.status === 204 || body == null) {
      return undefined as unknown as T;
    }

    return body as T;
  } catch (err) {
    // Preserve ApiError, AbortError, and typed Errors as-is; normalize unknown
    if (err instanceof ApiError) throw err;
    if (err instanceof Error) throw err;
    throw new Error(String(err));
  } finally {
    clearTimeout(timeout);
    if (externalSignal && onExternalAbort) {
      externalSignal.removeEventListener("abort", onExternalAbort);
    }
  }
}
