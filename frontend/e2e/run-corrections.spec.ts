import { expect, test, type Page } from "@playwright/test";
import { OPERATOR, signIn } from "./helpers";

// SRS RUN-5: an administrator corrects a run after creating it. The server
// refuses a correction that would falsify the run's bags, in words.

async function newPasteurizationRun(page: Page, bagCount: number) {
  await page.goto("/pasteurization-runs");
  const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Create Run" }) });
  await form.getByLabel("Mix Lot").selectOption({ label: "LOT-STD-001" });
  await form.getByLabel("Substrate Recipe").selectOption({ label: "Masters Mix (MM)" });
  await form.getByLabel("Bag Count").fill(String(bagCount));
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  await form
    .getByLabel("Unloaded At")
    .fill(`${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`);
  const runCodeField = form.getByRole("textbox", { name: "Run Code", exact: true });
  await expect(runCodeField).toHaveValue(/^\d{6}[A-Z]$/);
  const runCode = await runCodeField.inputValue();
  await form.getByRole("button", { name: "Create Run" }).click();
  await page.getByRole("link", { name: runCode }).click();
  await expect(page.getByText(`Run Code: ${runCode}`)).toBeVisible();
  return runCode;
}

test.describe("run corrections", () => {
  test("an administrator corrects a run, and is told why a correction is refused", async ({ page }) => {
    await signIn(page);
    await newPasteurizationRun(page, 6);
    const runUrl = page.url();
    const correction = page.getByRole("region", { name: "Correct this run" });

    // The planned count and a note are put right.
    await correction.getByRole("button", { name: "Correct this run" }).click();
    await expect(correction.getByLabel("Planned bag count")).toHaveValue("6");
    await correction.getByLabel("Planned bag count").fill("8");
    await correction.getByLabel("Notes").fill("Two more bags than planned");
    await correction.getByRole("button", { name: "Save correction" }).click();
    await expect(correction.getByRole("status")).toHaveText("Run corrected.");
    await expect(page.getByText("Planned Bag Count: 8")).toBeVisible();

    // Saving without a change says so and sends nothing.
    await correction.getByRole("button", { name: "Correct this run" }).click();
    await correction.getByRole("button", { name: "Save correction" }).click();
    await expect(correction.getByRole("status")).toHaveText("Nothing was changed.");

    // Five bag records now exist: the count cannot be put below them.
    const records = page.locator("form").filter({ has: page.getByRole("heading", { name: "Create Unlabeled Substrate Records" }) });
    await records.getByLabel("Record count").fill("5");
    await records.getByRole("button", { name: "Create Unlabeled Records" }).click();
    await expect(page.getByText(/Created 5 unlabeled substrate record/)).toBeVisible();

    await correction.getByRole("button", { name: "Correct this run" }).click();
    await correction.getByLabel("Planned bag count").fill("3");
    await correction.getByRole("button", { name: "Save correction" }).click();
    await expect(correction.getByRole("alert")).toContainText("already has 5 bag record(s)");
    await correction.getByRole("button", { name: "Cancel" }).click();

    // It survived a reload: it was saved, not just redrawn.
    await page.goto(runUrl);
    await expect(page.getByText("Planned Bag Count: 8")).toBeVisible();
  });

  test("an operator is not offered corrections", async ({ page }) => {
    await signIn(page);
    await newPasteurizationRun(page, 2);
    const runUrl = page.url();
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);

    await signIn(page, OPERATOR);
    await page.goto(runUrl);
    await expect(page.getByText("Planned Bag Count: 2")).toBeVisible();
    await expect(page.getByRole("region", { name: "Correct this run" })).toHaveCount(0);
  });
});
