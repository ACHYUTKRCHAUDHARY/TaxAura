"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  FileText,
  Calculator,
  Sparkles,
  BookOpen,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { api, token, TOKEN_KEY, User } from "@/lib/api";
import { Brand, ErrorMessage, Loading } from "./ui";
const UserContext = createContext<User | null>(null);
export function useUser() {
  const user = useContext(UserContext);
  if (!user) throw new Error("Workspace required");
  return user;
}
export function Workspace({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const client = useQueryClient();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!token()) router.replace("/login");
    else setReady(true);
    const logout = () => {
      setReady(false);
      void client.cancelQueries().then(() => client.clear());
      router.replace("/login");
    };
    window.addEventListener("taxaura:logout", logout);
    return () => window.removeEventListener("taxaura:logout", logout);
  }, [client, router]);
  const user = useQuery({
    queryKey: ["session"],
    queryFn: ({ signal }) => api<User>("/users/me", { signal }),
    enabled: ready,
    retry: false,
  });
  if (!ready || user.isPending)
    return (
      <main id="main">
        <Loading />
      </main>
    );
  if (user.isError)
    return (
      <main id="main" className="standalone-error">
        <ErrorMessage error={user.error} />
        <button className="button" onClick={() => user.refetch()}>
          Try again
        </button>
        <Link href="/login">Return to sign in</Link>
      </main>
    );
  const links = [
    { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
    { href: "/documents", label: "Documents", icon: FileText },
    { href: "/calculator", label: "Tax calculator", icon: Calculator },
    { href: "/assistant", label: "Tax assistant", icon: Sparkles },
    ...(user.data.role === "ADMIN"
      ? [{ href: "/admin", label: "Knowledge admin", icon: BookOpen }]
      : []),
  ];
  return (
    <UserContext value={user.data}>
      <div className="workspace">
        <aside className="sidebar">
          <Brand />
          <div className="workspace-caption">YOUR WORKSPACE</div>
          <nav aria-label="Workspace">
            {links.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={pathname === href ? "nav-item active" : "nav-item"}
                aria-current={pathname === href ? "page" : undefined}
              >
                <Icon size={19} />
                {label}
              </Link>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="privacy-note">
              <ShieldCheck size={21} />
              <strong>A space of your own</strong>
              <p>Your private documents stay out of Gemini answers.</p>
            </div>
            <button
              className="logout"
              onClick={() => {
                sessionStorage.removeItem(TOKEN_KEY);
                window.dispatchEvent(new Event("taxaura:logout"));
              }}
            >
              <LogOut size={17} />
              Sign out
            </button>
          </div>
        </aside>
        <div className="workspace-content">
          <header className="workspace-header">
            <span>Good decisions begin with clarity.</span>
            <div className="account">
              <span className="avatar">
                {user.data.full_name.slice(0, 1).toUpperCase()}
              </span>
              <span>
                {user.data.full_name}
                <small>
                  {user.data.role === "ADMIN"
                    ? "Administrator"
                    : "Personal workspace"}
                </small>
              </span>
            </div>
          </header>
          <main id="main" className="workspace-main">
            {children}
          </main>
          <footer className="workspace-footer">
            TaxAura · Educational estimates and guidance. Verify before filing.
          </footer>
        </div>
      </div>
    </UserContext>
  );
}
