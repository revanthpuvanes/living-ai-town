import { NextResponse } from "next/server";

export async function GET() {
  try {
    const base = process.env.TOWN_API_URL ?? "http://127.0.0.1:8000";

    const response = await fetch(`${base}/api/simulation`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Simulation unavailable" },
        { status: 502 },
      );
    }

    return NextResponse.json(await response.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { error: "Cannot connect to simulation" },
      { status: 502 },
    );
  }
}
