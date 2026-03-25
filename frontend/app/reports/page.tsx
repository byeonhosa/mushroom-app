"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import type { ProductionReport, ReportGroup } from "../../lib/types";

function formatKg(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }
  return `${value.toFixed(3)} kg`;
}

function formatPercent(value: number | null | undefined) {
  if (value == null) {
    return "-";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function GroupTable({ title, groups }: { title: string; groups: ReportGroup[] }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      {groups.length === 0 ? (
        <p>No data yet.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Group</th>
              <th>Total Bags</th>
              <th>Contaminated</th>
              <th>Rate</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <tr key={`${title}-${group.key}`}>
                <td>{group.label}</td>
                <td>{group.total_bags}</td>
                <td>{group.contaminated_bags}</td>
                <td>{formatPercent(group.contamination_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function ReportsPage() {
  const [report, setReport] = useState<ProductionReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        const res = await apiGet<ProductionReport>("/reports/production");
        setReport(res);
      } catch (e: any) {
        setError(e?.message || String(e));
      }
    })();
  }, []);

  return (
    <div>
      <div className="card">
        <h1>Production Reports</h1>
        <p>
          Review biological efficiency, contamination loss, and run outcomes from the current production data.
        </p>
        {report && <p>Generated: {new Date(report.generated_at).toLocaleString()}</p>}
        {error && <p className="error">{error}</p>}
      </div>

      {!report ? (
        <div className="card">
          <p>Loading report...</p>
        </div>
      ) : (
        <>
          <div className="card">
            <h2>Summary</h2>
            <div className="kpis">
              <div>
                <div className="kpi">{report.summary.total_spawn_bags}</div>
                <div className="kpiLabel">Spawn Bags</div>
              </div>
              <div>
                <div className="kpi">{report.summary.total_substrate_bags}</div>
                <div className="kpiLabel">Substrate Bags</div>
              </div>
              <div>
                <div className="kpi">{report.summary.total_contaminated_bags}</div>
                <div className="kpiLabel">Contaminated Bags</div>
              </div>
              <div>
                <div className="kpi">{formatKg(report.summary.total_harvest_kg)}</div>
                <div className="kpiLabel">Total Harvest</div>
              </div>
              <div>
                <div className="kpi">{formatKg(report.summary.total_dry_weight_kg)}</div>
                <div className="kpiLabel">Dry Weight Basis</div>
              </div>
              <div>
                <div className="kpi">{formatPercent(report.summary.overall_bio_efficiency)}</div>
                <div className="kpiLabel">Overall BE</div>
              </div>
            </div>
            <p>Contamination rate: {formatPercent(report.summary.contamination_rate)}</p>
            <p>Substrate bags with harvests: {report.summary.substrate_bags_with_harvest}</p>
            <p>Substrate bags with dry-weight data: {report.summary.substrate_bags_with_dry_weight}</p>
          </div>

          <div className="card">
            <h2>Pasteurization Run Outcomes</h2>
            {report.pasteurization_runs.length === 0 ? (
              <p>No pasteurization outcomes yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Bags</th>
                    <th>Contaminated</th>
                    <th>Harvest</th>
                    <th>Dry Weight</th>
                    <th>BE</th>
                  </tr>
                </thead>
                <tbody>
                  {report.pasteurization_runs.map((run) => (
                    <tr key={run.pasteurization_run_id}>
                      <td>{run.run_code}</td>
                      <td>{run.total_bags}</td>
                      <td>
                        {run.contaminated_bags} ({formatPercent(run.contamination_rate)})
                      </td>
                      <td>{formatKg(run.total_harvest_kg)}</td>
                      <td>{formatKg(run.total_dry_weight_kg)}</td>
                      <td>{formatPercent(run.bio_efficiency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <GroupTable title="Contamination By Bag Type" groups={report.contamination_by_bag_type} />
          <GroupTable title="Contamination By Species" groups={report.contamination_by_species} />
          <GroupTable
            title="Contamination By Source Sterilization Run"
            groups={report.contamination_by_source_sterilization_run}
          />
          <GroupTable title="Contamination By Pasteurization Run" groups={report.contamination_by_pasteurization_run} />
          <GroupTable title="Contamination By Parent Spawn Bag" groups={report.contamination_by_parent_spawn_bag} />

          <div className="card">
            <h2>Substrate Bag Metrics</h2>
            {report.substrate_bags.length === 0 ? (
              <p>No substrate bags found.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Bag</th>
                    <th>Species</th>
                    <th>Pasteurization Run</th>
                    <th>Parent Spawn</th>
                    <th>Status</th>
                    <th>Harvest</th>
                    <th>Dry Weight</th>
                    <th>Source</th>
                    <th>BE</th>
                  </tr>
                </thead>
                <tbody>
                  {report.substrate_bags.map((bag) => (
                    <tr key={bag.bag_id}>
                      <td>
                        <a href={`/bags/${encodeURIComponent(bag.bag_ref)}`}>{bag.bag_ref}</a>
                      </td>
                      <td>{bag.species_code ?? "-"}</td>
                      <td>{bag.pasteurization_run_code ?? "-"}</td>
                      <td>{bag.parent_spawn_bag_ref ?? "-"}</td>
                      <td>{bag.contaminated ? "CONTAMINATED" : bag.status}</td>
                      <td>{formatKg(bag.total_harvest_kg)}</td>
                      <td>{formatKg(bag.dry_weight_kg)}</td>
                      <td>{bag.dry_weight_source ?? "-"}</td>
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
