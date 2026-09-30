"use client";
import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowUp,
  BookOpen,
  Sparkles,
  ShieldCheck,
  ExternalLink,
} from "lucide-react";
import { api, Answer } from "@/lib/api";
import { ErrorMessage, PageTitle } from "@/components/ui";
type Exchange = { id: string; question: string; result: Answer };
function safeUrl(value: string | null) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}
export default function Assistant() {
  const [question, setQuestion] = useState("");
  const [include, setInclude] = useState(false);
  const [history, setHistory] = useState<Exchange[]>([]);
  const end = useRef<HTMLDivElement>(null);
  const ask = useMutation({
    mutationFn: ({
      question,
      include,
    }: {
      question: string;
      include: boolean;
    }) =>
      api<Answer>("/knowledge/ask", {
        method: "POST",
        body: JSON.stringify({ question, include_documents: include }),
      }),
    onSuccess: (result, variables) => {
      setHistory((old) => [
        ...old,
        { id: crypto.randomUUID(), question: variables.question, result },
      ]);
      setQuestion("");
    },
  });
  useEffect(() => {
    if (history.length)
      end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [history.length]);
  const examples = [
    "How does the standard deduction work?",
    "What is the section 87A rebate?",
    "What can I claim under the old regime?",
  ];
  return (
    <>
      <PageTitle
        eyebrow="A QUESTION IS A GOOD PLACE TO START"
        title="Let’s make sense of it."
      >
        Explore tax guidance with answers you can trace back to a source.
      </PageTitle>
      <section className="chat-panel panel">
        <div className="chat-heading">
          <span className="file-icon">
            <Sparkles size={22} />
          </span>
          <div>
            <h2>TaxAura assistant</h2>
            <p>Grounded in reviewed tax guidance</p>
          </div>
          <span className="tag">Source-linked</span>
        </div>
        <div
          className="chat-messages"
          role="log"
          aria-label="Conversation"
          aria-live="polite"
        >
          {!history.length && (
            <div className="chat-welcome">
              <span className="welcome-icon">
                <Sparkles size={30} />
              </span>
              <h2>What’s on your mind?</h2>
              <p>
                Start with a question about deductions, rebates, or tax regimes.
              </p>
              <div className="suggestions">
                {examples.map((text) => (
                  <button key={text} onClick={() => setQuestion(text)}>
                    {text}
                    <ArrowUp size={15} />
                  </button>
                ))}
              </div>
            </div>
          )}
          {history.map((item) => (
            <div className="exchange" key={item.id}>
              <div className="user-message">{item.question}</div>
              <div className="assistant-message">
                <span className="answer-label">
                  <Sparkles size={16} />
                  {item.result.mode === "generated"
                    ? "Gemini answer"
                    : "Local source excerpts"}
                </span>
                <p className="answer-text">{item.result.answer}</p>
                {item.result.sources.length > 0 && (
                  <div className="sources">
                    <span>
                      <BookOpen size={14} /> Sources
                    </span>
                    {item.result.sources.map((source, i) => {
                      const url = safeUrl(source.source_url);
                      return url ? (
                        <a
                          key={i}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {source.source_name}
                          <ExternalLink size={12} />
                        </a>
                      ) : (
                        <span className="source-label" key={i}>
                          {source.source_name}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ))}
          {ask.isPending && (
            <p role="status" className="thinking">
              <Sparkles className="spin" size={18} /> Looking through the
              sources…
            </p>
          )}
          <div ref={end} />
        </div>
        <div className="chat-composer">
          <ErrorMessage error={ask.error} />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (question.trim().length >= 5)
                ask.mutate({ question: question.trim(), include });
            }}
          >
            <label className="sr-only" htmlFor="question">
              Your tax question
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a tax question…"
              required
              minLength={5}
              maxLength={1000}
              rows={2}
              disabled={ask.isPending}
            />
            <button
              className="button send-button"
              aria-label="Send question"
              disabled={ask.isPending || question.trim().length < 5}
            >
              <ArrowUp size={21} />
            </button>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={include}
                onChange={(e) => setInclude(e.target.checked)}
                disabled={ask.isPending}
              />{" "}
              Include my documents <span>Local excerpts only</span>
            </label>
          </form>
          <p className="chat-privacy">
            <ShieldCheck size={14} />
            {include
              ? "Your question and documents stay in the local excerpt flow; they are not sent to Gemini."
              : "General questions and tax-rule excerpts may be sent to Gemini. Don’t enter sensitive personal details."}
          </p>
        </div>
      </section>
      <p className="quiet chat-disclaimer">
        Answers may be incomplete. Check the sources and applicable assessment
        year before acting.
      </p>
    </>
  );
}
