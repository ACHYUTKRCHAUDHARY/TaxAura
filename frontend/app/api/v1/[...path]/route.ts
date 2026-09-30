import { NextRequest, NextResponse } from "next/server";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
const routes: Record<string, RegExp[]> = {
  GET: [/^users\/me$/, /^documents$/, /^documents\/[0-9a-f-]+(?:\/text)?$/i],
  POST: [
    /^auth\/(login|register)$/,
    /^documents\/upload$/,
    /^documents\/[0-9a-f-]+\/retry$/i,
    /^tax\/compare$/,
    /^knowledge\/(ask|rules)$/,
    /^advisor\/ask$/,
  ],
  DELETE: [/^documents\/[0-9a-f-]+$/i],
};
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const route = path.join("/");
  if (!routes[request.method]?.some((pattern) => pattern.test(route)))
    return NextResponse.json({ detail: "Not found" }, { status: 404 });
  try {
    const origin = new URL(process.env.API_ORIGIN || "http://127.0.0.1:10000");
    if (
      !["http:", "https:"].includes(origin.protocol) ||
      origin.username ||
      origin.password
    )
      throw new Error("Invalid API origin");
    const headers = new Headers();
    for (const name of ["authorization", "content-type"]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    // Bound memory use, including multipart overhead. Vercel applies its own smaller limit.
    let body: Uint8Array | undefined;
    if (request.body) {
      const chunks: Uint8Array[] = [];
      let size = 0;
      const reader = request.body.getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > 11 * 1024 * 1024) {
          await reader.cancel();
          return NextResponse.json(
            { detail: "Upload is too large" },
            { status: 413 },
          );
        }
        chunks.push(value);
      }
      body = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) {
        body.set(chunk, offset);
        offset += chunk.length;
      }
    }
    const response = await fetch(new URL(`/api/v1/${route}`, origin), {
      method: request.method,
      headers,
      body: body as BodyInit | undefined,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(55_000),
    });
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") || "application/json",
        "Cache-Control": "private, no-store",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "The API is unavailable or took too long. Please try again." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as DELETE };
