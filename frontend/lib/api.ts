export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export const TOKEN_KEY = "taxaura_access_token";
export function token() {
  return typeof window === "undefined"
    ? null
    : sessionStorage.getItem(TOKEN_KEY);
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  const accessToken = token();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !(options.body instanceof URLSearchParams)
  )
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/")) {
      sessionStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event("taxaura:logout"));
    }
    const body = await response.json().catch(() => null);
    const message =
      typeof body?.detail === "string"
        ? body.detail
        : Array.isArray(body?.detail)
          ? body.detail.map((e: { msg: string }) => e.msg).join(". ")
          : "Request failed. Please try again.";
    throw new ApiError(message, response.status);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "USER" | "ADMIN";
};
export type AuthResponse = { access_token: string; user: User };
export type Document = {
  id: string;
  filename: string;
  mime_type: string;
  processing_status: "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";
  created_at: string;
  processing_error: string | null;
};
export type TaxResult = {
  assessment_year: string;
  old_regime: Regime;
  new_regime: Regime;
  recommended_regime: "OLD" | "NEW";
  estimated_saving: string;
  disclaimer: string;
};
type Regime = {
  taxable_income: string;
  tax_before_cess: string;
  cess: string;
  total_tax: string;
};
export type Answer = {
  answer: string;
  mode: "extractive" | "generated";
  sources: { source_name: string; source_url: string | null }[];
};
export function money(value: string | number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value));
}
