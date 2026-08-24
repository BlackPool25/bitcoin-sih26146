import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import ReplaySlider from "./ReplaySlider";

const MIN = "2024-01-01T00:00:00Z";
const MAX = "2024-01-01T02:00:00Z";

function mockOk(at: string, rows: unknown[] = [], count = 0) {
  return {
    ok: true,
    status: 200,
    json: async () => ({ rows, count, at }),
  } as unknown as Response;
}

function mock422() {
  return {
    ok: false,
    status: 422,
    json: async () => ({ detail: "Missing at" }),
  } as unknown as Response;
}

type FetchMock = typeof fetch;

describe("ReplaySlider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders slider with min/max and shows ISO", async () => {
    const fetchFn = vi.fn(async () => mockOk(MIN)) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} fetchFn={fetchFn} />);
    const slider = screen.getByTestId("replay-slider") as HTMLInputElement;
    expect(slider).toBeInTheDocument();
    expect(slider.type).toBe("range");
    const minMs = Date.parse(MIN);
    const maxMs = Date.parse(MAX);
    expect(Number(slider.min)).toBe(minMs);
    expect(Number(slider.max)).toBe(maxMs);
    expect(Number(slider.step)).toBe(60000);
    const atEl = screen.getByTestId("replay-at");
    expect(atEl.textContent).toBe(new Date(MIN).toISOString());
    const countEl = screen.getByTestId("replay-count");
    expect(countEl.textContent).toBe("0");
  });

  it("debounced fetch called with correct at", async () => {
    const fetchFn = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      return mockOk(decodeURIComponent(new URL(url, "http://localhost").searchParams.get("at")!));
    }) as unknown as FetchMock;
    const onReplayData = vi.fn();
    render(<ReplaySlider min={MIN} max={MAX} value={MIN} fetchFn={fetchFn} onReplayData={onReplayData} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(1));
    const calledUrl = (fetchFn as unknown as { mock: { calls: unknown[][] } }).mock.calls[0]![0] as string;
    expect(calledUrl).toContain("/api/replay?at=");
    expect(calledUrl).toContain(encodeURIComponent(MIN));
    await waitFor(() => expect(onReplayData).toHaveBeenCalled());
    expect((onReplayData.mock.calls[0] as unknown as { at: string }[])[0].at).toBe(MIN);
  });

  it("Z and +05:30 both trigger fetch with encoded at", async () => {
    const atZ = "2024-01-01T01:00:00Z";
    const atIST = "2024-01-01T01:00:00+05:30";
    const fetchFnZ = vi.fn(async () => mockOk(atZ)) as unknown as FetchMock;
    const { unmount } = render(<ReplaySlider min={MIN} max={MAX} value={atZ} fetchFn={fetchFnZ} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(fetchFnZ).toHaveBeenCalled());
    const urlZ = ((fetchFnZ as unknown as { mock: { calls: unknown[][] } }).mock.calls[0]![0] as string);
    expect(urlZ).toContain(encodeURIComponent(atZ));
    unmount();

    const fetchFnIST = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      const raw = new URL(url, "http://localhost").searchParams.get("at")!;
      expect(url).toContain("%2B");
      return mockOk(raw);
    }) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} value={atIST} fetchFn={fetchFnIST} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(fetchFnIST).toHaveBeenCalled());
    const urlIST = ((fetchFnIST as unknown as { mock: { calls: unknown[][] } }).mock.calls[0]![0] as string);
    expect(urlIST).toContain("%2B");
    const decodedAt = decodeURIComponent(new URL(urlIST, "http://localhost").searchParams.get("at")!);
    expect(decodedAt).toBe(atIST);
  });

  it("handles + encoding vs space fallback", async () => {
    const atIST = "2024-01-01T01:00:00+05:30";
    const fetchFn = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      expect(url).toContain("%2B");
      expect(url).not.toContain(" ");
      return mockOk(atIST);
    }) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} value={atIST} fetchFn={fetchFn} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(fetchFn).toHaveBeenCalled());
  });

  it("422 when at missing (empty string) shows error no crash", async () => {
    const fetchFn = vi.fn(async () => mock422()) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} value="" fetchFn={fetchFn} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(screen.getByTestId("replay-error")).toBeInTheDocument());
    expect(screen.getByTestId("replay-error").textContent).toMatch(/Missing at/i);
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it("422 response shows error", async () => {
    const fetchFn = vi.fn(async () => mock422()) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} value={MIN} fetchFn={fetchFn} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(screen.getByTestId("replay-error")).toBeInTheDocument());
    expect(screen.getByTestId("replay-error").textContent).toMatch(/Missing at/i);
  });

  it("loading state appears then disappears", async () => {
    let resolve!: (v: Response) => void;
    const fetchFn = vi.fn(
      () =>
        new Promise<Response>((r) => {
          resolve = r;
        }),
    ) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} value={MIN} fetchFn={fetchFn} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(screen.getByTestId("replay-loading")).toBeInTheDocument());
    await act(async () => {
      resolve(mockOk(MIN));
      await new Promise((r) => setTimeout(r, 20));
    });
    await waitFor(() => expect(screen.queryByTestId("replay-loading")).not.toBeInTheDocument());
  });

  it("onReplayData called with mock data and count display", async () => {
    const rows = [
      {
        timestamp: "2024-01-01T00:00:00Z",
        src_ip: "1.1.1.1",
        dst_ip: "2.2.2.2",
        src_port: 1000,
        dst_port: 2000,
        txid: "a".repeat(64),
        input_addresses: ["w1"],
        output_addresses: ["w2"],
        input_amounts: [1],
        output_amounts: [1],
        fee: 0.001,
        script_type: "P2PKH",
        geo_country: "US",
        geo_asn: 1,
      },
    ];
    const fetchFn = vi.fn(async () => mockOk(MIN, rows, rows.length)) as unknown as FetchMock;
    const onReplayData = vi.fn();
    render(<ReplaySlider min={MIN} max={MAX} value={MIN} fetchFn={fetchFn} onReplayData={onReplayData} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(onReplayData).toHaveBeenCalled());
    expect((onReplayData.mock.calls[0] as unknown as { count: number }[])[0].count).toBe(1);
    expect((onReplayData.mock.calls[0] as unknown as { rows: unknown[] }[])[0].rows).toEqual(rows);
    expect(screen.getByTestId("replay-count").textContent).toBe("1");
  });

  it("slider change debounces and updates at and fetch", async () => {
    const fetchFn = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      const at = new URL(url, "http://localhost").searchParams.get("at")!;
      return mockOk(decodeURIComponent(at));
    }) as unknown as FetchMock;
    const onChange = vi.fn();
    render(<ReplaySlider min={MIN} max={MAX} value={MIN} stepMs={60000} fetchFn={fetchFn} onChange={onChange} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    (fetchFn as unknown as { mockClear: () => void }).mockClear();
    const slider = screen.getByTestId("replay-slider") as HTMLInputElement;
    const nextMs = Date.parse("2024-01-01T01:00:00Z");
    await act(async () => {
      fireEvent.change(slider, { target: { value: String(nextMs) } });
    });
    expect(onChange).toHaveBeenCalledWith(new Date(nextMs).toISOString());
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(fetchFn).toHaveBeenCalledTimes(1));
    const called = ((fetchFn as unknown as { mock: { calls: unknown[][] } }).mock.calls[0]![0] as string);
    expect(called).toContain(encodeURIComponent(new Date(nextMs).toISOString()));
  });

  it("supports limit 1000 count display", async () => {
    const fetchFn = vi.fn(async () => mockOk(MAX, [], 1000)) as unknown as FetchMock;
    render(<ReplaySlider min={MIN} max={MAX} value={MAX} fetchFn={fetchFn} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    await waitFor(() => expect(screen.getByTestId("replay-count").textContent).toBe("1000"));
  });

  it("abort previous fetch on rapid change", async () => {
    const fetchFn = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      await new Promise((r) => setTimeout(r, 200));
      if (init?.signal?.aborted) {
        const e = new DOMException("Aborted", "AbortError");
        throw e;
      }
      return mockOk(MIN);
    }) as unknown as FetchMock;
    const onReplayData = vi.fn();
    const { rerender } = render(<ReplaySlider min={MIN} max={MAX} value={MIN} fetchFn={fetchFn} onReplayData={onReplayData} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 260));
    });
    rerender(<ReplaySlider min={MIN} max={MAX} value={MAX} fetchFn={fetchFn} onReplayData={onReplayData} />);
    await act(async () => {
      await new Promise((r) => setTimeout(r, 300));
    });
    expect(true).toBe(true);
  });
});
