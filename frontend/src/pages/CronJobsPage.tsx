import { FormEvent, useEffect, useState } from "react";
import { createCronJob, deleteCronJob, listCronJobRuns, listCronJobs, resumeCronJob, suspendCronJob } from "../api/cronjobs";
import { listNamespaces } from "../api/namespaces";
import type { CronJobInfo, JobRun } from "../types/cronjob";
import "./CronJobsPage.css";

function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function fmtDuration(start: string | null, end: string | null): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

function JobRunRow({ run }: { run: JobRun }) {
  const succeeded = run.succeeded > 0;
  const failed = run.failed > 0;
  const active = run.active > 0;
  const state = active ? "running" : failed ? "failed" : succeeded ? "succeeded" : "unknown";
  return (
    <tr className={`cj-run-row cj-run-${state}`}>
      <td className="cj-run-name">{run.name}</td>
      <td><span className={`cj-run-badge crb-${state}`}>{state}</span></td>
      <td className="cj-run-time">{fmtDate(run.start_time)}</td>
      <td className="cj-run-time">{fmtDuration(run.start_time, run.completion_time)}</td>
    </tr>
  );
}

export default function CronJobsPage() {
  const [cronJobs, setCronJobs] = useState<CronJobInfo[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>(["pi-apps"]);
  const [ns, setNs] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [togglingName, setTogglingName] = useState<string | null>(null);
  const [deletingName, setDeletingName] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [runsTarget, setRunsTarget] = useState<string | null>(null);
  const [runs, setRuns] = useState<JobRun[]>([]);
  const [runsLoading, setRunsLoading] = useState(false);

  const [form, setForm] = useState({
    name: "", namespace: "pi-apps", schedule: "0 * * * *",
    image: "", command: "", env: "",
  });

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await listCronJobs(ns || undefined);
      setCronJobs(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load CronJobs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    listNamespaces()
      .then((list) => setNamespaces(list.map((n) => n.name)))
      .catch(() => {});
  }, []);

  useEffect(() => { refresh(); }, [ns]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    const envVars: Record<string, string> = {};
    for (const line of form.env.split("\n")) {
      const eq = line.indexOf("=");
      if (eq === -1) continue;
      const k = line.slice(0, eq).trim();
      const v = line.slice(eq + 1);
      if (k) envVars[k] = v;
    }
    try {
      await createCronJob({
        name: form.name,
        namespace: form.namespace,
        schedule: form.schedule,
        image: form.image,
        command: form.command.trim() ? form.command.trim().split(/\s+/) : [],
        env_vars: envVars,
      });
      setForm({ name: "", namespace: "pi-apps", schedule: "0 * * * *", image: "", command: "", env: "" });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create CronJob");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggle(cj: CronJobInfo) {
    setTogglingName(cj.name);
    try {
      if (cj.suspended) {
        await resumeCronJob(cj.name, cj.namespace);
      } else {
        await suspendCronJob(cj.name, cj.namespace);
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to toggle CronJob");
    } finally {
      setTogglingName(null);
    }
  }

  async function handleDelete(name: string, namespace: string) {
    setDeletingName(name);
    try {
      await deleteCronJob(name, namespace);
      setConfirmDelete(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete CronJob");
    } finally {
      setDeletingName(null);
    }
  }

  async function handleShowRuns(cj: CronJobInfo) {
    setRunsTarget(cj.name);
    setRunsLoading(true);
    try {
      const data = await listCronJobRuns(cj.name, cj.namespace);
      setRuns(data);
    } catch {
      setRuns([]);
    } finally {
      setRunsLoading(false);
    }
  }

  return (
    <div className="cj-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">CronJobs</div>
          <div className="summ-value sv-blue">{cronJobs.length}</div>
          <div className="summ-sub">scheduled tasks</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Active</div>
          <div className="summ-value sv-green">{cronJobs.filter(c => !c.suspended).length}</div>
          <div className="summ-sub">running on schedule</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Suspended</div>
          <div className="summ-value sv-amber">{cronJobs.filter(c => c.suspended).length}</div>
          <div className="summ-sub">paused</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Create CronJob</span>
        <div className="cj-ns-wrap">
          <label className="cj-ns-lbl">Filter namespace:</label>
          <select className="cj-ns-select" value={ns} onChange={(e) => setNs(e.target.value)}>
            <option value="">All namespaces</option>
            {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      <div className="cj-form-card">
        <form className="cj-form" onSubmit={handleCreate}>
          <div className="cj-field">
            <label className="cj-label">Name</label>
            <input className="cj-input" placeholder="daily-backup" value={form.name}
              onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
              pattern="^[a-z][a-z0-9-]{0,62}$" required disabled={creating} />
          </div>
          <div className="cj-field">
            <label className="cj-label">Namespace</label>
            <select className="cj-input" value={form.namespace}
              onChange={(e) => setForm(f => ({ ...f, namespace: e.target.value }))} disabled={creating}>
              {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="cj-field">
            <label className="cj-label">Schedule (cron)</label>
            <input className="cj-input cj-mono" placeholder="0 * * * *" value={form.schedule}
              onChange={(e) => setForm(f => ({ ...f, schedule: e.target.value }))}
              required disabled={creating} />
            <span className="cj-hint-sm">min hour day month weekday</span>
          </div>
          <div className="cj-field cj-field-wide">
            <label className="cj-label">Image</label>
            <input className="cj-input" placeholder="busybox:latest" value={form.image}
              onChange={(e) => setForm(f => ({ ...f, image: e.target.value }))}
              required disabled={creating} />
          </div>
          <div className="cj-field cj-field-wide">
            <label className="cj-label">Command (optional, space-separated)</label>
            <input className="cj-input cj-mono" placeholder="/bin/sh -c 'echo hello'" value={form.command}
              onChange={(e) => setForm(f => ({ ...f, command: e.target.value }))} disabled={creating} />
          </div>
          <div className="cj-field cj-field-wide">
            <label className="cj-label">Env vars (KEY=value, one per line)</label>
            <textarea className="cj-textarea" rows={3} value={form.env}
              onChange={(e) => setForm(f => ({ ...f, env: e.target.value }))} disabled={creating} />
          </div>
          <div className="cj-field cj-field-submit">
            <button className="cj-btn-primary" type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>

      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">CronJobs</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading CronJobs…</span></div>
      ) : cronJobs.length === 0 ? (
        <div className="cj-empty">No CronJobs found.</div>
      ) : (
        <div className="cj-table-wrap">
          <table className="cj-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Namespace</th>
                <th>Schedule</th>
                <th>Image</th>
                <th>Active</th>
                <th>Last run</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cronJobs.map((cj) => (
                <tr key={`${cj.namespace}/${cj.name}`} className={cj.suspended ? "cj-row-suspended" : ""}>
                  <td className="cj-name">{cj.name}</td>
                  <td className="cj-mono">{cj.namespace}</td>
                  <td><code className="cj-schedule">{cj.schedule}</code></td>
                  <td className="cj-mono cj-img">{cj.image}</td>
                  <td className="cj-center">
                    {cj.active_jobs > 0
                      ? <span className="cj-active-badge">{cj.active_jobs} running</span>
                      : <span className="cj-dim">—</span>}
                  </td>
                  <td className="cj-date">{fmtDate(cj.last_schedule_time)}</td>
                  <td>
                    <span className={`cj-status-badge ${cj.suspended ? "csb-suspended" : "csb-active"}`}>
                      {cj.suspended ? "Suspended" : "Active"}
                    </span>
                  </td>
                  <td>
                    <div className="cj-actions">
                      <button className="cj-btn-runs" onClick={() => handleShowRuns(cj)}>Runs</button>
                      <button
                        className={`cj-btn-toggle${cj.suspended ? " cj-resume" : ""}`}
                        onClick={() => handleToggle(cj)}
                        disabled={togglingName === cj.name}
                      >
                        {togglingName === cj.name ? "…" : cj.suspended ? "Resume" : "Suspend"}
                      </button>
                      {confirmDelete === cj.name ? (
                        <div className="cj-confirm">
                          <button className="cj-btn-del-confirm" onClick={() => handleDelete(cj.name, cj.namespace)} disabled={deletingName === cj.name}>
                            {deletingName === cj.name ? "…" : "Delete"}
                          </button>
                          <button className="cj-btn-cancel" onClick={() => setConfirmDelete(null)}>Cancel</button>
                        </div>
                      ) : (
                        <button className="cj-btn-del" onClick={() => setConfirmDelete(cj.name)}>Delete</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {runsTarget && (
        <div className="cj-overlay" onClick={(e) => { if (e.target === e.currentTarget) setRunsTarget(null); }}>
          <div className="cj-modal">
            <div className="cj-modal-header">
              <span className="cj-modal-title">Job runs — <span className="cj-modal-name">{runsTarget}</span></span>
              <button className="cj-modal-close" onClick={() => setRunsTarget(null)}>✕</button>
            </div>
            <div className="cj-modal-body">
              {runsLoading ? (
                <div className="cj-modal-loading"><div className="spinner" /> Loading runs…</div>
              ) : runs.length === 0 ? (
                <div className="cj-modal-empty">No job history found. Jobs may have been garbage-collected.</div>
              ) : (
                <table className="cj-runs-table">
                  <thead>
                    <tr><th>Job</th><th>Status</th><th>Started</th><th>Duration</th></tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => <JobRunRow key={r.name} run={r} />)}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
