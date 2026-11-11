import { expect, test, type Page } from "@playwright/test";
import { ADMIN, E2E_PASSWORD, OPERATOR, signIn, submitSignIn } from "./helpers";

// SRS USR-1 to USR-4: sign-in, sign-out, roles, and a session that has ended.

// Next.js keeps a route announcer of its own with role="alert", so the app's
// messages are found by role and text together.
const alert = (page: Page, text: string) => page.getByRole("alert").filter({ hasText: text });
const status = (page: Page, text: string) => page.getByRole("status").filter({ hasText: text });

test.describe("sign-in", () => {
  test("a signed-out browser is sent to sign in and then back to the page it asked for", async ({ page }) => {
    await page.goto("/reports");
    await expect(page).toHaveURL(/\/login\?next=%2Freports$/);
    // Nothing of the app is drawn before sign-in: no menu, no data.
    await expect(page.getByRole("navigation")).toHaveCount(0);

    await submitSignIn(page, ADMIN.email);
    await expect(page).toHaveURL(/\/reports$/);
    await expect(page.getByRole("link", { name: ADMIN.name })).toBeVisible();
  });

  test("a wrong password is refused with a plain sentence", async ({ page }) => {
    await page.goto("/login");
    await submitSignIn(page, ADMIN.email, "not the password");
    await expect(alert(page, "The email or password is not right.")).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);

    // The API itself refuses, whatever the screen shows.
    const response = await page.request.get("/api/bags");
    expect(response.status()).toBe(401);
  });

  test("signing out ends the session", async ({ page }) => {
    await signIn(page);
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login$/);

    expect((await page.request.get("/api/auth/me")).status()).toBe(401);
    await page.goto("/bags");
    await expect(page).toHaveURL(/\/login\?next=%2Fbags$/);
  });

  test("a session that has ended sends the next action to sign in", async ({ page, context }) => {
    await signIn(page);
    await page.goto("/sterilization-runs");
    await expect(page.getByRole("heading", { name: "Sterilization Runs (Autoclave)" })).toBeVisible();
    // Let the page finish loading, so that the request below is the first one after the session ends.
    await page.waitForLoadState("networkidle");

    // The server no longer knows this session (expired, or the user was deactivated).
    await context.clearCookies();
    await page.getByLabel("Run code contains").fill("26");
    await expect(page).toHaveURL(/\/login\?next=%2Fsterilization-runs$/);
  });
});

