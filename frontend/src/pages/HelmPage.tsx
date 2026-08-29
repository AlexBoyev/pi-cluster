import { useEffect, useState } from "react";
import { listHelmReleases } from "../api/helm";
import type { HelmRelease } from "../types/helm";
import "./HelmPage.css";

function statusCls(s: string): string {
  if (s === "deployed")   return "helm-deployed";
  if (s === "failed")     return "helm-failed";
  if (s === "pending-install" || s === "pending-upgrade") return "helm-pending";
  if (s === "uninstalling") return "helm-pending";
  if (s === "superseded") return "helm-superseded";
  return "helm-other";
}

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleString();
}

export default function HelmPage() {
  const [releases, setReleases] = useState<HelmRelease[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [nsFilter, setNsFilter] = useState("");

  useEffect(() => {
    listHelmReleases()
      .then(setReleases)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load Helm releases"))
      .finally(() => setLoading(false));
  }, []);

  const namespaces = Array.from(new Set(releases.map((r) => r.namespace))).sort();
  const filtered   = nsFilter ? releases.filter((r) => r.namespace === nsFilter) : releases;
  const deployed   = releases.filter((r) => r.status === "deployed").length;
  const failed     = releases.filter((r) => r.status === "failed").length;

  return (
    <div className="helm-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Releases</div>
          <div className="summ-value sv-blue">{releases.length}</div>
          <div className="summ-sub">total helm releases</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Deployed</div>
          <div className="summ-value sv-green">{deployed}</div>
          <div className="summ-sub">healthy</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Failed</div>
          <div className="summ-value sv-red">{failed}</div>
          <div className="summ-sub">need attention</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">Namespaces</div>
          <div className="summ-value sv-blue">{namespaces.length}</div>
          <div className="summ-sub">with releases</div>
        </div>
      </div>

      <div className="helm-toolbar">
        {namespaces.length > 1 && (
          <div className="helm-ns-wrap">
            <label className="helm-ns-lbl">Namespace:</label>
            <select className="helm-ns-select" value={nsFilter} onChange={(e) => setNsFilter(e.target.value)}>
              <option value="">All</option>
              {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading Helm releases…</span></div>
      ) : filtered.length === 0 ? (
        <div className="helm-empty">
          No Helm releases found. Releases appear here after running <code>helm install</code>.<br />
          Applications deployed via ArgoCD or <code>kubectl apply</code> do not create Helm releases.
        </div>
      ) : (
        <div className="helm-table-wrap">
          <table className="helm-table">
            <thead>
              <tr>
                <th>Release</th>
                <th>Namespace</th>
                <th>Chart</th>
                <th>Chart Ver.</th>
                <th>App Ver.</th>
                <th>Status</th>
                <th>Rev.</th>
                <th>Last Deployed</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={`${r.namespace}/${r.name}`}>
                  <td className="helm-name">{r.name}</td>
                  <td className="helm-mono">{r.namespace}</td>
                  <td className="helm-mono">{r.chart}</td>
                  <td className="helm-mono helm-dim">{r.chart_version || "—"}</td>
                  <td className="helm-mono helm-dim">{r.app_version || "—"}</td>
                  <td>
                    <span className={`helm-badge ${statusCls(r.status)}`}>{r.status}</span>
                  </td>
                  <td className="helm-mono helm-dim">{r.revision}</td>
                  <td className="helm-mono helm-dim">{fmtDate(r.last_deployed)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
