import { Workspace } from "@/components/workspace";
export const metadata = { robots: { index: false, follow: false } };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <Workspace>{children}</Workspace>;
}