test.describe("roles", () => {
  test("an operator works the farm but cannot reach setup or users", async ({ page }) => {
    await signIn(page, OPERATOR);
    const menu = page.getByRole("navigation", { name: "Main" });
    await expect(menu.getByRole("link", { name: "Harvest" })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Reports" })).toBeVisible();
    await expect(menu.getByRole("link", { name: "Users" })).toHaveCount(0);

    // The species list can be read by anyone signed in, and changed only by an administrator.
    await menu.getByRole("link", { name: "Species", exact: true }).click();
    await expect(page.getByRole("heading", { name: "All species" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "lion-s-mane" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Add a species" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Edit" })).toHaveCount(0);

    // Typing the address does not help, and neither does calling the API.
    await page.goto("/users");
    await expect(alert(page, "Only an administrator can manage users.")).toBeVisible();
    expect((await page.request.get("/api/users")).status()).toBe(403);
    const write = await page.request.post("/api/species", {
      data: { code: "ZZ", name: "Not allowed" },
      headers: { Origin: "http://localhost:3001" },
    });
    expect(write.status()).toBe(403);

    // Reports are open to an operator.
    await page.goto("/reports");
    await expect(page.getByRole("heading", { name: "Pasteurization Run Outcomes" })).toBeVisible();
  });

  test("an administrator adds a user, who must choose a password at first sign-in", async ({ page, browser }) => {
    const email = `picker-${Date.now()}@e2e.test`;
    await signIn(page);
    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Users" }).click();
    await expect(page.getByRole("heading", { name: "Users", exact: true })).toBeVisible();

    const addForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Add user" }) });
    await addForm.getByLabel("Name").fill("Pat Picker");
    await addForm.getByLabel("Email").fill(email);
    await addForm.getByLabel("Role").selectOption("operator");
    await addForm.getByLabel("First password").fill("first password 1");
    await addForm.getByRole("button", { name: "Add user" }).click();
    await expect(status(page, "Pat Picker can now sign in.")).toBeVisible();
    await expect(page.locator("tbody tr").filter({ hasText: email })).toContainText("Active");

    // Pat, on another device.
    const patsContext = await browser.newContext();
    const pat = await patsContext.newPage();
    await pat.goto("/login");
    await submitSignIn(pat, email, "first password 1");
    await expect(pat).toHaveURL(/\/account$/);
    await expect(status(pat, "Choose your own before you continue.")).toBeVisible();
    // Until then every other page leads back here.
    await pat.goto("/bags");
    await expect(pat).toHaveURL(/\/account$/);

    await pat.getByLabel("Current password").fill("first password 1");
    await pat.getByLabel("New password", { exact: true }).fill("pats own password");
    await pat.getByLabel("New password again").fill("pats own password");
    await pat.getByRole("button", { name: "Change password" }).click();
    await expect(pat.getByRole("heading", { name: "Today's production picture in one place." })).toBeVisible();
    await expect(pat.getByRole("link", { name: "Pat Picker" })).toBeVisible();

    // The administrator deactivates the account: Pat's open session stops working.
    const row = page.locator("tbody tr").filter({ hasText: email });
    await row.getByRole("button", { name: "Deactivate" }).click();
    await expect(status(page, "Pat Picker can no longer sign in.")).toBeVisible();
    await expect(row).toContainText("Deactivated");
    await pat.goto("/bags");
    await expect(pat).toHaveURL(/\/login\?next=%2Fbags$/);
    await submitSignIn(pat, email, "pats own password");
    await expect(alert(pat, "The email or password is not right.")).toBeVisible();
    await patsContext.close();
  });

  test("an event shows who entered it", async ({ page }) => {
    await signIn(page);
    // Any bag will do; make one unlabeled spawn record through the API as the signed-in admin.
    const origin = { Origin: "http://localhost:3001" };
    const code = (await (await page.request.get("/api/sterilization-runs/next-code")).json()).run_code;
    const recipes = await (await page.request.get("/api/spawn-recipes")).json();
    const grains = await (await page.request.get("/api/grain-types")).json();
    const run = await (
      await page.request.post("/api/sterilization-runs", {
        headers: origin,
        data: {
          run_code: code,
          spawn_recipe_id: recipes[0].spawn_recipe_id,
          grain_type_id: grains[0].grain_type_id,
          unloaded_at: new Date().toISOString(),
          bag_count: 1,
        },
      })
    ).json();
    const bags = await (
      await page.request.post("/api/bags/spawn", {
        headers: origin,
        data: { sterilization_run_id: run.sterilization_run_id, bag_count: 1 },
      })
    ).json();

    await page.goto(`/bags/${bags[0].bag_id}`);
    const timeline = page.getByRole("heading", { name: "Lifecycle Timeline" }).locator("xpath=following-sibling::table[1]");
    await expect(timeline.getByRole("columnheader", { name: "Entered by" })).toBeVisible();
    await expect(timeline.locator("tbody tr").first()).toContainText(ADMIN.name);
  });
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

  test("sign-in, account and sign-out fit the screen and work by touch", async ({ page }) => {
    await page.goto("/login");
    // Nothing is cut off or needs sideways scrolling.
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBe(0);
    for (const control of [page.getByLabel("Email"), page.getByLabel("Password"), page.getByRole("button", { name: "Sign in" })]) {
      const box = await control.boundingBox();
      expect(box!.height).toBeGreaterThanOrEqual(44);
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(390);
    }

    await page.getByLabel("Email").fill(OPERATOR.email);
    await page.getByLabel("Password").fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).tap();
    await expect(page.getByRole("link", { name: OPERATOR.name })).toBeVisible();

    // The menu stays out of the way until it is asked for, and leaves the page readable.
    const menu = page.getByRole("navigation", { name: "Main" });
    await expect(menu).toBeHidden();
    const header = await page.locator("header").boundingBox();
    expect(header!.height).toBeLessThan(120);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);

    await page.getByRole("button", { name: "Menu" }).tap();
    await expect(menu.getByRole("link", { name: "Harvest" })).toBeVisible();
    const harvestLink = await menu.getByRole("link", { name: "Harvest" }).boundingBox();
    expect(harvestLink!.height).toBeGreaterThanOrEqual(40);
    await menu.getByRole("link", { name: "Harvest" }).tap();
    await expect(page.getByRole("heading", { name: "Harvest" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Main" })).toBeHidden();

    await page.getByRole("link", { name: OPERATOR.name }).tap();
    await expect(page.getByRole("heading", { name: "Your account" })).toBeVisible();
    await expect(page.getByText(`${OPERATOR.name} · ${OPERATOR.email} · Operator`)).toBeVisible();

    await page.getByRole("button", { name: "Sign out" }).tap();
    await expect(page).toHaveURL(/\/login$/);
  });
});
