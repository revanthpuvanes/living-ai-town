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

    const body = await request.json();

    if (
      !["emma", "noah", "sophia"].includes(body?.character_id) ||
      typeof body?.message !== "string" ||
      !body.message.trim() ||
      body.message.length > 300
    ) {
      return NextResponse.json(
        { error: "Invalid character or message" },
        { status: 400 },
      );
    }

    const base = process.env.TOWN_API_URL ?? "http://127.0.0.1:8000";

    const response = await fetch(`${base}/api/visitor-message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json(
      { error: "Unable to send visitor message" },
      { status: 502 },
    );
  }
}
