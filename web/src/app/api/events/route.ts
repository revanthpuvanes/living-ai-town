import { NextRequest, NextResponse } from "next/server";


export async function GET(request: NextRequest) {
  try {
    const raw = request.nextUrl.searchParams.get("limit") ?? "30";
    const limit = Number(raw);

    if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
      return NextResponse.json(
        { error: "limit must be an integer between 1 and 100" },
        { status: 400 },
      );
    }

    const base = process.env.TOWN_API_URL ?? "http://127.0.0.1:8000";

    const response = await fetch(
      `${base}/api/events?limit=${limit}`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Town backend unavailable" },
        { status: 502 },
      );
    }

    return NextResponse.json(await response.json(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { error: "Cannot connect to Living AI Town backend" },
      { status: 502 },
    );
  }
}
