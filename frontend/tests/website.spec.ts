import { test, expect, type Page } from "@playwright/test";
async function login(page: Page, email = "alice@example.com") {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel(/^Password/).fill("correct-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(
    page.getByRole("heading", { name: /A clearer picture/ }),
  ).toBeVisible();
}
async function upload(page: Page, name = "form16.pdf") {
  await page.getByLabel("Choose document").setInputFiles({
    name,
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\nTest document"),
  });
}
const browserErrors = new WeakMap<Page, string[]>();
test.afterEach(async ({ page }) => {
  expect(browserErrors.get(page) || []).toEqual([]);
});
test.beforeEach(async ({ request, page }) => {
  const errors: string[] = [];
  browserErrors.set(page, errors);
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      /Content Security Policy|hydration/i.test(message.text())
    )
      errors.push(message.text());
  });
  await request.post("http://127.0.0.1:8899/__reset");
});
test("landing, nonce CSP, mobile layout, legacy links, and registration", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const response = await page.goto("/");
  expect(response?.headers()["content-security-policy"]).toContain("'nonce-");
  expect(response?.headers()["content-security-policy"]).not.toContain(
    "unsafe-inline",
  );
  await expect(
    page.getByRole("heading", { name: /Less paperwork/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/home-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: "test-results/home-mobile.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Create your workspace" }).click();
  await page.getByLabel("Full name").fill("New Member");
  await page.getByLabel("Email address").fill("new@example.com");
  await page.getByLabel(/^Password/).fill("correct-password");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "A clearer picture, New." }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/dashboard-mobile.png",
    fullPage: true,
  });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.goto("/app/dashboard.html");
  await expect(page).toHaveURL(/\/dashboard$/);
  expect(errors).toEqual([]);
});
test("login errors, protected routes, sign out and cache isolation", async ({
  page,
}) => {
  await page.goto("/documents");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Email address").fill("alice@example.com");
  await page.getByLabel(/^Password/).fill("wrong");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".notice.error")).toContainText(
    "Invalid email or password",
  );
  await login(page);
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await upload(page);
  await expect(
    page.getByRole("cell", { name: /form16.pdf PDF document/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(
    await page.evaluate(() => sessionStorage.getItem("taxaura_access_token")),
  ).toBeNull();
  await login(page, "admin@example.com");
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await expect(
    page.getByText("Your uploaded documents will appear here."),
  ).toBeVisible();
  await expect(page.getByText("form16.pdf")).toHaveCount(0);
});
test("multipart upload, status polling, preview, duplicate error, retry and deletion", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await page.getByLabel("Choose document").setInputFiles({
    name: "script.html",
    mimeType: "text/html",
    buffer: Buffer.from("bad"),
  });
  await expect(page.locator(".notice.error")).toContainText("Choose a PDF");
  await upload(page);
  await expect(
    page.getByRole("button", { name: "View form16.pdf" }),
  ).toBeVisible({ timeout: 10_000 });
  await page.getByRole("button", { name: "View form16.pdf" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Annual salary: 1200000",
  );
  await expect(page.getByRole("dialog")).toContainText(
    "<script>not executable</script>",
  );
  await page.getByRole("button", { name: "Close preview" }).click();
  await upload(page);
  await expect(page.locator(".notice.error")).toContainText(
    "already been uploaded",
  );
  await upload(page, "failed.pdf");
  await page.getByRole("button", { name: "Retry failed.pdf" }).click();
  await expect(
    page.getByRole("button", { name: "View failed.pdf" }),
  ).toBeVisible({ timeout: 10_000 });
  await page.screenshot({
    path: "test-results/documents-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Delete form16.pdf" }).click();
  await page
    .getByRole("button", { name: "Delete document", exact: true })
    .click();
  await expect(page.getByText("Document deleted.")).toBeVisible();
  await expect(
    page.getByRole("cell", { name: /form16.pdf PDF document/ }),
  ).toHaveCount(0);
});
test("tax comparison and source-linked chat with privacy mode and error recovery", async ({
  page,
}) => {
  await login(page);
  await page.getByRole("link", { name: "Tax calculator" }).click();
  await page.getByLabel("Annual gross salary").fill("1200000");
  await page.getByRole("button", { name: "Compare regimes" }).click();
  await expect(
    page.getByRole("heading", {
      name: "The new regime has the lower estimate.",
    }),
  ).toBeVisible();
  await expect(page.getByText("₹1,04,000", { exact: true })).toHaveCount(2);
  await page.getByRole("link", { name: "Tax assistant" }).click();
  await page
    .getByRole("button", { name: "How does the standard deduction work?" })
    .click();
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.getByText("Gemini answer", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Reviewed tax guidance" }),
  ).toHaveAttribute("href", "https://www.incometax.gov.in/");
  await expect(page.locator('a[href^="javascript:"]')).toHaveCount(0);
  await page.getByLabel("Include my documents").check();
  await page.getByLabel("Your tax question").fill("What is in my document?");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(
    page.getByText("Local source excerpts", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Your tax question").fill("test failure please");
  await page.getByRole("button", { name: "Send question" }).click();
  await expect(page.locator(".notice.error")).toContainText(
    "Please try your question again",
  );
  await expect(page.getByLabel("Your tax question")).toHaveValue(
    "test failure please",
  );
});
test("administrator access and knowledge ingestion", async ({ page }) => {
  await login(page);
  await page.goto("/admin");
  await expect(
    page.getByRole("heading", { name: "Administrator access required" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "admin@example.com");
  await page.getByRole("link", { name: "Knowledge admin" }).click();
  await page.getByLabel("Source name").fill("Reviewed guidance");
  await page.getByLabel("Source URL").fill("https://www.incometax.gov.in/");
  await page
    .getByLabel("Reviewed content")
    .fill(
      "Reviewed public tax guidance for this assessment year. This is controlled test content only.",
    );
  await page.getByRole("button", { name: "Add knowledge source" }).click();
  await expect(page.getByRole("status")).toContainText("Added 2 chunks");
});
test("expired sessions and backend errors remain actionable", async ({
  page,
  request,
}) => {
  await login(page);
  await request.post("http://127.0.0.1:8899/__expire");
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
  await request.post("http://127.0.0.1:8899/__reset");
  await request.post("http://127.0.0.1:8899/__fail-documents");
  await login(page);
  await page.getByRole("link", { name: "Documents", exact: true }).click();
  await expect(page.locator(".notice.error")).toContainText(
    "Documents temporarily unavailable",
  );
});
test("proxy passes authentication failures and rejects unsupported paths", async ({
  request,
}) => {
  expect((await request.get("/api/v1/users/me")).status()).toBe(401);
  expect((await request.get("/api/v1/unknown")).status()).toBe(404);
  expect(
    (await request.get("/api/v1/documents")).headers()["cache-control"],
  ).toContain("no-store");
  expect((await request.get("/app/package.json")).status()).toBe(404);
});
