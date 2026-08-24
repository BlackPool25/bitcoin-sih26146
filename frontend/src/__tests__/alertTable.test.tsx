import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import AlertTable from "@/components/AlertTable";
import type { Alert } from "@/types/alert";

function makeAlert(overrides: Partial<Alert> & { alert_id: string }): Alert {
  const base: Alert = {
    alert_id: overrides.alert_id,
    rank: overrides.rank ?? 1,
    wallet: overrides.wallet ?? `bc1q${overrides.alert_id.slice(0, 30)}`,
    txid: overrides.txid ?? overrides.alert_id,
    p: overrides.p ?? 0.8,
    tier: overrides.tier ?? "high",
    why: overrides.why ?? "anomaly",
    geo_country: overrides.geo_country ?? "US",
    geo_asn: overrides.geo_asn ?? 15169,
    timestamp: overrides.timestamp ?? new Date().toISOString(),
  };
  return { ...base, ...overrides };
}

// 5 deterministic alerts with distinct p and tiers
const mockAlerts: Alert[] = [
  makeAlert({ alert_id: "a".repeat(64), rank: 1, p: 0.95, tier: "critical", wallet: "bc1qaaa-critical-wallet", why: "fan_in", geo_country: "US" }),
  makeAlert({ alert_id: "b".repeat(64), rank: 2, p: 0.88, tier: "high", wallet: "bc1qbbb-high-wallet", why: "mixer_score", geo_country: "CN" }),
  makeAlert({ alert_id: "c".repeat(64), rank: 3, p: 0.72, tier: "medium", wallet: "bc1qccc-medium-wallet", why: "burst_5m_count", geo_country: "RU" }),
  makeAlert({ alert_id: "d".repeat(64), rank: 4, p: 0.65, tier: "medium", wallet: "bc1qddd-another-medium", why: "peel_depth", geo_country: "DE" }),
  makeAlert({ alert_id: "e".repeat(64), rank: 5, p: 0.55, tier: "low", wallet: "bc1qeee-low-wallet", why: "fee_sat_per_vb", geo_country: "IN" }),
];

