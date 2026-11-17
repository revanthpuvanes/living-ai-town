import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const origin = request.headers.get("origin");

    if (origin && new URL(origin).host !== request.headers.get("host")) {
      return NextResponse.json(
        { error: "Invalid origin" },
        { status: 403 },
      );
    }

    const base = process.env.TOWN_API_URL ?? "http://127.0.0.1:8000";

    const response = await fetch(`${base}/api/simulation/stop`, {
      method: "POST",
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    return NextResponse.json(await response.json(), {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { error: "Unable to stop simulation" },
      { status: 502 },
    );
  }
}
