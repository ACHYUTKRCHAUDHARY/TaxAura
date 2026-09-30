import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";
export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: {
    default: "TaxAura — Tax clarity, in one place",
    template: "%s | TaxAura",
  },
  icons: { icon: "/icon.svg" },
  description:
    "Organize tax documents, compare Indian tax regimes, and find answers grounded in reviewed sources.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
