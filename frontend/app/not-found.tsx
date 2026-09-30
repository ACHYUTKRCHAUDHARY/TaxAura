import Link from "next/link";
export default function NotFound() {
  return (
    <main id="main" className="empty-state">
      <p className="eyebrow">404</p>
      <h1>This page wandered off.</h1>
      <Link className="button" href="/">
        Back to TaxAura
      </Link>
    </main>
  );
}
