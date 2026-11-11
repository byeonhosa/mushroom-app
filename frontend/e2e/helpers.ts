import { expect, type Page } from "@playwright/test";

// Accounts created by backend/scripts/serve_e2e.py.
export const E2E_PASSWORD = "e2e test password";
export const ADMIN = { email: "admin@e2e.test", name: "Ada Admin" };
export const OPERATOR = { email: "operator@e2e.test", name: "Olly Operator" };

/** Fill in the sign-in form. The caller says what should happen next. */
export async function submitSignIn(page: Page, email: string, password: string = E2E_PASSWORD) {
  await expect(page.getByRole("heading", { name: "Mushroom Farm App" })).toBeVisible();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

/** Sign in through the screen and wait for the dashboard. */
export async function signIn(page: Page, user: { email: string; name: string } = ADMIN) {
  await page.goto("/login");
  await submitSignIn(page, user.email);
  await expect(page.getByRole("heading", { name: "Today's production picture in one place." })).toBeVisible();
  await expect(page.getByRole("link", { name: user.name })).toBeVisible();
}
