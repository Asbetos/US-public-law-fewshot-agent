import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";

/** Where the pipeline writes its artefacts. Override with RESULTS_DIR. */
export const RESULTS = process.env.RESULTS_DIR
  ? path.resolve(process.env.RESULTS_DIR)
  : path.resolve(process.cwd(), "..", "results");

async function readJson(file: string): Promise<any | null> {
  try {
    return JSON.parse(await readFile(path.join(RESULTS, file), "utf8"));
  } catch {
    return null; // artefact not produced yet - the renderer handles absence
  }
}

/**
 * Assembles the exact payload shape eval/dashboard.py inlines, so the shared
 * renderer cannot tell which source fed it.
 */
export async function buildPayload(): Promise<any> {
  const metrics = await readJson("metrics.json");
  if (!metrics) throw new Error("metrics.json not found - run eval/score.py first.");

  metrics.infra = await readJson("infra.json");

  const thinking: Record<string, any> = {};
  try {
    for (const f of (await readdir(RESULTS)).sort()) {
      if (f.startsWith("thinking_ab_") && f.endsWith(".json")) {
        thinking[f.replace("thinking_ab_", "").replace(".json", "")] = await readJson(f);
      }
    }
  } catch { /* results dir missing */ }
  metrics.thinking_ab = thinking;

  metrics.run = { ...(metrics.run ?? {}), ...((await readJson("run_meta.json")) ?? {}) };
  metrics.run.model_short ??= "Qwen3.6-27B AWQ-4bit";
  metrics.run.display ??= [];

  try {
    metrics.generated_at = (await stat(path.join(RESULTS, "metrics.json"))).mtime.toISOString();
  } catch { /* ignore */ }

  return metrics;
}
