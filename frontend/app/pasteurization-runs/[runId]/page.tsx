"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet, apiPost } from "../../../lib/api";
import type { Bag, PasteurizationRunDetail } from "../../../lib/types";

function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function buildLabelsHref(bagRefs: string[], path: string) {
  return `${path}?ids=${bagRefs.map((bagRef) => encodeURIComponent(bagRef)).join(",")}`;
}

export default function PasteurizationRunDetailPage() {
  const params = useParams();
  const runIdRaw = params?.runId;
  const runId = typeof runIdRaw === "string" ? runIdRaw : Array.isArray(runIdRaw) ? runIdRaw[0] : undefined;
  const [run, setRun] = useState<PasteurizationRunDetail | null>(null);
  const [readySpawnBags, setReadySpawnBags] = useState<Bag[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [createMessage, setCreateMessage] = useState<string | null>(null);
  const [inoculationMessage, setInoculationMessage] = useState<string | null>(null);
  const [substrateLabelRefs, setSubstrateLabelRefs] = useState<string[]>([]);
  const [createCount, setCreateCount] = useState(1);
  const [actualDryKg, setActualDryKg] = useState("");
  const [inoculateCount, setInoculateCount] = useState(1);
  const [spawnBagRef, setSpawnBagRef] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isInoculating, setIsInoculating] = useState(false);

  useEffect(() => {
    if (!runId) {
      return;
    }

    async function loadPageData() {
      const [runDetail, donorRows] = await Promise.all([
        apiGet<PasteurizationRunDetail>(`/pasteurization-runs/${encodeURIComponent(runId)}/detail`),
        apiGet<Bag[]>("/bags?bag_type=SPAWN&status=READY"),
      ]);
      setRun(runDetail);
      setReadySpawnBags(donorRows);
      setSpawnBagRef((current) =>
        donorRows.some((bag) => bag.bag_ref === current) ? current : donorRows[0]?.bag_ref ?? "",
      );
    }

    loadPageData().then(
      () => setLoadError(null),
      (error: unknown) => setLoadError(error instanceof Error ? error.message : String(error)),
    );
  }, [runId]);

  const unlabeledBags = run?.bags.filter((bag) => !bag.bag_code) ?? [];
  const inoculatedBags = run?.bags.filter((bag) => bag.bag_code) ?? [];

  async function reloadRunData() {
    if (!runId) {
      return;
    }
    const [runDetail, donorRows] = await Promise.all([
      apiGet<PasteurizationRunDetail>(`/pasteurization-runs/${encodeURIComponent(runId)}/detail`),
      apiGet<Bag[]>("/bags?bag_type=SPAWN&status=READY"),
    ]);
    setRun(runDetail);
    setReadySpawnBags(donorRows);
    setSpawnBagRef((current) =>
      donorRows.some((bag) => bag.bag_ref === current) ? current : donorRows[0]?.bag_ref ?? "",
    );
  }

  async function createSubstrateRecords(e: React.FormEvent) {
    e.preventDefault();
    if (!run) {
      return;
    }
    if (!Number.isFinite(createCount) || createCount < 1) {
      setActionError("Substrate record count must be at least 1.");
      return;
    }

    const parsedActualDryKg = actualDryKg.trim() ? Number(actualDryKg) : undefined;
    if (parsedActualDryKg !== undefined && (!Number.isFinite(parsedActualDryKg) || parsedActualDryKg <= 0)) {
      setActionError("Actual dry kg per bag must be a positive number when provided.");
      return;
    }

    setIsCreating(true);
    setActionError(null);
    setCreateMessage(null);
    setInoculationMessage(null);
    setSubstrateLabelRefs([]);

    try {
      const createdBags = await apiPost<Bag[]>("/bags/substrate", {
        pasteurization_run_id: run.pasteurization_run_id,
        bag_count: createCount,
        actual_dry_kg: parsedActualDryKg,
      });
      await reloadRunData();
      setCreateMessage(
        `Created ${createdBags.length} unlabeled substrate record${createdBags.length === 1 ? "" : "s"} for ${run.run_code}.`,
      );
      setCreateCount(1);
      setActualDryKg("");
    } catch (error: unknown) {
      setActionError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsCreating(false);
    }
  }

  async function inoculateRunBags(e: React.FormEvent) {
    e.preventDefault();
    if (!run) {
      return;
    }
    if (!Number.isFinite(inoculateCount) || inoculateCount < 1) {
      setActionError("Inoculation count must be at least 1.");
      return;
    }
    if (unlabeledBags.length === 0) {
      setActionError("No unlabeled substrate records are available in this run.");
      return;
    }
    if (inoculateCount > unlabeledBags.length) {
      setActionError(`Only ${unlabeledBags.length} unlabeled substrate record(s) are available in this run.`);
      return;
    }
    if (!spawnBagRef.trim()) {
      setActionError("Enter or select one ready spawn bag code.");
      return;
    }

    setIsInoculating(true);
    setActionError(null);
    setCreateMessage(null);
    setInoculationMessage(null);

    try {
      const inoculatedBags = await apiPost<Bag[]>("/inoculations/batch", {
        pasteurization_run_id: run.pasteurization_run_id,
        bag_count: inoculateCount,
        spawn_bag_id: spawnBagRef.trim(),
      });
      await reloadRunData();
      setSubstrateLabelRefs(inoculatedBags.map((bag) => bag.bag_ref));
      setInoculationMessage(
        `Assigned printable bag codes to ${inoculatedBags.length} substrate bag${inoculatedBags.length === 1 ? "" : "s"} in ${run.run_code}.`,
      );
      setInoculateCount(1);
    } catch (error: unknown) {
      setActionError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsInoculating(false);
    }
  }

  if (!runId) {
    return (
      <div className="card">
        <h1>Pasteurization Run</h1>
        <p className="error">Missing run ID.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h1>Pasteurization Run Detail</h1>
        {loadError && <p className="error">{loadError}</p>}
        {!run ? (
          <p>Loading...</p>
        ) : (
          <>
            <p>Run Code: {run.run_code}</p>
            <p>Run ID: {run.pasteurization_run_id}</p>
            <p>Unloaded At: {new Date(run.unloaded_at).toLocaleString()}</p>
            <p>Planned Bag Count: {run.bag_count}</p>
            <p>Total Bag Records: {run.summary.total_bags}</p>
            <p>Unlabeled Substrate Records: {run.summary.unlabeled_bags}</p>
            <p>Contaminated Bags: {run.summary.contaminated_bags}</p>
            <p>Total Harvest: {run.summary.total_harvest_kg.toFixed(3)} kg</p>
            <p>Total Dry Weight: {run.summary.total_dry_weight_kg.toFixed(3)} kg</p>
            <p>Run BE: {formatPercent(run.summary.overall_bio_efficiency)}</p>
          </>
        )}
      </div>

      {run && (
        <>
          <div className="card">
            <h2>Run Actions</h2>
            <p className="workflow-note">
              Manage this run after pasteurization here. Create internal substrate records for the run, then inoculate
              unlabeled records from one ready spawn bag and print the resulting labels.
            </p>

            <form onSubmit={createSubstrateRecords} className="form">
              <h3>Create Unlabeled Substrate Records</h3>
              <p>Create internal bag records for substrate bags filled and pasteurized in this run.</p>
              <label>
                Record count
                <input
                  type="number"
                  min={1}
                  max={999}
                  value={createCount}
                  onChange={(e) => setCreateCount(Number(e.target.value) || 1)}
                />
              </label>
              <label>
                Actual dry kg per bag (optional)
                <input
                  type="number"
                  step="0.001"
                  min="0"
                  value={actualDryKg}
                  onChange={(e) => setActualDryKg(e.target.value)}
                  placeholder="Uses fill profile target if left blank"
                />
              </label>
              <button className="btn" type="submit" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create Unlabeled Records"}
              </button>
            </form>

            <form onSubmit={inoculateRunBags} className="form" style={{ marginTop: 24 }}>
              <h3>Inoculate Unlabeled Substrate Records</h3>
              <p>Available unlabeled records in this run: {unlabeledBags.length}</p>
              <label>
                Ready spawn bag code
                <input
                  list="ready-spawn-bag-options"
                  value={spawnBagRef}
                  onChange={(e) => setSpawnBagRef(e.target.value)}
                  placeholder="Scan or enter a ready spawn bag code"
                />
              </label>
              <datalist id="ready-spawn-bag-options">
                {readySpawnBags.map((bag) => (
                  <option key={bag.bag_id} value={bag.bag_ref} />
                ))}
              </datalist>
              <label>
                Inoculation count
                <input
                  type="number"
                  min={1}
                  max={Math.max(1, unlabeledBags.length)}
                  value={inoculateCount}
                  onChange={(e) => setInoculateCount(Number(e.target.value) || 1)}
                />
              </label>
              <button className="btn" type="submit" disabled={isInoculating || unlabeledBags.length === 0}>
                {isInoculating ? "Assigning Codes..." : "Assign Codes & Print Labels"}
              </button>
            </form>

            {readySpawnBags.length === 0 && (
              <p className="error">No ready spawn bags are available right now for substrate inoculation.</p>
            )}
            {actionError && <p className="error">{actionError}</p>}
            {createMessage && <p className="success">{createMessage}</p>}
            {inoculationMessage && <p className="success">{inoculationMessage}</p>}
            {substrateLabelRefs.length > 0 && (
              <p>
                <a className="btn" href={buildLabelsHref(substrateLabelRefs, "/bags/create/substrate/labels")}>
                  Print Last Batch Labels
                </a>
              </p>
            )}
          </div>

          <div className="card">
            <h2>Unlabeled Substrate Records</h2>
            {unlabeledBags.length === 0 ? (
              <p>No unlabeled substrate records are waiting in this run.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Internal Record</th>
                    <th>Status</th>
                    <th>Dry Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {unlabeledBags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_id)}`}>{bag.bag_id}</a>
                      </td>
                      <td>{bag.status}</td>
                      <td>
                        {bag.dry_weight_kg != null
                          ? `${bag.dry_weight_kg.toFixed(3)} kg (${bag.dry_weight_source ?? "-"})`
                          : "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2>Inoculated Substrate Bags In This Run</h2>
            {inoculatedBags.length === 0 ? (
              <p>No inoculated substrate bags in this run yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Bag</th>
                    <th>Parent Spawn</th>
                    <th>Source Sterilization</th>
                    <th>Status</th>
                    <th>Harvest</th>
                    <th>Dry Weight</th>
                    <th>BE</th>
                  </tr>
                </thead>
                <tbody>
                  {inoculatedBags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                      </td>
                      <td>
                        {bag.parent_spawn_bag_ref ? (
                          <a href={`/bags/${encodeURIComponent(bag.parent_spawn_bag_ref)}`}>{bag.parent_spawn_bag_ref}</a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>
                        {bag.source_sterilization_run_id ? (
                          <a href={`/sterilization-runs/${bag.source_sterilization_run_id}`}>
                            {bag.source_sterilization_run_code ?? bag.source_sterilization_run_id}
                          </a>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td>{bag.contaminated ? "CONTAMINATED" : bag.status}</td>
                      <td>{bag.total_harvest_kg.toFixed(3)} kg</td>
                      <td>
                        {bag.dry_weight_kg != null
                          ? `${bag.dry_weight_kg.toFixed(3)} kg (${bag.dry_weight_source ?? "-"})`
                          : "-"}
                      </td>
                      <td>{formatPercent(bag.bio_efficiency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
