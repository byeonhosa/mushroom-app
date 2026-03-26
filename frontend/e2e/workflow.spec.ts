import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const apiBaseUrl = "http://localhost:8001/api";

type BagRow = {
  bag_id: string;
  bag_code?: string | null;
  bag_ref: string;
  status: string;
};

type SterilizationRunRow = {
  sterilization_run_id: number;
  run_code: string;
};

type SterilizationRunDetail = {
  sterilization_run_id: number;
  run_code: string;
  bags: BagRow[];
  downstream_summary: {
    contaminated_bags: number;
    total_bags: number;
  };
};

type PasteurizationRunRow = {
  pasteurization_run_id: number;
  run_code: string;
};

type PasteurizationRunDetail = {
  pasteurization_run_id: number;
  run_code: string;
  bags: BagRow[];
};

function uniqueSuffix(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
}

function localDateTime(offsetMinutes = 0) {
  const timestamp = new Date(Date.now() + offsetMinutes * 60_000);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${timestamp.getFullYear()}-${pad(timestamp.getMonth() + 1)}-${pad(timestamp.getDate())}T${pad(timestamp.getHours())}:${pad(timestamp.getMinutes())}`;
}

function escapeForRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function apiGet<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(`${apiBaseUrl}${path}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as T;
}

async function waitForSterilizationRunId(request: APIRequestContext, runCode: string) {
  let runId: number | null = null;

  await expect
    .poll(async () => {
      const runs = await apiGet<SterilizationRunRow[]>(
        request,
        `/sterilization-runs?run_code_contains=${encodeURIComponent(runCode)}`,
      );
      runId = runs.find((run) => run.run_code === runCode)?.sterilization_run_id ?? null;
      return runId;
    })
    .not.toBeNull();

  return runId!;
}

async function waitForPasteurizationRunId(request: APIRequestContext, runCode: string) {
  let runId: number | null = null;

  await expect
    .poll(async () => {
      const runs = await apiGet<PasteurizationRunRow[]>(request, "/pasteurization-runs");
      runId = runs.find((run) => run.run_code === runCode)?.pasteurization_run_id ?? null;
      return runId;
    })
    .not.toBeNull();

  return runId!;
}

async function getSterilizationRunDetail(request: APIRequestContext, runId: number) {
  return apiGet<SterilizationRunDetail>(request, `/sterilization-runs/${runId}/detail`);
}

async function getPasteurizationRunDetail(request: APIRequestContext, runId: number) {
  return apiGet<PasteurizationRunDetail>(request, `/pasteurization-runs/${runId}/detail`);
}

async function createSterilizationRun(page: Page, request: APIRequestContext, runCode: string) {
  await page.goto("/sterilization-runs");
  await expect(page.getByRole("heading", { name: "Sterilization Runs (Autoclave)" })).toBeVisible();
  const createRunForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Create Run" }) });
  await createRunForm.getByRole("textbox", { name: "Run Code", exact: true }).fill(runCode);
  await createRunForm.getByLabel("Spawn Recipe").selectOption({ label: "SR1" });
  await createRunForm.getByLabel("Grain Type").selectOption({ label: "Rye" });
  await createRunForm.getByLabel("Bag Count").fill("1");
  await createRunForm.getByLabel("Unloaded At").fill(localDateTime(1));
  await createRunForm.getByRole("button", { name: "Create Run" }).click();
  await expect(page.getByRole("link", { name: runCode })).toBeVisible();
  return waitForSterilizationRunId(request, runCode);
}

async function createPasteurizationRun(page: Page, request: APIRequestContext, runCode: string) {
  await page.goto("/pasteurization-runs");
  await expect(page.getByRole("heading", { name: "Pasteurization Runs (Steam)" })).toBeVisible();
  const createRunForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Create Run" }) });
  await createRunForm.getByRole("textbox", { name: "Run Code", exact: true }).fill(runCode);
  await createRunForm.getByLabel("Mix Lot").selectOption({ label: "LOT-STD-001" });
  await createRunForm.getByLabel("Substrate Recipe").selectOption({ label: "Masters Mix (MM)" });
  await createRunForm.getByLabel("Bag Count").fill("1");
  await createRunForm.getByLabel("Unloaded At").fill(localDateTime(2));
  await createRunForm.getByRole("button", { name: "Create Run" }).click();
  await expect(page.getByRole("link", { name: runCode })).toBeVisible();
  return waitForPasteurizationRunId(request, runCode);
}

