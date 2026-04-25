import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 180; // /evaluate can take up to ~120s + overhead

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.text();
    const upstream = await fetch(`${BACKEND_URL}/evaluate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body,
    });
    const upstreamBody = await upstream.text();
    return new NextResponse(upstreamBody, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "proxy_failure", status_code: 502, detail: e instanceof Error ? e.message : "Upstream unreachable" },
      { status: 502 },
    );
  }
}
