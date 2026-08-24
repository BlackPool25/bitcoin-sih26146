import { describe, it, expect } from "vitest";
import { measureFPSForCyJson, benchPresetPerformance, BENCH_80, BENCH_2000 } from "./fps";
import { auditGuardrails, GUARDRAIL_DESCRIPTIONS } from "@/cytoscape/guardrails";
import { generateReportData } from "./report";
import fs from "node:fs";
import path from "node:path";

function readAllSrc(): string {
  // Aggregate key source files for guardrail audit (avoid full fs walk in test)
  const candidates = [
    "src/components/GraphView.tsx",
    "src/cytoscape/styles.ts",
    "src/cytoscape/update.ts",
    "src/App.tsx",
    "src/api/client.ts",
  ];
  const root = path.resolve(__dirname, "../..");
  let combined = "";
  for (const rel of candidates) {
    const full = path.join(root, rel);
    try {
      combined += "\n" + fs.readFileSync(full, "utf8");
    } catch {
      // ignore missing
    }
  }
  // also include styles pixelRatio constant explicitly
  return combined;
}

describe("bench fps preset >30", () => {
  it("80 nodes fps >30", () => {
    const r = benchPresetPerformance(80);
    expect(r.fps).toBeGreaterThan(30);
    expect(r.renderMs).toBeGreaterThan(0);
    expect(r.renderMs).toBeLessThan(33);
  });

  it("2000 nodes fps >30 with haystack (preset)", () => {
    const r = benchPresetPerformance(2000);
    expect(r.fps).toBeGreaterThan(30);
    expect(r.renderMs).toBeGreaterThan(0);
    expect(r.renderMs).toBeLessThan(33);
  });

  it("measureFPSForCyJson 80 returns >30", async () => {
    const fpsRaw = measureFPSForCyJson(BENCH_80, 2);
    const fps = fpsRaw instanceof Promise ? await fpsRaw : fpsRaw;
    expect(fps).toBeGreaterThan(30);
  });

  it("measureFPSForCyJson 2000 returns >30 with haystack preset", async () => {
    const fpsRaw = measureFPSForCyJson(BENCH_2000, 2);
    const fps = fpsRaw instanceof Promise ? await fpsRaw : fpsRaw;
    expect(fps).toBeGreaterThan(30);
  });

  it("fixtures have expected sizes", () => {
    expect(BENCH_80.nodes.length).toBe(80);
    expect(BENCH_2000.nodes.length).toBeGreaterThanOrEqual(2000);
    // 2000 graph should have haystack-eligible edges (>500)
    expect(BENCH_2000.edges.length).toBeGreaterThan(500);
  });
});

describe("guardrails audit", () => {
  it("auditGuardrails passes for project source", () => {
    const src = readAllSrc();
    const r = auditGuardrails(src);
    expect(r.pixelRatioOk, `pixelRatio guard failed: ${GUARDRAIL_DESCRIPTIONS.pixelRatioOk}`).toBe(true);
    expect(r.batchOk, GUARDRAIL_DESCRIPTIONS.batchOk).toBe(true);
    expect(r.haystackOk, GUARDRAIL_DESCRIPTIONS.haystackOk).toBe(true);
    expect(r.limitOk, GUARDRAIL_DESCRIPTIONS.limitOk).toBe(true);
  });

  it("detects missing guardrails", () => {
    const bad = "GET /api/graph/123 no-limit-param";
    const r = auditGuardrails(bad);
    expect(r.limitOk).toBe(false);
  });

  it("no limit-less graph API fetch in codebase", () => {
    const root = path.resolve(__dirname, "../..");
    const srcDir = path.join(root, "src");
    const bad: string[] = [];
    function walk(dir: string) {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (entry.name === "node_modules" || entry.name === "dist") continue;
          walk(full);
        } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
          if (full.endsWith("fps.test.ts")) continue;
          if (full.includes("__tests__")) continue;
          if (full.includes("m5.contract")) continue;
          const content = fs.readFileSync(full, "utf8");
          const lines = content.split("\n");
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (/fetch.*\/api\/graph/.test(line) && !/limit=/.test(line)) {
              if (line.trim().startsWith("//") || line.trim().startsWith("*")) continue;
              if (line.includes("without limit")) continue;
              bad.push(`${path.relative(root, full)}:${i + 1}:${line.trim()}`);
            }
          }
        }
      }
    }
    walk(srcDir);
    expect(bad, `Found limit-less graph fetch:\n${bad.join("\n")}`).toEqual([]);
  });
});

describe("bench report.json", () => {
  it("generates report.json with passed:true if not exists", async () => {
    const reportPath = path.resolve(__dirname, "../../bench/report.json");
    // Generate inline via generateReportData and write to bench/report.json
    const src = readAllSrc();
    const data = await generateReportData(src);
    expect(data.nodes80.fps).toBeGreaterThan(30);
    expect(data.nodes2000.fps).toBeGreaterThan(30);
    expect(data.alertToGraphMs).toBeLessThan(500);
    expect(data.passed).toBe(true);

    // Ensure bench dir exists and write report if missing or to update timestamp
    const benchDir = path.dirname(reportPath);
    if (!fs.existsSync(benchDir)) fs.mkdirSync(benchDir, { recursive: true });
    // If report doesn't exist, create it; otherwise verify existing also passed
    if (!fs.existsSync(reportPath)) {
      fs.writeFileSync(reportPath, JSON.stringify(data, null, 2), "utf8");
    } else {
      // Validate existing report
      const existing = JSON.parse(fs.readFileSync(reportPath, "utf8")) as typeof data;
      expect(existing.passed).toBe(true);
      expect(existing.nodes2000.fps).toBeGreaterThan(30);
      expect(existing.alertToGraphMs).toBeLessThan(500);
      // refresh file to keep timestamp recent (optional)
      fs.writeFileSync(reportPath, JSON.stringify(data, null, 2), "utf8");
    }
    expect(fs.existsSync(reportPath)).toBe(true);
    const final = JSON.parse(fs.readFileSync(reportPath, "utf8")) as typeof data;
    expect(final.passed).toBe(true);
  });
});
