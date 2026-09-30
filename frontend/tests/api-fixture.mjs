// Controlled API fixture behind the real Next.js proxy; no Gemini/DB credentials needed.
import http from "node:http";
import { randomUUID } from "node:crypto";
let users, documents, failedReads, expired;
function reset() {
  users = new Map([
    [
      "alice@example.com",
      {
        id: "00000000-0000-0000-0000-000000000001",
        email: "alice@example.com",
        full_name: "Alice Demo",
        role: "USER",
      },
    ],
    [
      "admin@example.com",
      {
        id: "00000000-0000-0000-0000-000000000002",
        email: "admin@example.com",
        full_name: "Admin Demo",
        role: "ADMIN",
      },
    ],
  ]);
  documents = [];
  failedReads = false;
  expired = false;
}
reset();
http
  .createServer(async (req, res) => {
    const url = req.url;
    const method = req.method;
    const send = (status, body) => {
      res.writeHead(status, { "Content-Type": "application/json" });
      res.end(body === undefined ? undefined : JSON.stringify(body));
    };
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const raw = Buffer.concat(chunks).toString();
    if (url === "/health") return send(200, { status: "UP" });
    if (url === "/__reset") {
      reset();
      return send(200, {});
    }
    if (url === "/__expire") {
      expired = true;
      return send(200, {});
    }
    if (url === "/__fail-documents") {
      failedReads = true;
      return send(200, {});
    }
    if (url === "/api/v1/auth/login") {
      if (
        !req.headers["content-type"]?.startsWith(
          "application/x-www-form-urlencoded",
        )
      )
        return send(415, { detail: "Form content type missing" });
      const data = new URLSearchParams(raw);
      const user = users.get(data.get("username"));
      if (!user || data.get("password") !== "correct-password")
        return send(401, { detail: "Invalid email or password" });
      expired = false;
      return send(200, { access_token: user.email, user });
    }
    if (url === "/api/v1/auth/register") {
      const data = JSON.parse(raw);
      if (users.has(data.email))
        return send(409, { detail: "Email already registered" });
      const user = { ...data, id: randomUUID(), role: "USER" };
      delete user.password;
      users.set(user.email, user);
      return send(201, { access_token: user.email, user });
    }
    const user = users.get(req.headers.authorization?.replace("Bearer ", ""));
    if (!user || expired) return send(401, { detail: "Session expired" });
    if (url === "/api/v1/users/me") return send(200, user);
    if (url === "/api/v1/documents" && method === "GET") {
      if (failedReads)
        return send(503, { detail: "Documents temporarily unavailable" });
      return send(
        200,
        documents
          .filter((d) => d.user_id === user.id)
          .map((d) => {
            if (
              d.processing_status === "QUEUED" &&
              Date.now() - d.queuedAt > 750
            )
              d.processing_status = "COMPLETED";
            return d;
          }),
      );
    }
    if (url === "/api/v1/documents/upload") {
      if (
        !req.headers["content-type"]?.includes("multipart/form-data; boundary=")
      )
        return send(415, { detail: "Multipart boundary missing" });
      const filename = raw.match(/filename="([^"]+)"/)?.[1];
      if (!filename) return send(422, { detail: "File missing" });
      if (
        documents.some((d) => d.user_id === user.id && d.filename === filename)
      )
        return send(409, { detail: "This document has already been uploaded" });
      const doc = {
        id: randomUUID(),
        user_id: user.id,
        filename,
        mime_type: "application/pdf",
        processing_status: filename === "failed.pdf" ? "FAILED" : "QUEUED",
        processing_error:
          filename === "failed.pdf" ? "Extraction failed" : null,
        created_at: new Date().toISOString(),
        queuedAt: Date.now(),
      };
      documents.unshift(doc);
      return send(202, { document_id: doc.id, status: doc.processing_status });
    }
    const match = url.match(
      /^\/api\/v1\/documents\/([0-9a-f-]+)(\/text|\/retry)?$/,
    );
    if (match) {
      const doc = documents.find(
        (d) => d.id === match[1] && d.user_id === user.id,
      );
      if (!doc) return send(404, { detail: "Document not found" });
      if (match[2] === "/text")
        return send(200, {
          id: doc.id,
          filename: doc.filename,
          text: "Form 16. Annual salary: 1200000. <script>not executable</script>",
        });
      if (match[2] === "/retry") {
        doc.processing_status = "QUEUED";
        doc.processing_error = null;
        doc.queuedAt = Date.now();
        return send(200, doc);
      }
      if (method === "DELETE") {
        documents = documents.filter((d) => d.id !== doc.id);
        return send(204);
      }
    }
    if (url === "/api/v1/tax/compare") {
      const data = JSON.parse(raw);
      if (
        typeof data.annual_salary !== "number" ||
        typeof data.old_regime_deductions !== "number"
      )
        return send(422, { detail: "Numbers expected" });
      const regime = {
        taxable_income: "1125000",
        tax_before_cess: "0",
        cess: "0",
        total_tax: "0",
      };
      return send(200, {
        assessment_year: "AY 2026-27",
        old_regime: {
          ...regime,
          tax_before_cess: "100000",
          cess: "4000",
          total_tax: "104000",
        },
        new_regime: regime,
        recommended_regime: "NEW",
        estimated_saving: "104000",
        disclaimer: "Fixture estimate for browser verification.",
      });
    }
    if (url === "/api/v1/knowledge/ask") {
      const data = JSON.parse(raw);
      if (data.question.includes("failure"))
        return send(503, { detail: "Please try your question again" });
      return send(200, {
        answer: data.include_documents
          ? "Local document excerpt: Form 16 salary information."
          : "The standard deduction reduces taxable salary. <script>not executable</script>",
        mode: data.include_documents ? "extractive" : "generated",
        sources: [
          {
            source_name: "Reviewed tax guidance",
            source_url: "https://www.incometax.gov.in/",
          },
          {
            source_name: "Unsafe URL is plain text",
            source_url: "javascript:alert(1)",
          },
        ],
      });
    }
    if (url === "/api/v1/knowledge/rules") {
      if (user.role !== "ADMIN")
        return send(403, { detail: "Administrator required" });
      const data = JSON.parse(raw);
      if (data.content.length < 50)
        return send(422, { detail: "Content too short" });
      return send(201, { chunks_created: 2, semantic_indexed: true });
    }
    send(404, { detail: "Not found" });
  })
  .listen(8899, "127.0.0.1");
