/**
 * Alerts + Evidence typed API with mock fallback.
 * - listAlerts: GET /api/alerts with limit/sort/tier/q/offset
 * - getEvidence: GET /api/evidence/{id}
 * Fallback to mocks on 404 / timeout / network error (console.warn).
 */

import { apiFetch } from "./client";
import type { Alert, Evidence, Tier } from "@/types/alert";
import { tierFromP as tierFromPBase } from "@/types/alert";
import { getMockAlerts } from "@/mocks/alerts.mock";
import { getMockEvidence } from "@/mocks/evidence.mock";

// ---------------------------------------------------------------------------
// Re-exports / aliases required by spec
// ---------------------------------------------------------------------------

export type AlertTier = Tier;
export type { Alert, Evidence };

/**
 * Derive tier from model probability p (0-1).
 * Re-export canonical helper for spec compliance.
 */
export const tierFromP = tierFromPBase;

// ---------------------------------------------------------------------------
// Params
// ---------------------------------------------------------------------------

export interface ListAlertsParams {
  limit?: number;
  offset?: number;
  sort?: string;
  tier?: AlertTier;
  q?: string;
}

export interface EvidenceParams {
  id: string;
}

// Internal shape mirrors openapi.yaml /api/alerts 200 response
interface ListAlertsResponse {
  alerts: Alert[];
  count: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isAbortError(err: unknown): boolean {
  return (
    err instanceof DOMException && err.name === "AbortError" ||
    (err instanceof Error && err.name === "AbortError")
  );
}

function buildAlertsQuery(params: ListAlertsParams): string {
  const sp = new URLSearchParams();
  // mirror openapi defaults: limit 50, sort p, offset 0
  if (params.limit !== undefined) sp.set("limit", String(params.limit));
  else sp.set("limit", "50");
  if (params.offset !== undefined) sp.set("offset", String(params.offset));
  if (params.sort !== undefined) sp.set("sort", params.sort);
  if (params.tier !== undefined) sp.set("tier", params.tier);
  if (params.q !== undefined && params.q.length > 0) sp.set("q", params.q);
  const qs = sp.toString();
  return qs ? `?${qs}` : "";
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * List ranked alerts. Falls back to getMockAlerts on 404 / timeout / network error.
 * Supports AbortSignal via params signal (passed through init).
 */
export async function listAlerts(
  params: ListAlertsParams = {},
  init?: { signal?: AbortSignal },
): Promise<ListAlertsResponse> {
  const qs = buildAlertsQuery(params);
  const path = `/api/alerts${qs}`;

  try {
    const raw = await apiFetch<unknown>(path, { signal: init?.signal });

    // API may return wrapped object or bare array (legacy mockFetch)
    if (Array.isArray(raw)) {
      const alerts = raw as Alert[];
      return {
        alerts,
        count: alerts.length,
        limit: params.limit ?? 50,
        offset: params.offset ?? 0,
      };
    }

    const data = raw as Partial<ListAlertsResponse> & { alerts?: Alert[] };
    if (data && Array.isArray(data.alerts)) {
      return {
        alerts: data.alerts,
        count: typeof data.count === "number" ? data.count : data.alerts.length,
        limit: typeof data.limit === "number" ? data.limit : (params.limit ?? 50),
        offset: typeof data.offset === "number" ? data.offset : (params.offset ?? 0),
      };
    }

    // Unexpected shape → fallback
    throw new Error("Unexpected /api/alerts response shape");
  } catch (err) {
    if (isAbortError(err)) throw err;
    // eslint-disable-next-line no-console
    console.warn(`[api] fallback to mock alerts for ${path}:`, err instanceof Error ? err.message : String(err));
    const mock = getMockAlerts(params);
    return {
      alerts: mock.alerts,
      count: mock.count,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    };
  }
}

/**
 * Get evidence for alert id. Falls back to getMockEvidence on 404 / timeout / network error.
 * Supports AbortSignal for rapid-click abort (S-EDGE-07).
 */
export async function getEvidence(
  id: string,
  signal?: AbortSignal,
): Promise<Evidence> {
  const path = `/api/evidence/${encodeURIComponent(id)}`;
  try {
    const data = await apiFetch<Evidence>(path, { signal });
    return data;
  } catch (err) {
    if (isAbortError(err)) throw err;
    // eslint-disable-next-line no-console
    console.warn(`[api] fallback to mock evidence for ${id}:`, err instanceof Error ? err.message : String(err));
    const mock = getMockEvidence(id);
    if (mock) return mock;
    // Preserve original error semantics if no mock found
    throw err;
  }
}
