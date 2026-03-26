"use client";

import { startTransition, useDeferredValue, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiGet } from "../../lib/api";
import type { Bag } from "../../lib/types";

const STATUS_OPTIONS = [
  "",
  "STERILIZED",
  "PASTEURIZED",
  "INOCULATED",
  "INCUBATING",
  "READY",
  "FRUITING",
  "FLUSH_1_COMPLETE",
  "FLUSH_2_COMPLETE",
  "DISPOSED",
  "CONTAMINATED",
  "CONSUMED",
] as const;

type BagsPageClientProps = {
  initialBagType: string;
  initialStatus: string;
  initialBagRefContains: string;
};

function formatDate(value: string | null | undefined) {
  return value ? new Date(value).toLocaleDateString() : "-";
}

export default function BagsPageClient({
  initialBagType,
  initialStatus,
  initialBagRefContains,
}: BagsPageClientProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [bags, setBags] = useState<Bag[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState(initialBagType);
  const [filterStatus, setFilterStatus] = useState(initialStatus);
  const [bagRefSearch, setBagRefSearch] = useState(initialBagRefContains);
  const deferredBagRefSearch = useDeferredValue(bagRefSearch.trim());

  useEffect(() => {
    const params = new URLSearchParams();
    if (filterType) params.set("bag_type", filterType);
    if (filterStatus) params.set("status", filterStatus);
    if (deferredBagRefSearch) params.set("bag_ref_contains", deferredBagRefSearch);
    const nextQuery = params.toString();
    const currentQuery = window.location.search.startsWith("?")
      ? window.location.search.slice(1)
      : window.location.search;
    if (currentQuery === nextQuery) return;
    startTransition(() => {
      router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false });
    });
  }, [deferredBagRefSearch, filterStatus, filterType, pathname, router]);

  useEffect(() => {
    let active = true;
    const params = new URLSearchParams();
    if (filterType) params.set("bag_type", filterType);
    if (filterStatus) params.set("status", filterStatus);
    if (deferredBagRefSearch) params.set("bag_ref_contains", deferredBagRefSearch);

    setLoading(true);
    apiGet<Bag[]>(`/bags?${params.toString()}`)
      .then((data) => {
        if (!active) return;
        setBags(data);
        setError(null);
      })
      .catch((e) => {
        if (!active) return;
        setError(String(e));
        setBags([]);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [deferredBagRefSearch, filterStatus, filterType]);

  const unlabeledCount = bags.filter((bag) => !bag.bag_code).length;
  const readyCount = bags.filter((bag) => bag.status === "READY").length;
  const contaminatedCount = bags.filter((bag) => bag.status === "CONTAMINATED").length;

  return (
    <div className="stack">
      <section className="card">
        <div className="sectionHeader">
          <div>
            <p className="sectionEyebrow">Bag Queue</p>
            <h1>Bags</h1>
            <p className="muted">
              Search by printable code or internal bag ID, and use queue filters to move quickly from dashboard counts into operator work.
            </p>
          </div>
          <div className="toolbar">
            <a className="btn" href="/bags/create/spawn">Create Spawn Records</a>
            <a className="btn" href="/events/spawn-inoculation">Spawn Inoculation</a>
            <a className="btn" href="/bags/create/substrate">Create Substrate Records</a>
            <a className="btn" href="/events/inoculation">Substrate Inoculation</a>
          </div>
        </div>

        <div className="filterGrid">
          <label>
            Bag ref search
            <input
              placeholder="Bag code or internal bag ID"
              value={bagRefSearch}
              onChange={(e) => setBagRefSearch(e.target.value)}
            />
          </label>
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
              {STATUS_OPTIONS.filter((status) => status).map((status) => (
                <option key={status} value={status}>
                  {status.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <button
            className="btn"
            type="button"
            onClick={() => {
              setBagRefSearch("");
              setFilterType("");
              setFilterStatus("");
            }}
          >
            Clear Filters
          </button>
        </div>

        <div className="dashboardGrid dashboardGridCompact">
          <article className="metricCard">
            <p className="metricLabel">Visible bags</p>
            <p className="metricValue">{loading ? "..." : bags.length}</p>
            <p className="metricMeta">Current result set after filters.</p>
          </article>
          <article className="metricCard">
            <p className="metricLabel">Unlabeled records</p>
            <p className="metricValue">{loading ? "..." : unlabeledCount}</p>
            <p className="metricMeta">Bags still awaiting printable code assignment.</p>
          </article>
          <article className="metricCard">
            <p className="metricLabel">Ready now</p>
            <p className="metricValue">{loading ? "..." : readyCount}</p>
            <p className="metricMeta">Bags that can move into the next operator action.</p>
          </article>
          <article className="metricCard">
            <p className="metricLabel">Contaminated</p>
            <p className="metricValue">{loading ? "..." : contaminatedCount}</p>
            <p className="metricMeta">Visible contamination cases needing review.</p>
          </article>
        </div>
      </section>

      <section className="card">
        <table className="table tableTight">
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
            {bags.map((bag) => (
              <tr key={bag.bag_id}>
                <td>
                  <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                  <div className="tableMeta">{bag.bag_code ? "Printable code" : "Internal record"}</div>
                </td>
                <td>{bag.bag_type}</td>
                <td>
                  <span className={`statusBadge status${bag.status}`}>{bag.status.replaceAll("_", " ")}</span>
                </td>
                <td>{bag.bag_code ? "Assigned" : "Unlabeled"}</td>
                <td>{formatDate(bag.inoculated_at)}</td>
                <td>{formatDate(bag.incubation_start_at)}</td>
                <td>{formatDate(bag.ready_at)}</td>
                <td>{formatDate(bag.fruiting_start_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && bags.length === 0 && <p className="muted">No bags found for the current filters.</p>}
        {loading && <p className="muted">Loading bags...</p>}
        {error && <p className="error">{error}</p>}
      </section>
    </div>
  );
}
