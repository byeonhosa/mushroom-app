import { expect, test } from "@playwright/test";
import { OPERATOR, signIn } from "./helpers";

// SRS REF-3 to REF-6, REF-10, REF-12, REF-14: recipes, fill profiles, grain
// types and liquid cultures can be added, changed and switched off from a
// screen, and what is switched off is no longer offered for new work.

test.describe("reference data", () => {
  test("an administrator sets up a recipe and a fill profile and uses them for a mix lot", async ({ page }) => {
    await signIn(page);
    await page.goto("/recipes");

    const recipes = page.getByRole("region", { name: "Substrate recipes" });
    await recipes.getByLabel("Name").fill("Hardwood and bran");
    await recipes.getByLabel("Code").fill("hb");
    await recipes.getByLabel("Description").fill("80% oak, 20% wheat bran");
    await recipes.getByRole("button", { name: "Add substrate recipe" }).click();
    await expect(recipes.getByRole("status")).toHaveText("Added Hardwood and bran.");
    await expect(recipes.getByRole("row").filter({ hasText: "Hardwood and bran" })).toContainText("HB");

    const profiles = page.getByRole("region", { name: "Fill profiles" });
    await profiles.getByLabel("Name").fill("10 lb block");
    await profiles.getByLabel("Dry weight per bag").fill("1.9");
    await profiles.getByLabel("Water per bag").fill("2.6");
    await profiles.getByRole("button", { name: "Add fill profile" }).click();
    await expect(profiles.getByRole("status")).toHaveText("Added 10 lb block.");
    await expect(profiles.getByRole("row").filter({ hasText: "10 lb block" })).toContainText("1.9 kg");

    // Both are offered where a mix lot is recorded.
    await page.goto("/mix-lots");
    await expect(page.getByRole("option", { name: /Hardwood and bran/ })).toBeAttached();
    await expect(page.getByRole("option", { name: /10 lb block/ })).toBeAttached();
  });

  test("an administrator corrects a spawn recipe and switches one off", async ({ page }) => {
    await signIn(page);
    await page.goto("/recipes");
    const spawn = page.getByRole("region", { name: "Spawn recipes" });

    await spawn.getByLabel("Code").fill("MILLET-1");
    await spawn.getByLabel("Description").fill("Millet");
    await spawn.getByRole("button", { name: "Add spawn recipe" }).click();
    await expect(spawn.getByRole("status")).toHaveText("Added MILLET-1.");

    await spawn.getByRole("button", { name: "Edit MILLET-1" }).click();
    await spawn.getByLabel("Description of MILLET-1").fill("Millet, 1% gypsum");
    await spawn.getByRole("button", { name: "Save" }).click();
    await expect(spawn.getByRole("status")).toHaveText("Saved MILLET-1.");
    await expect(spawn.getByRole("row").filter({ hasText: "MILLET-1" })).toContainText("Millet, 1% gypsum");

    await spawn.getByRole("button", { name: "Deactivate MILLET-1" }).click();
    await expect(spawn.getByRole("status")).toContainText("MILLET-1 is deactivated.");
    await expect(spawn.getByRole("row").filter({ hasText: "MILLET-1" })).toContainText("Deactivated");

    // Still on the list here; no longer offered for a new sterilization run.
    await page.goto("/sterilization-runs");
    await expect(page.getByRole("option", { name: "SR1", exact: true })).toBeAttached();
    await expect(page.getByRole("option", { name: "MILLET-1" })).toHaveCount(0);

    // A second recipe with a code already taken is refused in words.
    await page.goto("/recipes");
    const again = page.getByRole("region", { name: "Spawn recipes" });
    await again.getByLabel("Code").fill("MILLET-1");
    await again.getByRole("button", { name: "Add spawn recipe" }).click();
    await expect(again.getByRole("alert")).toContainText("already exists");
  });

  test("an operator sees recipes and cannot change them", async ({ page }) => {
    await signIn(page, OPERATOR);
    await page.goto("/recipes");
    await expect(page.getByText("Only an administrator can change them.")).toBeVisible();
    const spawn = page.getByRole("region", { name: "Spawn recipes" });
    await expect(spawn.getByRole("row").filter({ hasText: "SR1" })).toBeVisible();
    await expect(spawn.getByRole("button")).toHaveCount(0);
    await expect(page.getByRole("button", { name: /^Add / })).toHaveCount(0);
  });

  test("a culture names its parent, and a retired culture leaves the pick list", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await signIn(page);
    await page.goto("/liquid-cultures");

    await page.getByLabel("Culture code").fill("LC-LM-E2E-2");
    await page.getByLabel("Species").selectOption({ label: "Lion's Mane (LM)" });
    const parent = page.getByRole("combobox", { name: "Made from" });
    const firstParent = await parent.locator("option").nth(1).textContent();
    await parent.selectOption({ index: 1 });
    await page.getByRole("button", { name: "Add liquid culture" }).click();
    await expect(page.getByRole("status")).toHaveText("Added LC-LM-E2E-2.");

    const row = page.getByRole("row").filter({ hasText: "LC-LM-E2E-2" });
    await expect(row.getByRole("cell").nth(2)).toHaveText(firstParent ?? "");

    await page.getByRole("button", { name: "Deactivate LC-LM-E2E-2" }).click();
    await expect(page.getByRole("status")).toContainText("LC-LM-E2E-2 is deactivated.");
    await expect(row).toContainText("Deactivated");

    await page.goto("/events/spawn-inoculation");
    await expect(page.getByRole("option", { name: /LC-LM-E2E-2/ })).toHaveCount(0);

    // Nothing on these screens is wider than the phone.
    for (const path of ["/liquid-cultures", "/recipes", "/grain-types"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, path).toBeLessThanOrEqual(0);
    }
  });
});
