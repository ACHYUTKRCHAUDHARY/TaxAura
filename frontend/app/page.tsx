import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileText,
  Calculator,
  Sparkles,
  ShieldCheck,
  ArrowUpRight,
} from "lucide-react";
import { Brand } from "@/components/ui";
export default function Home() {
  return (
    <>
      <header className="public-header">
        <Brand />
        <nav aria-label="Main navigation">
          <Link href="#how-it-works" className="desktop-link">
            How it works
          </Link>
          <Link href="/login">Log in</Link>
          <Link href="/register" className="button small">
            Get started <ArrowUpRight size={16} />
          </Link>
        </nav>
      </header>
      <main id="main">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">
              <span className="live-dot" /> YOUR TAXES. A LITTLE CLEARER.
            </p>
            <h1>
              Less paperwork.
              <br />
              More <em>peace of mind.</em>
            </h1>
            <p className="hero-description">
              Your documents, tax estimates, and answers — together in one calm
              workspace. Make sense of your taxes, one step at a time.
            </p>
            <div className="hero-actions">
              <Link href="/register" className="button">
                Create your workspace <ArrowRight size={18} />
              </Link>
              <Link href="#how-it-works" className="text-link">
                Take a look <span>↗</span>
              </Link>
            </div>
            <p className="quiet hero-note">
              <ShieldCheck size={16} /> Private documents stay out of Gemini
              answers.
            </p>
          </div>
          <div className="hero-visual">
            <div className="preview-label">
              A LITTLE ORGANIZATION GOES A LONG WAY
            </div>
            <div className="preview-card">
              <div className="preview-top">
                <span className="brand-mark">
                  <LeafIcon />
                </span>
                <span>
                  Your tax workspace<small>Illustrative preview</small>
                </span>
                <span className="tag">AY 2026–27</span>
              </div>
              <h2>Everything in its place.</h2>
              <div className="preview-document">
                <FileText />
                <span>
                  Form 16.pdf<small>Extracted and ready to review</small>
                </span>
                <span className="check-icon">
                  <Check size={15} />
                </span>
              </div>
              <div className="preview-document">
                <FileText />
                <span>
                  Investment proof.pdf
                  <small>Extracted and ready to review</small>
                </span>
                <span className="check-icon">
                  <Check size={15} />
                </span>
              </div>
              <div className="preview-insight">
                <Sparkles size={22} />
                <div>
                  <strong>Clarity starts with a question.</strong>
                  <p>Find answers with sources you can check.</p>
                </div>
              </div>
            </div>
            <div className="floating-note">
              <ShieldCheck size={20} />
              <span>
                Your workspace.
                <br />
                <strong>Your documents.</strong>
              </span>
            </div>
            <div className="visual-orbit" />
          </div>
        </section>
        <section id="how-it-works" className="features-section">
          <div className="section-heading">
            <p className="eyebrow">A SIMPLER WAY THROUGH TAX SEASON</p>
            <h2>From scattered files to a clearer picture.</h2>
          </div>
          <div className="feature-grid">
            {[
              {
                icon: FileText,
                n: "01",
                title: "Bring it all together",
                text: "Upload PDFs and images. Review extracted text and keep your paperwork in one place.",
              },
              {
                icon: Calculator,
                n: "02",
                title: "Know your options",
                text: "Compare old and new regimes with a transparent salary-based estimate for AY 2026–27.",
              },
              {
                icon: Sparkles,
                n: "03",
                title: "Ask. Understand. Decide.",
                text: "Explore tax questions with source-linked answers and clearly labeled local excerpts.",
              },
            ].map(({ icon: Icon, n, title, text }) => (
              <article className="feature" key={n}>
                <div className="feature-top">
                  <Icon size={25} />
                  <span>{n}</span>
                </div>
                <h3>{title}</h3>
                <p>{text}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
      <footer className="public-footer">
        <Brand />
        <p>
          Built for clarity. Educational guidance, not tax filing or
          professional advice.
        </p>
        <span>Made for India ↗</span>
      </footer>
    </>
  );
}
function LeafIcon() {
  return <ShieldCheck size={22} />;
}