async function createReadySpawnBag(page: Page, request: APIRequestContext, suffix: string) {
  const runCode = `E2E-STER-${suffix}`;
  const runId = await createSterilizationRun(page, request, runCode);

  await page.goto(`/sterilization-runs/${runId}`);
  await expect(page.getByText(`Run Code: ${runCode}`)).toBeVisible();

  const createRecordsForm = page
    .locator("form")
    .filter({ has: page.getByRole("heading", { name: "Create Unlabeled Spawn Records" }) });
  await createRecordsForm.getByLabel("Record count").fill("1");
  await createRecordsForm.getByRole("button", { name: "Create Unlabeled Records" }).click();
  await expect(page.getByText(/Created 1 unlabeled spawn record/)).toBeVisible();

  const inoculationForm = page
    .locator("form")
    .filter({ has: page.getByRole("heading", { name: "Inoculate Unlabeled Spawn Records" }) });
  await inoculationForm
    .getByRole("combobox", { name: "Liquid Culture", exact: true })
    .selectOption({ label: "LC-LM-001 - Internal lab" });
  await inoculationForm.getByLabel("Inoculation count").fill("1");
  await inoculationForm.getByRole("button", { name: "Assign Codes & Print Labels" }).click();
  await expect(page.getByText(/Assigned printable bag codes to 1 spawn bag/)).toBeVisible();

  let runDetail: SterilizationRunDetail | null = null;
  await expect.poll(async () => {
    runDetail = await getSterilizationRunDetail(request, runId);
    return runDetail.bags.filter((bag) => bag.bag_code).length;
  }).toBe(1);

  const spawnBagRef = runDetail!.bags.find((bag) => bag.bag_code)?.bag_ref;
  expect(spawnBagRef).toBeTruthy();

  await recordBagStateChange(page, "/events/incubation", "Record Incubation Start", spawnBagRef!, "INCUBATING");
  await recordBagStateChange(page, "/events/ready", "Record Ready", spawnBagRef!, "READY");

  return { runCode, runId, spawnBagRef: spawnBagRef! };
}

async function createSubstrateBagFromSpawn(
  page: Page,
  request: APIRequestContext,
  spawnBagRef: string,
  suffix: string,
) {
  const runCode = `E2E-PAST-${suffix}`;
  const runId = await createPasteurizationRun(page, request, runCode);

  await page.goto(`/pasteurization-runs/${runId}`);
  await expect(page.getByText(`Run Code: ${runCode}`)).toBeVisible();

  const createRecordsForm = page
    .locator("form")
    .filter({ has: page.getByRole("heading", { name: "Create Unlabeled Substrate Records" }) });
  await createRecordsForm.getByLabel("Record count").fill("1");
  await createRecordsForm.getByLabel("Actual dry kg per bag (optional)").fill("1.000");
  await createRecordsForm.getByRole("button", { name: "Create Unlabeled Records" }).click();
  await expect(page.getByText(/Created 1 unlabeled substrate record/)).toBeVisible();

  const inoculationForm = page
    .locator("form")
    .filter({ has: page.getByRole("heading", { name: "Inoculate Unlabeled Substrate Records" }) });
  await inoculationForm.getByLabel("Ready spawn bag code").fill(spawnBagRef);
  await inoculationForm.getByLabel("Inoculation count").fill("1");
  await inoculationForm.getByRole("button", { name: "Assign Codes & Print Labels" }).click();
  await expect(page.getByText(/Assigned printable bag codes to 1 substrate bag/)).toBeVisible();

  let runDetail: PasteurizationRunDetail | null = null;
  await expect.poll(async () => {
    runDetail = await getPasteurizationRunDetail(request, runId);
    return runDetail.bags.filter((bag) => bag.bag_code).length;
  }).toBe(1);

  const substrateBagRef = runDetail!.bags.find((bag) => bag.bag_code)?.bag_ref;
  expect(substrateBagRef).toBeTruthy();

  return { runCode, runId, substrateBagRef: substrateBagRef! };
}

async function recordBagStateChange(
  page: Page,
  route: string,
  buttonLabel: string,
  bagRef: string,
  expectedStatus: string,
) {
  await page.goto(route);
  await page.getByLabel("Bag code").fill(bagRef);
  await page.getByRole("button", { name: buttonLabel }).click();
  await expect(page.getByText(new RegExp(`Recorded: ${escapeForRegExp(bagRef)}`))).toBeVisible();
  await expect(page.getByText(new RegExp(`Status: ${expectedStatus}`))).toBeVisible();
}

async function recordHarvest(page: Page, bagRef: string, flush: 1 | 2, weight: string) {
  await page.goto("/events/harvest");
  await page.getByLabel("Bag code").fill(bagRef);
  await page.getByLabel("Flush").selectOption(String(flush));
  await page.getByLabel("Fresh weight (kg)").fill(weight);
  await page.getByRole("button", { name: "Record Harvest" }).click();
  await expect(
    page.getByText(new RegExp(`Recorded flush ${flush}: .*${escapeForRegExp(bagRef)}`)),
  ).toBeVisible();
}

