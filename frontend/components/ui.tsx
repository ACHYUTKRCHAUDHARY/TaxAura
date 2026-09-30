import Link from "next/link";
import { ArrowUpRight, Leaf, LoaderCircle } from "lucide-react";
export function Brand() {
  return (
    <Link href="/" className="brand" aria-label="TaxAura home">
      <span className="brand-mark">
        <Leaf size={23} />
      </span>
      TaxAura<span className="brand-dot">.</span>
    </Link>
  );
}
export function Loading({
  label = "Loading your workspace…",
}: {
  label?: string;
}) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={22} />
      {label}
    </div>
  );
}
export function ErrorMessage({ error }: { error: Error | null }) {
  return error ? (
    <p className="notice error" role="alert">
      {error.message}
    </p>
  ) : null;
}
export function PageTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <header className="page-title">
      <p className="eyebrow">{eyebrow}</p>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  );
}
export function ActionLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link className="button" href={href}>
      {children}
      <ArrowUpRight size={17} />
    </Link>
  );
}
