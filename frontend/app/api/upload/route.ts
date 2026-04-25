import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const upstream = await fetch(`${BACKEND_URL}/upload`, {
      method: "POST",
      body: formData,
    });
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "proxy_failure", status_code: 502, detail: e instanceof Error ? e.message : "Upstream unreachable" },
      { status: 502 },
    );
  }
}