async function recordDisposal(page: Page, bagRef: string, reason: "CONTAMINATION" | "FINAL_HARVEST") {
  await page.goto("/events/disposal");
  await page.getByLabel("Bag code").fill(bagRef);
  await page.getByLabel("Reason").selectOption(reason);
  await page.getByRole("button", { name: "Record Disposal" }).click();
  await expect(
    page.getByText(new RegExp(`Recorded: ${escapeForRegExp(bagRef)}.*${reason}`)),
  ).toBeVisible();
}

test.describe("bag workflow e2e", () => {
  test("supports a happy path from spawn inoculation through final harvest reporting", async ({
    page,
    request,
  }) => {
    const suffix = uniqueSuffix("happy");
    const { spawnBagRef } = await createReadySpawnBag(page, request, suffix);
    const { runCode: pasteurizationRunCode, substrateBagRef } = await createSubstrateBagFromSpawn(
      page,
      request,
      spawnBagRef,
      suffix,
    );

    await recordBagStateChange(page, "/events/incubation", "Record Incubation Start", substrateBagRef, "INCUBATING");
    await recordBagStateChange(page, "/events/ready", "Record Ready", substrateBagRef, "READY");
    await recordBagStateChange(page, "/events/fruiting", "Record Fruiting Start", substrateBagRef, "FRUITING");
    await recordHarvest(page, substrateBagRef, 1, "0.500");
    await recordHarvest(page, substrateBagRef, 2, "0.300");
    await recordDisposal(page, substrateBagRef, "FINAL_HARVEST");

    await page.goto(`/bags/${encodeURIComponent(substrateBagRef)}`);
    await expect(page.getByText("Status: DISPOSED")).toBeVisible();
    await expect(page.getByText("Biological Efficiency: 80.0%")).toBeVisible();
    await expect(page.getByText("Total Harvest: 0.800 kg")).toBeVisible();
    await expect(page.getByText("Flush 1: 0.500 kg")).toBeVisible();
    await expect(page.getByText("Flush 2: 0.300 kg")).toBeVisible();

    await page.goto("/reports");
    const pasteurizationOutcomesCard = page
      .getByRole("heading", { name: "Pasteurization Run Outcomes" })
      .locator("xpath=..");
    const runRow = pasteurizationOutcomesCard.locator("tr").filter({ hasText: pasteurizationRunCode });
    await expect(runRow).toContainText("0.800 kg");
    await expect(runRow).toContainText("80.0%");

    const substrateMetricsCard = page.getByRole("heading", { name: "Substrate Bag Metrics" }).locator("xpath=..");
    const bagRow = substrateMetricsCard.locator("tr").filter({ hasText: substrateBagRef });
    await expect(bagRow).toContainText("DISPOSED");
    await expect(bagRow).toContainText("0.800 kg");
    await expect(bagRow).toContainText("1.000 kg");
    await expect(bagRow).toContainText("80.0%");
  });

  test("tracks contamination through run detail and reporting views", async ({ page, request }) => {
    const suffix = uniqueSuffix("contam");
    const { runId: sterilizationRunId, spawnBagRef } = await createReadySpawnBag(page, request, suffix);
    const { substrateBagRef } = await createSubstrateBagFromSpawn(page, request, spawnBagRef, suffix);

    await recordBagStateChange(page, "/events/incubation", "Record Incubation Start", substrateBagRef, "INCUBATING");
    await recordDisposal(page, substrateBagRef, "CONTAMINATION");

    await page.goto(`/bags/${encodeURIComponent(substrateBagRef)}`);
    await expect(page.getByText("Status: CONTAMINATED")).toBeVisible();
    await expect(page.getByText(/Disposal: CONTAMINATION at/)).toBeVisible();
    await expect(page.getByRole("cell", { name: "Disposed" })).toBeVisible();

    await page.goto(`/sterilization-runs/${sterilizationRunId}`);
    await expect(page.getByText("Downstream Contamination: 1")).toBeVisible();

    await page.goto("/reports");
    const substrateMetricsCard = page.getByRole("heading", { name: "Substrate Bag Metrics" }).locator("xpath=..");
    const contaminationRow = substrateMetricsCard.locator("tr").filter({ hasText: substrateBagRef });
    await expect(contaminationRow).toContainText("LM");
    await expect(contaminationRow).toContainText("LC-LM-001");
    await expect(contaminationRow).toContainText("CONTAMINATED");
  });
});
