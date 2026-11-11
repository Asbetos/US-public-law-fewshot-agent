import { NextResponse } from "next/server";
import { buildPayload, RESULTS } from "../../lib/payload";

/** The same payload the page renders, for scripting against. */
export const dynamic = "force-dynamic";
export const revalidate = 0;

export async function GET() {
  try {
    return NextResponse.json(await buildPayload(), {
      headers: { "Cache-Control": "no-store, max-age=0" },
    });
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : String(e), results_dir: RESULTS },
      { status: 404 },
    );
  }
}
