import { test, expect } from "@playwright/test";

// A valid one-page text PDF. The real backend parses this with pypdf and indexes it in Chroma.
function salaryPdf() {
  const stream =
    "BT /F1 14 Tf 50 750 Td (Form 16 salary document. Annual salary is 1200000 rupees.) Tj ET";
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const start = Buffer.byteLength(pdf);
  pdf += `xref\n0 6\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((offset) => `${String(offset).padStart(10, "0")} 00000 n \n`)
    .join("")}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${start}\n%%EOF`;
  return Buffer.from(pdf);
}

test("real browser → Next.js → FastAPI → PostgreSQL and Chroma document and tax journey", async ({
  page,
  request,
}) => {
  const email = `e2e-${Date.now()}@example.com`;
  const password = "ci-member-password-123";
  await page.goto("/register");
  await page.getByLabel("Full name").fill("Browser Journey");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "A clearer picture, Browser." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  const accepted = page.waitForResponse(
    (response) =>
      response.url().endsWith("/documents/upload") &&
      response.request().method() === "POST",
  );
  await page
    .getByLabel("Choose document")
    .setInputFiles({
      name: "form16-e2e.pdf",
      mimeType: "application/pdf",
      buffer: salaryPdf(),
    });
  const uploaded = await accepted;
  expect(uploaded.status()).toBe(202);
  const { document_id: id } = await uploaded.json();
  await expect(
    page.getByRole("button", { name: "View form16-e2e.pdf" }),
  ).toBeVisible({ timeout: 80_000 });
  await page.getByRole("button", { name: "View form16-e2e.pdf" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Annual salary is 1200000",
  );
  await page.getByRole("button", { name: "Close preview" }).click();
  // Another real account must not read or delete this document through the proxy.
  const outsider = await request.post("/api/v1/auth/register", {
    data: { email: `other-${email}`, full_name: "Other Member", password },
  });
  expect(outsider.ok()).toBeTruthy();
  const otherToken = (await outsider.json()).access_token;
  expect(
    (
      await request.get(`/api/v1/documents/${id}/text`, {
        headers: { Authorization: `Bearer ${otherToken}` },
      })
    ).status(),
  ).toBe(404);
  expect(
    (
      await request.delete(`/api/v1/documents/${id}`, {
        headers: { Authorization: `Bearer ${otherToken}` },
      })
    ).status(),
  ).toBe(404);
  await page.getByRole("link", { name: "Tax calculator" }).click();
  await page.getByLabel("Annual gross salary").fill("1200000");
  await page.getByRole("button", { name: "Compare regimes" }).click();
  await expect(
    page.getByRole("heading", {
      name: "The new regime has the lower estimate.",
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Tax assistant" }).click();
  await page
    .getByLabel("Your tax question")
    .fill("What is the section 87A rebate for AY 2026-27?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.getByRole("link", { name: /Income Tax Department/ }).first(),
  ).toBeVisible({ timeout: 30_000 });
  await page.getByLabel("Include my documents").check();
  await page
    .getByLabel("Your tax question")
    .fill("What salary is recorded in my Form 16 document?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.locator(".sources").getByText("Your document: form16-e2e.pdf", { exact: true }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByText("Local source excerpts", { exact: true }).last(),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/real-stack-assistant.png",
    fullPage: true,
  });
  // Sign in again to prove account and documents persisted beyond client cache.
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await page.getByRole("button", { name: "Delete form16-e2e.pdf" }).click();
  await page
    .getByRole("button", { name: "Delete document", exact: true })
    .click();
  await expect(page.getByText("Document deleted.")).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("Your uploaded documents will appear here."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
});

test("real administrator can ingest reviewed knowledge", async ({ page }) => {
  test.skip(
    !process.env.E2E_ADMIN_EMAIL || !process.env.E2E_ADMIN_PASSWORD,
    "Provide an admin in the disposable test stack.",
  );
  await page.goto("/login");
  await page.getByLabel("Email address").fill(process.env.E2E_ADMIN_EMAIL!);
  await page.getByLabel(/^Password/).fill(process.env.E2E_ADMIN_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "Knowledge admin" }).click();
  await page.getByLabel("Source name").fill(`CI knowledge ${Date.now()}`);
  await page.getByLabel("Source URL").fill("https://www.incometax.gov.in/");
  await page
    .getByLabel("Reviewed content")
    .fill(
      "This test source exists only in a disposable test database. Confirm the applicable assessment year and eligibility using official tax guidance before filing.",
    );
  await page.getByRole("button", { name: "Add knowledge source" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Semantic search is ready.",
    { timeout: 30_000 },
  );
});
