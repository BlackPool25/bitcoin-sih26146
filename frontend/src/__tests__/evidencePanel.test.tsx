import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import EvidencePanel from "@/components/EvidencePanel";
import * as alertsApi from "@/api/alerts";
import type { Evidence } from "@/types/alert";

// Mock recharts ResponsiveContainer to render children directly (jsdom has no layout)
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  const MockResponsive: React.FC<{ children: React.ReactNode }> = ({ children }) => (
    <div data-testid="mock-responsive">{children}</div>
  );
  return {
    ...actual,
    ResponsiveContainer: MockResponsive,
  };
});

const mockEvidence: Evidence = {
  alert_id: "a".repeat(64),
  p: 0.95,
  tier: "critical",
  shap: {
    fan_in: 0.45,
    mixer_score: -0.32,
    burst_5m_count: 0.28,
    fee_sat_per_vb: -0.15,
    geo_distance_variance_km: 0.1,
  },
  top_shap: ["fan_in", "mixer_score", "burst_5m_count"],
  nl: "Wallet bc1qaaa flagged: fan_in — conf 0.95 (fan_in+mixer_score+burst_5m_count)",
  geo_timeline: [
    { country: "US", ts: new Date().toISOString(), asn: 15169, lat: 39.8, lng: -98.5, radius: 120 },
    { country: "CN", ts: new Date().toISOString(), asn: 4134, lat: 35.8, lng: 104, radius: 80 },
  ],
  amount_flow: [
    { ts: new Date().toISOString(), amount: 1.2 },
    { ts: new Date().toISOString(), amount: 2.1 },
  ],
  temporal_burst: [
    { bucket: "0-5m", count: 12 },
    { bucket: "5-10m", count: 3 },
  ],
  accuracy_hint: { radius_km: 250, is_hint: true },
  geo_inconsistent: true,
};

describe("EvidencePanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("null placeholder shows Select an alert and data-state empty", () => {
    render(<EvidencePanel alertId={null} />);
    const panel = screen.getByTestId("evidence-panel");
    expect(panel).toBeInTheDocument();
    expect(panel.getAttribute("data-state")).toBe("empty");
    expect(screen.getByText(/Select an alert to view evidence/i)).toBeInTheDocument();
  });

  it("selectedAlertId alias also triggers placeholder when null", () => {
    render(<EvidencePanel selectedAlertId={null} />);
    expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("empty");
  });

  it("loading state shows data-state loading with skeletons", async () => {
    let resolve!: (v: Evidence) => void;
    const hanging = new Promise<Evidence>((r) => {
      resolve = r;
    });
    const spy = vi.spyOn(alertsApi, "getEvidence").mockReturnValue(hanging as unknown as never);

    render(<EvidencePanel alertId={"a".repeat(64)} />);

    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("loading"));
    expect(screen.getByText(/Loading evidence/)).toBeInTheDocument();

    resolve(mockEvidence);
    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("loaded"));
    spy.mockRestore();
  });

  it("loading→evidence: shows SHAP, nl, accuracy hint, geo_inconsistent", async () => {
    const spy = vi.spyOn(alertsApi, "getEvidence").mockResolvedValue(mockEvidence);
    render(<EvidencePanel alertId={"a".repeat(64)} />);
    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("loaded"));
    expect(screen.getByText(/Wallet bc1qaaa flagged/)).toBeInTheDocument();
    expect(screen.getByText(/SHAP waterfall/)).toBeInTheDocument();
    expect(screen.getByText(/Amount flow/)).toBeInTheDocument();
    expect(screen.getByText(/Geo timeline/)).toBeInTheDocument();
    expect(screen.getByText(/Temporal burst/)).toBeInTheDocument();
    const hint = screen.getByTestId("accuracy-hint");
    expect(hint).toBeInTheDocument();
    expect(hint.textContent).toContain("250km");
    expect(hint.textContent).toContain("area not point");
    expect(screen.getByText(/Geo inconsistent/)).toBeInTheDocument();
    expect(screen.getByText(/flagged/)).toBeInTheDocument();
    spy.mockRestore();
  });

  it("error retry: shows error and Retry triggers refetch", async () => {
    const spy = vi
      .spyOn(alertsApi, "getEvidence")
      .mockRejectedValueOnce(new Error("Network down"))
      .mockResolvedValueOnce(mockEvidence);
    render(<EvidencePanel alertId={"b".repeat(64)} />);
    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("error"));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Network down/)).toBeInTheDocument();
    const retry = screen.getByRole("button", { name: /Retry/i });
    fireEvent.click(retry);
    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("loaded"));
    expect(screen.getByText(/Wallet bc1qaaa flagged/)).toBeInTheDocument();
    spy.mockRestore();
  });

  it("accuracy_hint not shown when is_hint false", async () => {
    const withoutHint: Evidence = { ...mockEvidence, accuracy_hint: { radius_km: 10, is_hint: false } };
    const spy = vi.spyOn(alertsApi, "getEvidence").mockResolvedValue(withoutHint);
    render(<EvidencePanel alertId={"c".repeat(64)} />);
    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("loaded"));
    expect(screen.queryByTestId("accuracy-hint")).not.toBeInTheDocument();
    spy.mockRestore();
  });

  it("clears evidence when alertId becomes null (reset)", async () => {
    const spy = vi.spyOn(alertsApi, "getEvidence").mockResolvedValue(mockEvidence);
    const { rerender } = render(<EvidencePanel alertId={"a".repeat(64)} />);
    await waitFor(() => expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("loaded"));
    rerender(<EvidencePanel alertId={null} />);
    expect(screen.getByTestId("evidence-panel").getAttribute("data-state")).toBe("empty");
    expect(screen.getByText(/Select an alert to view evidence/)).toBeInTheDocument();
    spy.mockRestore();
  });
});
