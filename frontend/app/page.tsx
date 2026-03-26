"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import type { DashboardOverview } from "../lib/types";

function formatDateTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatPercent(value: number | null | undefined) {
  if (value == null) return "-";
  return `${(value * 100).toFixed(1)}%`;
}

function formatWeight(value: number | null | undefined) {
  if (value == null) return "-";
  return `${value.toFixed(3)} kg`;
}

export default function Home() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiGet<DashboardOverview>("/dashboard/overview")
      .then((data) => {
        if (!active) return;
        setOverview(data);
        setError(null);
      })
      .catch((e) => {
        if (!active) return;
        setError(String(e));
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const summary = overview?.summary;
  const queueTotal = overview?.queues.reduce((sum, queue) => sum + queue.count, 0) ?? 0;

  return (
    <div className="dashboard">
      <section className="hero">
        <div>
          <p className="eyebrow">Operations Dashboard</p>
          <h1 className="heroTitle">Today&apos;s production picture in one place.</h1>
          <p className="heroText">
            Run the bag workflow from thermal batches through harvest, with open queues, recent activity, and traceability alerts surfaced first.
          </p>
        </div>
        <div className="heroActions">
          <a className="btn btnSolid" href="/sterilization-runs">Sterilization Runs</a>
          <a className="btn" href="/pasteurization-runs">Pasteurization Runs</a>
          <a className="btn" href="/reports">Reports</a>
        </div>
      </section>

      {error && (
        <section className="card">
          <h2>Dashboard unavailable</h2>
          <p className="error">{error}</p>
        </section>
      )}

      <section className="dashboardGrid">
        <article className="metricCard">
          <p className="metricLabel">Open queue items</p>
          <p className="metricValue">{loading ? "..." : queueTotal}</p>
          <p className="metricMeta">Actionable bag queues across spawn, substrate, and contamination follow-up.</p>
        </article>
        <article className="metricCard">
          <p className="metricLabel">Spawn bags tracked</p>
          <p className="metricValue">{loading ? "..." : summary?.total_spawn_bags ?? 0}</p>
          <p className="metricMeta">All spawn bags in the system, including consumed source bags.</p>
        </article>
        <article className="metricCard">
          <p className="metricLabel">Substrate bags tracked</p>
          <p className="metricValue">{loading ? "..." : summary?.total_substrate_bags ?? 0}</p>
          <p className="metricMeta">Substrate bags available for BE, contamination, and harvest analysis.</p>
        </article>
        <article className="metricCard">
          <p className="metricLabel">Contamination rate</p>
          <p className="metricValue">{loading ? "..." : formatPercent(summary?.contamination_rate)}</p>
          <p className="metricMeta">
            {loading ? "Loading contamination data..." : `${summary?.total_contaminated_bags ?? 0} contaminated bag(s) recorded.`}
          </p>
        </article>
        <article className="metricCard">
          <p className="metricLabel">Total harvest</p>
          <p className="metricValue">{loading ? "..." : formatWeight(summary?.total_harvest_kg)}</p>
          <p className="metricMeta">
            {loading ? "Loading harvest totals..." : `Overall BE: ${formatPercent(summary?.overall_bio_efficiency)}`}
          </p>
        </article>
      </section>

      <section className="dashboardColumns">
        <div className="stack">
          <div className="card">
            <div className="sectionHeader">
              <div>
                <p className="sectionEyebrow">Queues</p>
                <h2>Where the team should look next</h2>
              </div>
              <a className="textLink" href="/bags">Open all bags</a>
            </div>
            <div className="queueGrid">
              {overview?.queues.map((queue) => (
                <a key={queue.key} className={`queueCard queueCard${queue.tone}`} href={queue.href}>
                  <div className="queueTopline">
                    <span className="pill">{queue.count}</span>
                    <span className="queueLabel">{queue.label}</span>
                  </div>
                  <p className="muted">{queue.description}</p>
                </a>
              ))}
              {!loading && overview?.queues.length === 0 && <p className="muted">No active queues.</p>}
            </div>
          </div>

          <div className="card">
            <div className="sectionHeader">
              <div>
                <p className="sectionEyebrow">Alerts</p>
                <h2>Exceptions and follow-up</h2>
              </div>
              <a className="textLink" href="/reports">Open reports</a>
            </div>
            <div className="alertList">
              {overview?.alerts.map((alert, index) => (
                <a key={`${alert.title}-${index}`} className={`alertCard alert${alert.severity}`} href={alert.href}>
                  <p className="alertTitle">{alert.title}</p>
                  <p className="muted">{alert.detail}</p>
                </a>
              ))}
              {!loading && overview?.alerts.length === 0 && <p className="muted">No active alerts.</p>}
            </div>
          </div>
        </div>

        <div className="stack">
          <div className="card">
            <div className="sectionHeader">
              <div>
                <p className="sectionEyebrow">Runs</p>
                <h2>Sterilization worklist</h2>
              </div>
              <a className="textLink" href="/sterilization-runs">All sterilization runs</a>
            </div>
            <table className="table tableTight">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Recorded</th>
                  <th>Ready</th>
                  <th>Downstream</th>
                  <th>Next Action</th>
                </tr>
              </thead>
              <tbody>
                {overview?.sterilization_runs.map((run) => (
                  <tr key={`ster-${run.run_id}`}>
                    <td>
                      <a href={run.href}>{run.run_code}</a>
                      <div className="tableMeta">{new Date(run.unloaded_at).toLocaleDateString()}</div>
                    </td>
                    <td>{run.total_bags} / {run.planned_bag_count}</td>
                    <td>{run.ready_bags}</td>
                    <td>{run.downstream_bags}</td>
                    <td>{run.next_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && overview?.sterilization_runs.length === 0 && <p className="muted">No sterilization runs yet.</p>}
          </div>

          <div className="card">
            <div className="sectionHeader">
              <div>
                <p className="sectionEyebrow">Runs</p>
                <h2>Pasteurization worklist</h2>
              </div>
              <a className="textLink" href="/pasteurization-runs">All pasteurization runs</a>
            </div>
            <table className="table tableTight">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Recorded</th>
                  <th>Ready</th>
                  <th>Fruiting</th>
                  <th>Next Action</th>
                </tr>
              </thead>
              <tbody>
                {overview?.pasteurization_runs.map((run) => (
                  <tr key={`past-${run.run_id}`}>
                    <td>
                      <a href={run.href}>{run.run_code}</a>
                      <div className="tableMeta">{new Date(run.unloaded_at).toLocaleDateString()}</div>
                    </td>
                    <td>{run.total_bags} / {run.planned_bag_count}</td>
                    <td>{run.ready_bags}</td>
                    <td>{run.fruiting_bags}</td>
                    <td>{run.next_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && overview?.pasteurization_runs.length === 0 && <p className="muted">No pasteurization runs yet.</p>}
          </div>

          <div className="card">
            <div className="sectionHeader">
              <div>
                <p className="sectionEyebrow">Timeline</p>
                <h2>Recent bag activity</h2>
              </div>
            </div>
            <div className="activityList">
              {overview?.recent_activity.map((activity) => (
                <a key={`${activity.bag_id}-${activity.occurred_at}-${activity.event_type}`} className="activityItem" href={activity.href}>
                  <div className="activityHeader">
                    <strong>{activity.title}</strong>
                    <span className="tableMeta">{formatDateTime(activity.occurred_at)}</span>
                  </div>
                  <p>{activity.bag_ref} · {activity.bag_type}</p>
                  {activity.detail && <p className="muted">{activity.detail}</p>}
                </a>
              ))}
              {!loading && overview?.recent_activity.length === 0 && <p className="muted">No activity recorded yet.</p>}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
