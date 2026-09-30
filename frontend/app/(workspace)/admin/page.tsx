"use client";
import { useMutation } from "@tanstack/react-query";
import { useRef } from "react";
import Link from "next/link";
import { BookOpen } from "lucide-react";
import { api } from "@/lib/api";
import { useUser } from "@/components/workspace";
import { ErrorMessage, PageTitle } from "@/components/ui";
export default function Admin() {
  const user = useUser();
  const form = useRef<HTMLFormElement>(null);
  const ingest = useMutation({
    mutationFn: (data: FormData) =>
      api<{ chunks_created: number; semantic_indexed: boolean }>(
        "/knowledge/rules",
        {
          method: "POST",
          body: JSON.stringify({
            source_name: String(data.get("source_name")).trim(),
            source_url: String(data.get("source_url")).trim() || null,
            content: String(data.get("content")).trim(),
          }),
        },
      ),
    onSuccess: () => form.current?.reset(),
  });
  if (user.role !== "ADMIN")
    return (
      <div className="empty-state">
        <BookOpen size={30} />
        <h1>Administrator access required</h1>
        <p>Only administrators can add reviewed knowledge sources.</p>
        <Link href="/dashboard" className="button">
          Back to overview
        </Link>
      </div>
    );
  return (
    <>
      <PageTitle
        eyebrow="KNOWLEDGE ADMINISTRATION"
        title="Good answers start with good sources."
      >
        Add reviewed, public tax guidance to the shared knowledge base.
      </PageTitle>
      <section className="panel admin-panel">
        <form
          ref={form}
          onSubmit={(e) => {
            e.preventDefault();
            ingest.mutate(new FormData(e.currentTarget));
          }}
        >
          <label>
            Source name
            <input
              name="source_name"
              required
              minLength={2}
              maxLength={255}
              placeholder="e.g. Income Tax Department — AY 2026–27 guidance"
            />
          </label>
          <label>
            Source URL (optional)
            <input
              name="source_url"
              type="url"
              pattern="https?://.*"
              placeholder="https://…"
            />
          </label>
          <label>
            Reviewed content
            <textarea
              name="content"
              required
              minLength={50}
              maxLength={100000}
              rows={12}
              placeholder="Paste reviewed public guidance. Include the applicable financial and assessment year."
            />
          </label>
          <p className="notice">
            Add public tax guidance only. This content is shared and may be sent
            to Gemini. Do not paste private documents or personal information.
          </p>
          <ErrorMessage error={ingest.error} />
          {ingest.data && (
            <p className="notice success" role="status">
              Added {ingest.data.chunks_created} chunks.{" "}
              {ingest.data.semantic_indexed
                ? "Semantic search is ready."
                : "Full-text search is available; semantic indexing needs a retry via the reindex command."}
            </p>
          )}
          <button className="button" disabled={ingest.isPending}>
            {ingest.isPending ? "Adding source…" : "Add knowledge source"}
          </button>
        </form>
      </section>
    </>
  );
}
