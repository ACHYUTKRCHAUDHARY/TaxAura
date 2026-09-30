"use client";
import Link from "next/link";
import {
  FileText,
  CheckCircle2,
  Clock3,
  ArrowUpRight,
  Calculator,
  Sparkles,
} from "lucide-react";
import { useUser } from "@/components/workspace";
import { useDocuments } from "@/lib/queries";
import { PageTitle, ErrorMessage, Loading } from "@/components/ui";
export default function Dashboard() {
  const user = useUser();
  const docs = useDocuments();
  return (
    <>
      <PageTitle
        eyebrow="YOUR OVERVIEW"
        title={`A clearer picture, ${user.full_name.split(" ")[0]}.`}
      >
        Everything you need for your next step, in one place.
      </PageTitle>
      <ErrorMessage error={docs.error} />
      <div className="stats-grid">
        {[
          {
            label: "Total documents",
            count: docs.data?.length,
            icon: FileText,
          },
          {
            label: "Ready to review",
            count: docs.data?.filter((d) => d.processing_status === "COMPLETED")
              .length,
            icon: CheckCircle2,
          },
          {
            label: "In progress",
            count: docs.data?.filter((d) =>
              ["QUEUED", "PROCESSING"].includes(d.processing_status),
            ).length,
            icon: Clock3,
          },
        ].map(({ label, count, icon: Icon }) => (
          <div className="stat-card" key={label}>
            <Icon size={21} />
            <strong>{count ?? "—"}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">YOUR PAPERWORK</p>
              <h2>Recent documents</h2>
            </div>
            <Link href="/documents" className="text-link">
              View all <ArrowUpRight size={16} />
            </Link>
          </div>
          {docs.isPending ? (
            <Loading label="Loading documents…" />
          ) : docs.data?.length ? (
            <div>
              {docs.data.slice(0, 4).map((doc) => (
                <Link
                  href="/documents"
                  className="document-summary"
                  key={doc.id}
                >
                  <span className="file-icon">
                    <FileText size={21} />
                  </span>
                  <span className="truncate">
                    {doc.filename}
                    <small>
                      {new Date(doc.created_at).toLocaleDateString("en-IN")}
                    </small>
                  </span>
                  <span
                    className={`status ${doc.processing_status.toLowerCase()}`}
                  >
                    {doc.processing_status.toLowerCase()}
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <FileText size={32} />
              <h3>A fresh start for your paperwork.</h3>
              <p>Add a Form 16, salary slip, or investment proof.</p>
              <Link href="/documents" className="button">
                Upload a document <ArrowUpRight size={17} />
              </Link>
            </div>
          )}
        </section>
        <section className="next-step">
          <p className="eyebrow">YOUR NEXT STEP</p>
          <Calculator size={31} />
          <h2>
            Two regimes.
            <br />
            One informed choice.
          </h2>
          <p>
            Compare estimated tax under the old and new regimes for AY 2026–27.
          </p>
          <Link href="/calculator" className="button light">
            Compare regimes <ArrowUpRight size={17} />
          </Link>
        </section>
      </div>
      <Link href="/assistant" className="assistant-banner">
        <span className="file-icon">
          <Sparkles size={22} />
        </span>
        <div>
          <h3>Have a tax question on your mind?</h3>
          <p>Start with an answer. Follow it back to the source.</p>
        </div>
        <ArrowUpRight size={23} />
      </Link>
    </>
  );
}
