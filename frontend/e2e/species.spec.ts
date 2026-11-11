import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

// SRS REF-1, REF-2, SPR-1, SPR-2: one species list, the website's fields, and
// profiles that say where their values come from.

test.describe("species", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
  });

  test("the list holds the farm's eighteen varieties with their codes and slugs", async ({ page }) => {
    await page.goto("/species");
    const rows = page.locator("tbody tr");
    await expect(rows).toHaveCount(18);

    const lionsMane = rows.filter({ hasText: "Hericium erinaceus" });
    await expect(lionsMane.getByRole("cell").nth(0)).toHaveText("LM");
    await expect(lionsMane.getByRole("cell", { name: "lion-s-mane" })).toBeVisible();
    await expect(lionsMane).toContainText("Year-round");
    await expect(lionsMane).toContainText("Available");
    await expect(lionsMane).toContainText("Restriction: legal-review");

    // Golden oyster is sold wholesale only and is not in rotation.
    const golden = rows.filter({ hasText: "Golden Oyster" });
    await expect(golden.getByRole("cell").nth(3)).toHaveText("No");
    await expect(golden.getByRole("cell").nth(5)).toHaveText("Wholesale only");
  });

  test("an administrator changes what the website may say about a variety", async ({ page }) => {
    await page.goto("/species");
    const pink = page.locator("tbody tr").filter({ hasText: "Pink Oyster" });
    await expect(pink.getByRole("cell").nth(3)).toHaveText("No");

    await pink.getByRole("button", { name: "Edit" }).click();
    await pink.getByLabel("Website tier").selectOption("in-rotation-now");
    await pink.getByLabel("Website sale").selectOption("low-stock");
    await pink.getByLabel("Growing now").check();
    await pink.getByRole("button", { name: "Save" }).click();

    await expect(page.getByRole("status").filter({ hasText: "Pink Oyster saved." })).toBeVisible();
    await expect(pink.getByRole("cell").nth(3)).toHaveText("Yes");
    await expect(pink.getByRole("cell").nth(5)).toHaveText("Low stock");
    // The slug is not offered for editing: the website keys on it.
    await expect(pink.getByRole("cell", { name: "pink-oyster" })).toBeVisible();

    // It survives a reload: it was saved, not just redrawn.
    await page.reload();
    await expect(page.locator("tbody tr").filter({ hasText: "Pink Oyster" }).getByRole("cell").nth(5)).toHaveText("Low stock");
  });

  test("an administrator adds a species and its slug is made from its name", async ({ page }) => {
    await page.goto("/species");
    const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Add species" }) });
    await form.getByLabel("Code").fill("wc");
    await form.getByLabel("Name", { exact: true }).fill("Wine Cap");
    await form.getByLabel("Latin name").fill("Stropharia rugosoannulata");
    await form.getByRole("button", { name: "Add species" }).click();

    await expect(page.getByRole("status").filter({ hasText: "Wine Cap added with code WC." })).toBeVisible();
    const row = page.locator("tbody tr").filter({ hasText: "Stropharia rugosoannulata" });
    await expect(row.getByRole("cell", { name: "wine-cap" })).toBeVisible();
    await expect(row.getByRole("cell").nth(5)).toHaveText("Hidden");

    // A code that would not fit a label is refused in plain words.
    await form.getByLabel("Code").fill("WC");
    await form.getByLabel("Name", { exact: true }).fill("Wine Cap");
    await form.getByRole("button", { name: "Add species" }).click();
    await expect(page.getByRole("alert").filter({ hasText: /already (exists|uses)/ })).toBeVisible();
  });

  test("the reference page marks the profiles that come from research", async ({ page }) => {
    await page.goto("/reference/species");
    const cards = page.locator("article.sp-card");
    await expect(cards).toHaveCount(18);

    const pioppino = cards.filter({ hasText: "Pioppino" });
    await expect(pioppino.getByText("Researched", { exact: true })).toBeVisible();
    await expect(pioppino).toContainText("Researched from suppliers and papers");
    await expect(pioppino).toContainText("PP");

    const shiitake = cards.filter({ hasText: "Lentinula edodes" });
    await expect(shiitake.getByText("Researched", { exact: true })).toHaveCount(0);
    await expect(shiitake).toContainText("From the farm's own sources.");
  });
});
