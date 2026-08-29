import { useEffect, useState } from "react";
import { listJobs } from "../api/jobs";
import type { JobInfo } from "../types/job";
import "./JobsPage.css";

function stateCls(s: string): string {
  if (s === "succeeded") return "job-succeeded";
  if (s === "running")   return "job-running";
  if (s === "failed")    return "job-failed";
  return "job-unknown";
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtDuration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const endTs = end ? new Date(end).getTime() : Date.now();
  const ms = endTs - new Date(start).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

export default function JobsPage() {
  const [jobs, setJobs]       = useState<JobInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [nsFilter, setNsFilter] = useState("");
  const [stateFilter, setStateFilter] = useState<"all" | "running" | "succeeded" | "failed">("all");

  useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load jobs"))
      .finally(() => setLoading(false));
  }, []);

  const namespaces = Array.from(new Set(jobs.map((j) => j.namespace))).sort();
  const filtered = jobs
    .filter((j) => !nsFilter || j.namespace === nsFilter)
    .filter((j) => stateFilter === "all" || j.state === stateFilter);

  const running   = jobs.filter((j) => j.state === "running").length;
  const succeeded = jobs.filter((j) => j.state === "succeeded").length;
  const failed    = jobs.filter((j) => j.state === "failed").length;

  return (
    <div className="jobs-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total Jobs</div>
          <div className="summ-value sv-blue">{jobs.length}</div>
          <div className="summ-sub">batch job runs</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Succeeded</div>
          <div className="summ-value sv-green">{succeeded}</div>
          <div className="summ-sub">completed</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Running</div>
          <div className="summ-value sv-amber">{running}</div>
          <div className="summ-sub">in progress</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Failed</div>
          <div className="summ-value sv-red">{failed}</div>
          <div className="summ-sub">need attention</div>
        </div>
      </div>

      <div className="jobs-toolbar">
        <div className="jobs-filters">
          <select className="jobs-select" value={stateFilter} onChange={(e) => setStateFilter(e.target.value as typeof stateFilter)}>
            <option value="all">All states</option>
            <option value="running">Running</option>
            <option value="succeeded">Succeeded</option>
            <option value="failed">Failed</option>
          </select>
          {namespaces.length > 1 && (
            <select className="jobs-select" value={nsFilter} onChange={(e) => setNsFilter(e.target.value)}>
              <option value="">All namespaces</option>
              {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          )}
        </div>
        <span className="jobs-count">{filtered.length} jobs</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading jobs…</span></div>
      ) : filtered.length === 0 ? (
        <div className="jobs-empty">
          {jobs.length === 0
            ? "No batch jobs found. Jobs are created by CronJobs or directly via kubectl."
            : "No jobs match the current filter."}
        </div>
      ) : (
        <div className="jobs-table-wrap">
          <table className="jobs-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Namespace</th>
                <th>State</th>
                <th>✓ / ✗ / ⟳</th>
                <th>CronJob</th>
                <th>Started</th>
                <th>Duration</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((j) => (
                <tr key={`${j.namespace}/${j.name}`}>
                  <td className="jobs-name">{j.name}</td>
                  <td className="jobs-mono">{j.namespace}</td>
                  <td>
                    <span className={`jobs-badge ${stateCls(j.state)}`}>{j.state}</span>
                  </td>
                  <td className="jobs-mono jobs-counts">
                    <span className="jobs-ok">{j.succeeded}</span>
                    {" / "}
                    <span className="jobs-fail">{j.failed}</span>
                    {" / "}
                    <span className="jobs-act">{j.active}</span>
                  </td>
                  <td className="jobs-mono jobs-dim">{j.cron_job ?? "—"}</td>
                  <td className="jobs-mono jobs-dim">{fmtDate(j.start_time)}</td>
                  <td className="jobs-mono jobs-dim">{fmtDuration(j.start_time, j.completion_time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
