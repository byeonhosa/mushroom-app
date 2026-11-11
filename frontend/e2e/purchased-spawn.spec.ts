import { expect, test, type Locator, type Page } from "@playwright/test";
import { OPERATOR, signIn } from "./helpers";

// SRS REF-11, INO-6, INO-7: the farm inoculates its substrate from purchased
// grain spawn. A lot is recorded once and then serves any number of sessions.

const status = (page: Page, text: string | RegExp) => page.getByRole("status").filter({ hasText: text });
// A select inside its label: found by role and exact name, as its options are part of the label's text.
const lotPicker = (scope: Page | Locator) => scope.getByRole("combobox", { name: "Purchased spawn lot", exact: true });

async function recordLot(page: Page, vendor: string) {
  await page.goto("/purchased-spawn-lots");
  const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Record lot" }) });
  await form.getByLabel("Supplier", { exact: true }).fill(vendor);
  await form.getByLabel("Supplier's lot number").fill("NS-48213");
  await form.getByLabel("Species").selectOption({ label: "Blue Oyster (BO)" });
  await form.getByLabel("Grain").selectOption({ label: "Rye" });
  await form.getByLabel("Quantity").fill("4");
  await form.getByRole("button", { name: "Record lot" }).click();
  await expect(status(page, /Lot PL-BO-\d{6}[A-Z] recorded\./)).toBeVisible();
  const row = page.locator("tbody tr").filter({ hasText: vendor });
  const lotCode = (await row.getByRole("cell").first().innerText()).split("\n")[0].trim();
  expect(lotCode).toMatch(/^PL-BO-\d{6}[A-Z]$/);
  return lotCode;
}

async function newPasteurizationRun(page: Page, bagCount: number) {
  await page.goto("/pasteurization-runs");
  const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Create Run" }) });
  await form.getByLabel("Mix Lot").selectOption({ label: "LOT-STD-001" });
  await form.getByLabel("Substrate Recipe").selectOption({ label: "Masters Mix (MM)" });
  await form.getByLabel("Bag Count").fill(String(bagCount));
  const now = new Date();
  const pad = (value: number) => String(value).padStart(2, "0");
  const unloaded = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
  await form.getByLabel("Unloaded At").fill(unloaded);
  const runCodeField = form.getByRole("textbox", { name: "Run Code", exact: true });
  await expect(runCodeField).toHaveValue(/^\d{6}[A-Z]$/);
  const runCode = await runCodeField.inputValue();
  await form.getByRole("button", { name: "Create Run" }).click();
  await page.getByRole("link", { name: runCode }).click();
  await expect(page.getByText(`Run Code: ${runCode}`)).toBeVisible();

  const records = page.locator("form").filter({ has: page.getByRole("heading", { name: "Create Unlabeled Substrate Records" }) });
  await records.getByLabel("Record count").fill(String(bagCount));
  await records.getByRole("button", { name: "Create Unlabeled Records" }).click();
  await expect(page.getByText(new RegExp(`Created ${bagCount} unlabeled substrate record`))).toBeVisible();
  return runCode;
}

test.describe("purchased spawn", () => {
  test("a lot is recorded, inoculates two sessions, and is then marked used up", async ({ page }) => {
    await signIn(page);
    const vendor = `North Spore ${Date.now()}`;
    const lotCode = await recordLot(page, vendor);
    const lotRow = page.locator("tbody tr").filter({ hasText: vendor });
    await expect(lotRow).toContainText("Blue Oyster");
    await expect(lotRow).toContainText("4 bags");
    await expect(lotRow).toContainText("Open");

    const runCode = await newPasteurizationRun(page, 3);

    // First session, from the run page: two of the three bags.
    const inoculate = page.locator("form").filter({ has: page.getByRole("heading", { name: "Inoculate Unlabeled Substrate Records" }) });
    await expect(inoculate.getByRole("combobox", { name: "Inoculated from" })).toHaveValue("PURCHASED_SPAWN");
    await lotPicker(inoculate).selectOption({ label: `${lotCode} · Blue Oyster · ${vendor}` });
    await inoculate.getByLabel("Inoculation count").fill("2");
    await inoculate.getByRole("button", { name: "Assign Codes & Print Labels" }).click();
    await expect(page.getByText(/Assigned printable bag codes to 2 substrate bags/)).toBeVisible();

    // The bags took the lot's species and the short code.
    const firstBag = `SB-BO-${runCode}-01`;
    await page.goto(`/bags/${firstBag}`);
    await expect(page.getByText("Status: INOCULATED")).toBeVisible();
    await expect(page.getByRole("link", { name: `Purchased spawn lot ${lotCode}` })).toBeVisible();
    await expect(page.getByRole("cell", { name: `Inoculated from purchased spawn lot ${lotCode} (${vendor})` })).toBeVisible();

    // Second session, from the inoculation screen: the lot is still there to choose.
    await page.goto("/events/inoculation");
    await lotPicker(page).selectOption({ label: `${lotCode} · Blue Oyster · ${vendor}` });
    await page.getByRole("combobox", { name: "Pasteurization Run" }).selectOption({ label: runCode });
    await page.getByLabel("Bag count").fill("1");
    await page.getByRole("button", { name: "Assign Codes & Print Labels" }).click();
    await expect(page).toHaveURL(new RegExp(`/bags/create/substrate/labels\\?ids=SB-BO-${runCode}-03`));

    // Used up: it leaves the choices and stays on the record.
    await page.goto("/purchased-spawn-lots");
    await lotRow.getByRole("button", { name: "Mark used up" }).click();
    await expect(status(page, `Lot ${lotCode} marked used up.`)).toBeVisible();
    await expect(lotRow).toContainText("Used up");
    await page.goto("/events/inoculation");
    await expect(page.getByRole("combobox", { name: "Inoculated from" })).toBeVisible();
    await expect(page.locator("option", { hasText: lotCode })).toHaveCount(0);

    // The report groups contamination by lot.
    await page.goto("/reports");
    const byLot = page.getByRole("heading", { name: "Contamination By Purchased Spawn Lot" }).locator("xpath=..");
    await expect(byLot.locator("tr").filter({ hasText: lotCode })).toContainText("3");
  });

  test("an operator records a lot on a phone", async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
    const page = await context.newPage();
    await signIn(page, OPERATOR);
    const lotCode = await recordLot(page, `Phone Supplier ${Date.now()}`);
    expect(lotCode).toMatch(/^PL-BO-/);
    // The form and the list fit the screen.
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
    await context.close();
  });
});
