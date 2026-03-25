"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { Bag } from "../../lib/types";

export default function BagsPage() {
  const [bags, setBags] = useState<Bag[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  async function loadBags() {
    const params = new URLSearchParams();
    if (filterType) params.set("bag_type", filterType);
    if (filterStatus) params.set("status", filterStatus);
    const data = await apiGet<Bag[]>(`/bags?${params.toString()}`);
    setBags(data);
  }

  useEffect(() => {
    loadBags().catch((e) => setError(String(e)));
  }, [filterType, filterStatus]);

  return (
    <div>
      <div className="card">
        <h1>Bags</h1>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <label>
            Type
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All</option>
              <option value="SPAWN">Spawn</option>
              <option value="SUBSTRATE">Substrate</option>
            </select>
          </label>
          <label>
            Status
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">All</option>
              <option value="STERILIZED">Sterilized</option>
              <option value="PASTEURIZED">Pasteurized</option>
              <option value="INOCULATED">Inoculated</option>
              <option value="INCUBATING">Incubating</option>
              <option value="READY">Ready</option>
              <option value="FRUITING">Fruiting</option>
              <option value="FLUSH_1_COMPLETE">Flush 1 Complete</option>
              <option value="FLUSH_2_COMPLETE">Flush 2 Complete</option>
              <option value="DISPOSED">Disposed</option>
              <option value="CONTAMINATED">Contaminated</option>
              <option value="CONSUMED">Consumed</option>
            </select>
          </label>
          <a className="btn" href="/bags/create/spawn">Create Spawn Records</a>
          <a className="btn" href="/events/spawn-inoculation">Spawn Inoculation</a>
          <a className="btn" href="/bags/create/substrate">Create Substrate Records</a>
          <a className="btn" href="/events/inoculation">Substrate Inoculation</a>
        </div>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Bag Ref</th>
              <th>Type</th>
              <th>Status</th>
              <th>Label</th>
              <th>Inoculated</th>
              <th>Incubation</th>
              <th>Ready</th>
              <th>Fruiting</th>
            </tr>
          </thead>
          <tbody>
            {bags.map((b) => (
              <tr key={b.bag_id}>
                <td>
                  <a href={`/bags/${encodeURIComponent(b.bag_ref)}`}>{b.bag_ref}</a>
                </td>
                <td>{b.bag_type}</td>
                <td>{b.status}</td>
                <td>{b.bag_code ? "Assigned" : "Unlabeled"}</td>
                <td>{b.inoculated_at ? new Date(b.inoculated_at).toLocaleDateString() : "-"}</td>
                <td>{b.incubation_start_at ? new Date(b.incubation_start_at).toLocaleDateString() : "-"}</td>
                <td>{b.ready_at ? new Date(b.ready_at).toLocaleDateString() : "-"}</td>
                <td>{b.fruiting_start_at ? new Date(b.fruiting_start_at).toLocaleDateString() : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {bags.length === 0 && <p>No bags found.</p>}
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
