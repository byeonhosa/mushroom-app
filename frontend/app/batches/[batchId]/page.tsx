"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiDelete, apiGet, apiPost } from "../../../lib/api";
import type {
  BatchInoculation,
  BatchMetrics,
  IngredientLot,
  SubstrateBag,
  SubstrateBatchAddin,
} from "../../../lib/types";

type AddinForm = {
  ingredient_lot_id: string;
  dry_kg: string;
  pct_of_base_dry: string;
  notes: string;
};

const emptyAddinForm: AddinForm = {
  ingredient_lot_id: "",
  dry_kg: "",
  pct_of_base_dry: "",
  notes: "",
};

function toNullableNumber(raw: string): number | null {
  if (!raw.trim()) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

function formatNumber(value: number): string {
  return value.toFixed(4).replace(/\.?0+$/, "");
}

export default function BatchDetail() {
  const params = useParams();
  const batchIdRaw = params?.batchId;
  const batchId =
    typeof batchIdRaw === "string"
      ? batchIdRaw
      : Array.isArray(batchIdRaw)
      ? batchIdRaw[0]
      : undefined;

  const [bags, setBags] = useState<SubstrateBag[]>([]);
  const [metrics, setMetrics] = useState<BatchMetrics | null>(null);
  const [inoculation, setInoculation] = useState<BatchInoculation | null>(null);
  const [ingredientLots, setIngredientLots] = useState<IngredientLot[]>([]);
  const [addins, setAddins] = useState<SubstrateBatchAddin[]>([]);
  const [addinForm, setAddinForm] = useState<AddinForm>(emptyAddinForm);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!batchId) return;
    const [bagsRes, metricsRes, lotsRes, addinsRes] = await Promise.all([
      apiGet<SubstrateBag[]>(`/batches/${batchId}/bags`),
      apiGet<BatchMetrics>(`/batches/${batchId}/metrics`),
      apiGet<IngredientLot[]>("/ingredient-lots"),
      apiGet<SubstrateBatchAddin[]>(`/batches/${batchId}/addins`),
    ]);
    setBags(bagsRes);
    setMetrics(metricsRes);
    setIngredientLots(lotsRes);
    setAddins(addinsRes);
    try {
      const inoc = await apiGet<BatchInoculation>(`/batches/${batchId}/inoculation`);
      setInoculation(inoc);
    } catch {
      setInoculation(null);
    }
  }

  useEffect(() => {
    if (!batchId) return;
    refresh().catch((e) => setError(e?.message || String(e)));
  }, [batchId]);

  if (!batchId) {
    return (
      <div className="card">
        <h1>Batch</h1>
        <p className="error">Missing batchId in route params.</p>
      </div>
    );
  }

  const baseDryKg = metrics?.dry_kg_total ?? null;

  async function onCreateAddin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiPost<SubstrateBatchAddin>(`/batches/${batchId}/addins`, {
        ingredient_lot_id: Number(addinForm.ingredient_lot_id),
        dry_kg: toNullableNumber(addinForm.dry_kg),
        pct_of_base_dry: toNullableNumber(addinForm.pct_of_base_dry),
        notes: addinForm.notes.trim() || null,
      });
      setAddinForm(emptyAddinForm);
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  async function onDeleteAddin(addinId: number) {
    setError(null);
    try {
      await apiDelete(`/batches/${batchId}/addins/${addinId}`);
      await refresh();
    } catch (e: any) {
      setError(e?.message || String(e));
    }
  }

  function onDryKgChange(raw: string) {
    setAddinForm((prev) => {
      const next: AddinForm = { ...prev, dry_kg: raw };
      const dry = toNullableNumber(raw);
      if (dry == null) return { ...next, pct_of_base_dry: "" };
      if (baseDryKg && baseDryKg > 0) {
        next.pct_of_base_dry = formatNumber((dry / baseDryKg) * 100.0);
      }
      return next;
    });
  }

  function onPctChange(raw: string) {
    setAddinForm((prev) => {
      const next: AddinForm = { ...prev, pct_of_base_dry: raw };
      const pct = toNullableNumber(raw);
      if (pct == null) return { ...next, dry_kg: "" };
      if (baseDryKg != null) {
        next.dry_kg = formatNumber((baseDryKg * pct) / 100.0);
      }
      return next;
    });
  }

  return (
    <div className="card">
      <h1>Batch {batchId}</h1>

      {error && <p className="error">{error}</p>}

      {!metrics ? (
        <p>Loading…</p>
      ) : (
        <div className="kpis">
          <div>
            <div className="kpiLabel">Total Harvest (kg)</div>
            <div className="kpi">{metrics.total_harvest_kg.toFixed(3)}</div>
          </div>
          <div>
            <div className="kpiLabel">Dry Mass Total (kg)</div>
            <div className="kpi">{metrics.dry_kg_total.toFixed(3)}</div>
          </div>
          <div>
            <div className="kpiLabel">BE%</div>
            <div className="kpi">{metrics.be_percent.toFixed(1)}</div>
          </div>
        </div>
      )}

      <h2>Inoculation</h2>
      {!inoculation ? (
        <p>No inoculation record.</p>
      ) : (
        <p>
          Spawn Batch #{inoculation.spawn_batch_id} ({inoculation.spawn_batch.strain_code} / {inoculation.spawn_batch.spawn_type})
          {" "}at {new Date(inoculation.inoculated_at).toLocaleString()}
          {inoculation.spawn_blocks_used ? ` using ${inoculation.spawn_blocks_used} block(s)` : ""}
        </p>
      )}

      <h2>Add-ins</h2>
      <form className="form" onSubmit={onCreateAddin}>
        <label>
          Ingredient Lot
          <select
            required
            value={addinForm.ingredient_lot_id}
            onChange={(e) => setAddinForm((p) => ({ ...p, ingredient_lot_id: e.target.value }))}
          >
            <option value="">Select ingredient lot...</option>
            {ingredientLots.map((lot) => (
              <option key={lot.ingredient_lot_id} value={lot.ingredient_lot_id}>
                #{lot.ingredient_lot_id} {lot.ingredient?.name ?? `Ingredient ${lot.ingredient_id}`}
                {lot.lot_code ? ` / ${lot.lot_code}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          Dry kg
          <input
            type="number"
            min="0"
            step="0.0001"
            value={addinForm.dry_kg}
            onChange={(e) => onDryKgChange(e.target.value)}
          />
        </label>
        <label>
          % of base dry
          <input
            type="number"
            min="0"
            step="0.0001"
            value={addinForm.pct_of_base_dry}
            onChange={(e) => onPctChange(e.target.value)}
          />
        </label>
        <label>
          Notes
          <input
            value={addinForm.notes}
            onChange={(e) => setAddinForm((p) => ({ ...p, notes: e.target.value }))}
          />
        </label>
        <button className="btn" type="submit">Add Add-in</button>
      </form>

      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Ingredient</th>
            <th>Lot</th>
            <th>Dry kg</th>
            <th>% base dry</th>
            <th>Notes</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {addins.map((line) => (
            <tr key={line.substrate_batch_addin_id}>
              <td>{line.substrate_batch_addin_id}</td>
              <td>{line.ingredient_lot?.ingredient?.name ?? `Ingredient ${line.ingredient_lot?.ingredient_id ?? "?"}`}</td>
              <td>{line.ingredient_lot?.lot_code ?? `#${line.ingredient_lot_id}`}</td>
              <td>{line.dry_kg == null ? "" : line.dry_kg.toFixed(4)}</td>
              <td>{line.pct_of_base_dry == null ? "" : line.pct_of_base_dry.toFixed(4)}</td>
              <td>{line.notes ?? ""}</td>
              <td>
                <button className="btn" onClick={() => onDeleteAddin(line.substrate_batch_addin_id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Bags</h2>
      <ul className="list">
        {bags.map((b) => (
          <li key={b.bag_id}>
            <a href={`/bags/${encodeURIComponent(b.bag_id)}`}>{b.bag_id}</a> —{" "}
            {b.status}
          </li>
        ))}
      </ul>
    </div>
  );
}
