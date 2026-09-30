"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, AuthResponse, TOKEN_KEY } from "@/lib/api";
import { Brand, ErrorMessage } from "./ui";
import { ArrowRight, ShieldCheck } from "lucide-react";
export function AuthForm({ register = false }: { register?: boolean }) {
  const router = useRouter();
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (data: FormData) => {
      const email = String(data.get("email")).trim();
      const password = String(data.get("password"));
      return api<AuthResponse>(register ? "/auth/register" : "/auth/login", {
        method: "POST",
        body: register
          ? JSON.stringify({
              email,
              password,
              full_name: String(data.get("full_name")).trim(),
            })
          : new URLSearchParams({ username: email, password }),
      });
    },
    onSuccess: async (data) => {
      await client.cancelQueries();
      client.clear();
      sessionStorage.setItem(TOKEN_KEY, data.access_token);
      router.replace("/dashboard");
    },
  });
  return (
    <main id="main" className="auth-page">
      <div className="auth-story">
        <Brand />
        <div>
          <p className="eyebrow">A LITTLE CLARITY GOES A LONG WAY</p>
          <h1>
            Your next chapter.
            <br />
            <em>Less tax stress.</em>
          </h1>
          <p>
            A simple space for your documents, estimates, and the questions in
            between.
          </p>
        </div>
        <p className="quiet">
          <ShieldCheck size={19} /> Your documents are accessible only to your
          account.
        </p>
      </div>
      <div className="auth-form-area">
        <Link className="back-link" href="/">
          ← Back to home
        </Link>
        <div className="auth-card">
          <p className="eyebrow">WELCOME{register ? " TO TAXAURA" : " BACK"}</p>
          <h2>
            {register ? "Make room for clarity." : "Your workspace awaits."}
          </h2>
          <p>
            {register
              ? "Create an account to get started."
              : "Sign in to pick up where you left off."}
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              mutation.mutate(new FormData(e.currentTarget));
            }}
          >
            {register && (
              <label>
                Full name
                <input
                  name="full_name"
                  autoComplete="name"
                  required
                  minLength={2}
                  maxLength={120}
                  placeholder="Your name"
                />
              </label>
            )}
            <label>
              Email address
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@example.com"
              />
            </label>
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
                required
                minLength={register ? 12 : 1}
                maxLength={128}
              />
              {register && <small>Use at least 12 characters.</small>}
            </label>
            <ErrorMessage error={mutation.error} />
            <button className="button full" disabled={mutation.isPending}>
              {mutation.isPending
                ? "Please wait…"
                : register
                  ? "Create account"
                  : "Sign in"}
              <ArrowRight size={17} />
            </button>
          </form>
          <p className="auth-switch">
            {register ? "Already have an account?" : "New to TaxAura?"}{" "}
            <Link href={register ? "/login" : "/register"}>
              {register ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
        <p className="quiet">
          Educational guidance. Your financial decisions stay yours.
        </p>
      </div>
    </main>
  );
}
