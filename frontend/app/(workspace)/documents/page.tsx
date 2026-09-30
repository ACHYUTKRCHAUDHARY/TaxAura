"use client";
import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileText, X, Trash2, RotateCcw, Eye } from "lucide-react";
import { api, Document } from "@/lib/api";
import { useDocuments } from "@/lib/queries";
import { useUser } from "@/components/workspace";
import { ErrorMessage, Loading, PageTitle } from "@/components/ui";
const maxMB = Number(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB || 4);
export default function Documents() {
  const user = useUser();
  const client = useQueryClient();
  const docs = useDocuments();
  const input = useRef<HTMLInputElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const [selected, setSelected] = useState<Document | null>(null);
  const [localError, setLocalError] = useState<Error | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null);
  const deleteDialog = useRef<HTMLDialogElement>(null);
  const [notice, setNotice] = useState("");
  const refresh = () =>
    client.invalidateQueries({ queryKey: ["documents", user.id] });
  const upload = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return api("/documents/upload", { method: "POST", body });
    },
    onSuccess: () => {
      setNotice(
        "Document uploaded. Extraction will continue in the background.",
      );
      void refresh();
    },
    onSettled: () => {
      if (input.current) input.current.value = "";
    },
  });
  const retry = useMutation({
    mutationFn: (id: string) =>
      api(`/documents/${id}/retry`, { method: "POST" }),
    onSuccess: () => {
      setNotice("Document queued again.");
      void refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/documents/${id}`, { method: "DELETE" }),
    onSuccess: (_, id) => {
      client.removeQueries({ queryKey: ["document-text", user.id, id] });
      setDeleteTarget(null);
      deleteDialog.current?.close();
      setNotice("Document deleted.");
      void refresh();
    },
  });
  const preview = useQuery({
    queryKey: ["document-text", user.id, selected?.id],
    queryFn: ({ signal }) =>
      api<{ text: string }>(`/documents/${selected!.id}/text`, { signal }),
    enabled: !!selected,
    gcTime: 0,
  });
  function choose(file?: File) {
    if (!file || upload.isPending) return;
    setLocalError(null);
    setNotice("");
    upload.reset();
    if (!["application/pdf", "image/png", "image/jpeg"].includes(file.type)) {
      setLocalError(new Error("Choose a PDF, PNG, or JPEG file."));
      if (input.current) input.current.value = "";
      return;
    }
    if (file.size > maxMB * 1024 * 1024) {
      setLocalError(new Error(`Choose a file smaller than ${maxMB} MB.`));
      if (input.current) input.current.value = "";
      return;
    }
    upload.mutate(file);
  }
  return (
    <>
      <PageTitle
        eyebrow="YOUR PAPERWORK, ORGANIZED"
        title="A home for your documents."
      >
        Upload, review, and manage the files behind your tax decisions.
      </PageTitle>
      <section
        className={`upload-zone ${upload.isPending ? "busy" : ""}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          choose(e.dataTransfer.files[0]);
        }}
      >
        <span className="upload-icon">
          <UploadCloud size={29} />
        </span>
        <div>
          <h2>
            {upload.isPending
              ? "Uploading your document…"
              : "Bring your paperwork together."}
          </h2>
          <p>
            Drop a file here, or browse your device. PDF, PNG, or JPEG · up to{" "}
            {maxMB} MB.
          </p>
          <small>
            Text PDFs and clear images work best. Convert scanned PDFs to images
            first.
          </small>
        </div>
        <input
          ref={input}
          type="file"
          aria-label="Choose document"
          accept="application/pdf,image/png,image/jpeg"
          className="sr-only"
          disabled={upload.isPending}
          onChange={(e) => choose(e.target.files?.[0])}
        />
        <button
          className="button"
          disabled={upload.isPending}
          onClick={() => input.current?.click()}
        >
          {upload.isPending ? "Uploading…" : "Browse files"}
        </button>
      </section>
      <ErrorMessage
        error={localError || upload.error || retry.error || docs.error}
      />
      {notice && (
        <p role="status" className="notice success">
          {notice}
        </p>
      )}
      <section className="panel documents-panel">
        <div className="panel-heading">
          <h2>
            Your documents{" "}
            <span className="count">{docs.data?.length ?? "—"}</span>
          </h2>
          <span className="quiet">Status updates automatically</span>
        </div>
        {docs.isPending ? (
          <Loading />
        ) : !docs.data?.length ? (
          <div className="empty-state">
            <FileText size={34} />
            <h3>A little less scattered.</h3>
            <p>Your uploaded documents will appear here.</p>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Added</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {docs.data.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <div className="file-cell">
                        <FileText size={21} />
                        <div>
                          <strong>{doc.filename}</strong>
                          <small>
                            {doc.mime_type === "application/pdf"
                              ? "PDF document"
                              : "Image document"}
                          </small>
                          {doc.processing_error && (
                            <small className="error-text">
                              {doc.processing_error}
                            </small>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="nowrap">
                      {new Date(doc.created_at).toLocaleDateString("en-IN")}
                    </td>
                    <td>
                      <span
                        className={`status ${doc.processing_status.toLowerCase()}`}
                      >
                        {doc.processing_status.toLowerCase()}
                      </span>
                    </td>
                    <td>
                      <div className="row-actions">
                        {doc.processing_status === "COMPLETED" && (
                          <button
                            className="icon-button"
                            aria-label={`View ${doc.filename}`}
                            title="View extracted text"
                            onClick={() => {
                              setSelected(doc);
                              dialog.current?.showModal();
                            }}
                          >
                            <Eye size={18} />
                          </button>
                        )}
                        {doc.processing_status === "FAILED" && (
                          <button
                            className="icon-button"
                            disabled={retry.isPending}
                            aria-label={`Retry ${doc.filename}`}
                            onClick={() => retry.mutate(doc.id)}
                          >
                            <RotateCcw size={18} />
                          </button>
                        )}
                        <button
                          className="icon-button danger"
                          aria-label={`Delete ${doc.filename}`}
                          onClick={() => {
                            remove.reset();
                            setDeleteTarget(doc);
                            deleteDialog.current?.showModal();
                          }}
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <dialog
        ref={dialog}
        className="text-dialog"
        onClose={() => setSelected(null)}
        aria-labelledby="preview-title"
      >
        <div className="panel-heading">
          <div>
            <p className="eyebrow">EXTRACTED TEXT</p>
            <h2 id="preview-title">{selected?.filename}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close preview"
            onClick={() => dialog.current?.close()}
          >
            <X />
          </button>
        </div>
        {preview.isPending ? (
          <Loading label="Loading extracted text…" />
        ) : preview.isError ? (
          <ErrorMessage error={preview.error} />
        ) : (
          <pre>{preview.data?.text || "No text was extracted."}</pre>
        )}
      </dialog>
      <dialog
        ref={deleteDialog}
        className="confirm-dialog"
        onClose={() => setDeleteTarget(null)}
        aria-labelledby="delete-title"
      >
        <h2 id="delete-title">Delete this document?</h2>
        <p>
          {deleteTarget?.filename} and its extracted content will be removed.
          This cannot be undone.
        </p>
        <ErrorMessage error={remove.error} />
        <div className="dialog-actions">
          <button
            className="button secondary"
            onClick={() => deleteDialog.current?.close()}
          >
            Cancel
          </button>
          <button
            className="button destructive"
            disabled={remove.isPending || !deleteTarget}
            onClick={() => deleteTarget && remove.mutate(deleteTarget.id)}
          >
            {remove.isPending ? "Deleting…" : "Delete document"}
          </button>
        </div>
      </dialog>
    </>
  );
}