describe("AlertTable", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders 5 rows sorted desc by p (default)", () => {
    render(<AlertTable data={mockAlerts} />);
    const rows = screen.getAllByTestId(/^alert-row-/);
    expect(rows).toHaveLength(5);
    // First row should be highest p (critical a*64)
    expect(rows[0].getAttribute("data-testid")).toBe(`alert-row-${"a".repeat(64)}`);
    expect(rows[1].getAttribute("data-testid")).toBe(`alert-row-${"b".repeat(64)}`);
    // Last row should be lowest p
    expect(rows[4].getAttribute("data-testid")).toBe(`alert-row-${"e".repeat(64)}`);
  });

  it("tier filter: selecting critical shows only critical", async () => {
    render(<AlertTable data={mockAlerts} />);
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(5);
    const filter = screen.getByTestId("alert-tier-filter") as HTMLSelectElement;
    fireEvent.change(filter, { target: { value: "critical" } });
    const filtered = screen.getAllByTestId(/^alert-row-/);
    expect(filtered).toHaveLength(1);
    expect(filtered[0].getAttribute("data-testid")).toBe(`alert-row-${"a".repeat(64)}`);

    // back to all
    fireEvent.change(filter, { target: { value: "all" } });
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(5);
  });

  it("search filter filters by wallet/txid/why", async () => {
    render(<AlertTable data={mockAlerts} />);
    const input = screen.getByTestId("alert-search-input") as HTMLInputElement;
    // search for critical wallet substring
    fireEvent.change(input, { target: { value: "aaa-critical" } });
    let rows = screen.getAllByTestId(/^alert-row-/);
    expect(rows).toHaveLength(1);
    expect(rows[0].getAttribute("data-testid")).toBe(`alert-row-${"a".repeat(64)}`);

    // search by why field
    fireEvent.change(input, { target: { value: "mixer_score" } });
    rows = screen.getAllByTestId(/^alert-row-/);
    expect(rows).toHaveLength(1);
    expect(rows[0].getAttribute("data-testid")).toBe(`alert-row-${"b".repeat(64)}`);

    // clear search
    fireEvent.change(input, { target: { value: "" } });
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(5);
  });

  it("click calls onSelectAlert with alert_id and toggles selected state", () => {
    const onSelect = vi.fn();
    const { unmount } = render(<AlertTable data={mockAlerts} onSelectAlert={onSelect} />);
    const firstRow = screen.getByTestId(`alert-row-${"a".repeat(64)}`);
    fireEvent.click(firstRow);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("a".repeat(64));
    unmount();

    // when controlled via selectedAlertId, aria-selected reflects
    const { rerender } = render(<AlertTable data={mockAlerts} onSelectAlert={onSelect} selectedAlertId={"a".repeat(64)} />);
    // Re-render controlled
    rerender(<AlertTable data={mockAlerts} onSelectAlert={onSelect} selectedAlertId={"b".repeat(64)} />);
    const selected = screen.getAllByTestId(`alert-row-${"b".repeat(64)}`);
    const target = selected[selected.length - 1];
    expect(target.getAttribute("aria-selected")).toBe("true");
  });

  it("pagination: Next/Prev and Rows per page", async () => {
    render(<AlertTable data={mockAlerts} />);
    // default pageSize 50 shows all 5
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(5);
    expect(screen.getByText(/Page 1 of 1/)).toBeInTheDocument();

    // change rows per page to 2
    const sizeSelect = screen.getByLabelText(/Rows per page/) as HTMLSelectElement;
    fireEvent.change(sizeSelect, { target: { value: "10" } });
    // still all visible because 10 >5, but change to 2? Actually options are 10,25,50,100 — no 2.
    // To test pagination we pass larger dataset via controlled pagination? Simulate by checking controls exist
    // Instead, test that changing pageSize works and pagination controls update
    expect(sizeSelect.value).toBe("10");
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(5);

    // Reset to 50
    fireEvent.change(sizeSelect, { target: { value: "50" } });
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(5);

    // With pagination pageSize 2 via direct table interaction is not exposed, but we can test Prev/Next disabled state
    const prev = screen.getByLabelText("Previous page") as HTMLButtonElement;
    const next = screen.getByLabelText("Next page") as HTMLButtonElement;
    expect(prev.disabled).toBe(true);
    expect(next.disabled).toBe(true);

    // To properly test pagination with small pageSize, render with custom pageSize via user interaction
    // We simulate by creating a 5-row table and programmatically setting pageSize 2 through Select id alert-page-size
    // The Select only has 10/25/50/100, so we cannot select 2 via UI. Instead assert that pagination shows correct string
    // and that sorting still works: clicking Rank header toggles sort
    const rankButton = screen.getByRole("button", { name: /Rank/ });
    // Rank initially ascending? But p is default desc — clicking Rank should sort by rank asc then desc
    fireEvent.click(rankButton);
    let rowsAfterSort = screen.getAllByTestId(/^alert-row-/);
    // After sorting by rank asc, first row should be rank 1 (a...)
    expect(rowsAfterSort[0].getAttribute("data-testid")).toBe(`alert-row-${"a".repeat(64)}`);
  });

  it("pagination with pageSize 2 via controlled data slice simulation", () => {
    // Create 5 alerts and test that AlertTable pagination slices when pageSize forced to 2
    // Since UI only exposes 10/25/50/100, we test the underlying logic by checking that
    // getPaginationRowModel respects pagination state — we do this by verifying Next/Prev enable when pageSize < count
    // To force small pageSize, we directly render and then fire change on the select with a value not in options
    // jsdom allows setting value even if not in options by dispatching change event manually
    render(<AlertTable data={mockAlerts} />);
    const sizeSelect = document.getElementById("alert-page-size") as HTMLSelectElement;
    // Programmatically add option 2
    const opt = document.createElement("option");
    opt.value = "2";
    opt.text = "2";
    sizeSelect.appendChild(opt);
    fireEvent.change(sizeSelect, { target: { value: "2" } });
    // Now pageSize 2 → 3 pages (5 rows)
    expect(screen.getByText(/Page 1 of 3/)).toBeInTheDocument();
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(2);
    // Next page
    const next = screen.getByLabelText("Next page");
    fireEvent.click(next);
    expect(screen.getByText(/Page 2 of 3/)).toBeInTheDocument();
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(2);
    fireEvent.click(next);
    expect(screen.getByText(/Page 3 of 3/)).toBeInTheDocument();
    expect(screen.getAllByTestId(/^alert-row-/)).toHaveLength(1);
  });

  it("keyboard Enter triggers onSelectAlert", () => {
    const onSelect = vi.fn();
    render(<AlertTable data={mockAlerts} onSelectAlert={onSelect} />);
    const row = screen.getByTestId(`alert-row-${"c".repeat(64)}`);
    row.focus();
    fireEvent.keyDown(row, { key: "Enter", code: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("c".repeat(64));
  });

  it("empty data shows No alerts placeholder", () => {
    render(<AlertTable data={[]} />);
    expect(screen.getByText(/No alerts/)).toBeInTheDocument();
    expect(screen.queryByTestId(/^alert-row-/)).not.toBeInTheDocument();
  });
});
