"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiGet, apiPost } from "../../../lib/api";
import type { Bag, LiquidCulture, SterilizationRunDetail } from "../../../lib/types";

function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function buildLabelsHref(bagRefs: string[], path: string) {
  return `${path}?ids=${bagRefs.map((bagRef) => encodeURIComponent(bagRef)).join(",")}`;
}

export default function SterilizationRunDetailPage() {
  const params = useParams();
  const runIdRaw = params?.runId;
  const runId = typeof runIdRaw === "string" ? runIdRaw : Array.isArray(runIdRaw) ? runIdRaw[0] : undefined;
  const [run, setRun] = useState<SterilizationRunDetail | null>(null);
  const [liquidCultures, setLiquidCultures] = useState<LiquidCulture[]>([]);
  const [readySpawnBags, setReadySpawnBags] = useState<Bag[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [createMessage, setCreateMessage] = useState<string | null>(null);
  const [inoculationMessage, setInoculationMessage] = useState<string | null>(null);
  const [spawnLabelRefs, setSpawnLabelRefs] = useState<string[]>([]);
  const [createCount, setCreateCount] = useState(1);
  const [inoculateCount, setInoculateCount] = useState(1);
  const [sourceType, setSourceType] = useState<"LIQUID_CULTURE" | "SPAWN_BAG">("LIQUID_CULTURE");
  const [liquidCultureId, setLiquidCultureId] = useState<number | "">("");
  const [donorSpawnBagRef, setDonorSpawnBagRef] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isInoculating, setIsInoculating] = useState(false);

  useEffect(() => {
    if (!runId) {
      return;
    }

    async function loadPageData() {
      const [runDetail, cultureRows, donorRows] = await Promise.all([
        apiGet<SterilizationRunDetail>(`/sterilization-runs/${encodeURIComponent(runId)}/detail`),
        apiGet<LiquidCulture[]>("/liquid-cultures"),
        apiGet<Bag[]>("/bags?bag_type=SPAWN&status=READY"),
      ]);
      setRun(runDetail);
      setLiquidCultures(cultureRows);
      setReadySpawnBags(donorRows);
      setLiquidCultureId((current) =>
        cultureRows.some((culture) => culture.liquid_culture_id === current)
          ? current
          : cultureRows[0]?.liquid_culture_id ?? "",
      );
      setDonorSpawnBagRef((current) =>
        donorRows.some((bag) => bag.bag_ref === current) ? current : donorRows[0]?.bag_ref ?? "",
      );
      setSourceType((current) => {
        if (current === "LIQUID_CULTURE" && cultureRows.length === 0 && donorRows.length > 0) {
          return "SPAWN_BAG";
        }
        if (current === "SPAWN_BAG" && donorRows.length === 0 && cultureRows.length > 0) {
          return "LIQUID_CULTURE";
        }
        return current;
      });
    }

    loadPageData().then(
      () => setLoadError(null),
      (error: unknown) => setLoadError(error instanceof Error ? error.message : String(error)),
    );
  }, [runId]);

  const unlabeledBags = run?.bags.filter((bag) => !bag.bag_code) ?? [];
  const labeledBags = run?.bags.filter((bag) => bag.bag_code) ?? [];

  async function reloadRunData() {
    if (!runId) {
      return;
    }
    const [runDetail, donorRows] = await Promise.all([
      apiGet<SterilizationRunDetail>(`/sterilization-runs/${encodeURIComponent(runId)}/detail`),
      apiGet<Bag[]>("/bags?bag_type=SPAWN&status=READY"),
    ]);
    setRun(runDetail);
    setReadySpawnBags(donorRows);
    setDonorSpawnBagRef((current) =>
      donorRows.some((bag) => bag.bag_ref === current) ? current : donorRows[0]?.bag_ref ?? "",
    );
  }

  async function createSpawnRecords(e: React.FormEvent) {
    e.preventDefault();
    if (!run) {
      return;
    }
    if (!Number.isFinite(createCount) || createCount < 1) {
      setActionError("Spawn record count must be at least 1.");
      return;
    }

    setIsCreating(true);
    setActionError(null);
    setCreateMessage(null);
    setInoculationMessage(null);
    setSpawnLabelRefs([]);

    try {
      const createdBags = await apiPost<Bag[]>("/bags/spawn", {
        sterilization_run_id: run.sterilization_run_id,
        bag_count: createCount,
      });
      await reloadRunData();
      setCreateMessage(
        `Created ${createdBags.length} unlabeled spawn record${createdBags.length === 1 ? "" : "s"} for ${run.run_code}.`,
      );
      setCreateCount(1);
      setInoculateCount((current) => Math.max(1, current));
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
      setActionError("No unlabeled spawn records are available in this run.");
      return;
    }
    if (inoculateCount > unlabeledBags.length) {
      setActionError(`Only ${unlabeledBags.length} unlabeled spawn record(s) are available in this run.`);
      return;
    }
    if (sourceType === "LIQUID_CULTURE" && liquidCultureId === "") {
      setActionError("Select a liquid culture.");
      return;
    }
    if (sourceType === "SPAWN_BAG" && !donorSpawnBagRef) {
      setActionError("Select a donor spawn bag.");
      return;
    }

    setIsInoculating(true);
    setActionError(null);
    setCreateMessage(null);
    setInoculationMessage(null);

    try {
      const inoculatedBags = await apiPost<Bag[]>("/spawn-inoculations/batch", {
        sterilization_run_id: run.sterilization_run_id,
        bag_count: inoculateCount,
        source_type: sourceType,
        liquid_culture_id: sourceType === "LIQUID_CULTURE" ? liquidCultureId : undefined,
        donor_spawn_bag_id: sourceType === "SPAWN_BAG" ? donorSpawnBagRef : undefined,
      });
      await reloadRunData();
      setSpawnLabelRefs(inoculatedBags.map((bag) => bag.bag_ref));
      setInoculationMessage(
        `Assigned printable bag codes to ${inoculatedBags.length} spawn bag${inoculatedBags.length === 1 ? "" : "s"} in ${run.run_code}.`,
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
        <h1>Sterilization Run</h1>
        <p className="error">Missing run ID.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="card">
        <h1>Sterilization Run Detail</h1>
        {loadError && <p className="error">{loadError}</p>}
        {!run ? (
          <p>Loading...</p>
        ) : (
          <>
            <p>Run Code: {run.run_code}</p>
            <p>Run ID: {run.sterilization_run_id}</p>
            <p>Unloaded At: {new Date(run.unloaded_at).toLocaleString()}</p>
            <p>Planned Bag Count: {run.bag_count}</p>
            <p>Total Bag Records: {run.summary.total_bags}</p>
            <p>Unlabeled Spawn Records: {run.summary.unlabeled_bags}</p>
            <p>Ready Spawn Bags: {run.summary.ready_bags}</p>
            <p>Consumed Spawn Bags: {run.summary.consumed_bags}</p>
            <p>Downstream Substrate Bags: {run.downstream_summary.total_bags}</p>
            <p>Downstream Contamination: {run.downstream_summary.contaminated_bags}</p>
            <p>Downstream Harvest: {run.downstream_summary.total_harvest_kg.toFixed(3)} kg</p>
            <p>Downstream BE: {formatPercent(run.downstream_summary.overall_bio_efficiency)}</p>
          </>
        )}
      </div>

      {run && (
        <>
          <div className="card">
            <h2>Run Actions</h2>
            <p className="workflow-note">
              Manage this run from fill through labeling here. Create internal records after sterilization, then
              inoculate unlabeled bags from this run to assign printable codes and print labels.
            </p>

            <form onSubmit={createSpawnRecords} className="form">
              <h3>Create Unlabeled Spawn Records</h3>
              <p>Create internal bag records for spawn bags filled and sterilized in this run.</p>
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
              <button className="btn" type="submit" disabled={isCreating}>
                {isCreating ? "Creating..." : "Create Unlabeled Records"}
              </button>
            </form>

            <form onSubmit={inoculateRunBags} className="form" style={{ marginTop: 24 }}>
              <h3>Inoculate Unlabeled Spawn Records</h3>
              <p>Available unlabeled records in this run: {unlabeledBags.length}</p>
              <label>
                Source Type
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value as "LIQUID_CULTURE" | "SPAWN_BAG")}
                >
                  <option value="LIQUID_CULTURE">Liquid Culture</option>
                  <option value="SPAWN_BAG">Donor Spawn Bag</option>
                </select>
              </label>
              {sourceType === "LIQUID_CULTURE" ? (
                <label>
                  Liquid Culture
                  <select
                    value={liquidCultureId}
                    onChange={(e) => setLiquidCultureId(Number(e.target.value) || "")}
                    required
                  >
                    <option value="">- Select -</option>
                    {liquidCultures.map((culture) => (
                      <option key={culture.liquid_culture_id} value={culture.liquid_culture_id}>
                        {culture.culture_code}
                        {culture.source ? ` - ${culture.source}` : ""}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <label>
                  Donor Spawn Bag
                  <select value={donorSpawnBagRef} onChange={(e) => setDonorSpawnBagRef(e.target.value)} required>
                    <option value="">- Select -</option>
                    {readySpawnBags.map((bag) => (
                      <option key={bag.bag_id} value={bag.bag_ref}>
                        {bag.bag_ref}
                      </option>
                    ))}
                  </select>
                </label>
              )}
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
              <button
                className="btn"
                type="submit"
                disabled={
                  isInoculating ||
                  unlabeledBags.length === 0 ||
                  (sourceType === "LIQUID_CULTURE" && liquidCultures.length === 0) ||
                  (sourceType === "SPAWN_BAG" && readySpawnBags.length === 0)
                }
              >
                {isInoculating ? "Assigning Codes..." : "Assign Codes & Print Labels"}
              </button>
            </form>

            {sourceType === "LIQUID_CULTURE" && liquidCultures.length === 0 && (
              <p className="error">No active liquid cultures are available yet. Add one before inoculating this run.</p>
            )}
            {sourceType === "SPAWN_BAG" && readySpawnBags.length === 0 && (
              <p className="error">No ready donor spawn bags are available right now.</p>
            )}
            {actionError && <p className="error">{actionError}</p>}
            {createMessage && <p className="success">{createMessage}</p>}
            {inoculationMessage && <p className="success">{inoculationMessage}</p>}
            {spawnLabelRefs.length > 0 && (
              <p>
                <a className="btn" href={buildLabelsHref(spawnLabelRefs, "/bags/create/spawn/labels")}>
                  Print Last Batch Labels
                </a>
              </p>
            )}
          </div>

          <div className="card">
            <h2>Unlabeled Spawn Records</h2>
            {unlabeledBags.length === 0 ? (
              <p>No unlabeled spawn records are waiting in this run.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Internal Record</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {unlabeledBags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_id)}`}>{bag.bag_id}</a>
                      </td>
                      <td>{bag.status}</td>
                      <td>{new Date(bag.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2>Labeled Spawn Bags In This Run</h2>
            {labeledBags.length === 0 ? (
              <p>No inoculated spawn bags in this run yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Printable Bag</th>
                    <th>Internal Record</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Ready</th>
                    <th>Consumed</th>
                  </tr>
                </thead>
                <tbody>
                  {labeledBags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                      </td>
                      <td>{bag.bag_id}</td>
                      <td>
                        {bag.inoculation_source_type === "LIQUID_CULTURE"
                          ? bag.source_liquid_culture_code ?? "Liquid culture"
                          : bag.source_spawn_bag_ref ?? "-"}
                      </td>
                      <td>{bag.status}</td>
                      <td>{bag.ready_at ? new Date(bag.ready_at).toLocaleDateString() : "-"}</td>
                      <td>{bag.consumed_at ? new Date(bag.consumed_at).toLocaleDateString() : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h2>Downstream Substrate Outcomes</h2>
            {run.downstream_substrate_bags.length === 0 ? (
              <p>No downstream substrate bags found yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Bag</th>
                    <th>Pasteurization Run</th>
                    <th>Status</th>
                    <th>Harvest</th>
                    <th>Dry Weight</th>
                    <th>BE</th>
                  </tr>
                </thead>
                <tbody>
                  {run.downstream_substrate_bags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                      </td>
                      <td>
                        {bag.pasteurization_run_id ? (
                          <a href={`/pasteurization-runs/${bag.pasteurization_run_id}`}>
                            {bag.pasteurization_run_code ?? bag.pasteurization_run_id}
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
