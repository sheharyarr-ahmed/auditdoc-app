import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const upstream = await fetch(`${BACKEND_URL}/results/${encodeURIComponent(params.id)}`);
    const body = await upstream.text();
    return new NextResponse(body, {
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
