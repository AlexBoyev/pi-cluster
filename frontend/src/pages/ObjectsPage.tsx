import { useEffect, useState } from "react";
import { listDaemonSets, listStatefulSets } from "../api/k8s_objects";
import type { DaemonSetInfo, StatefulSetInfo } from "../types/k8s_objects";
import "./ObjectsPage.css";

type Tab = "statefulsets" | "daemonsets";

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString();
}

export default function ObjectsPage() {
  const [tab, setTab] = useState<Tab>("statefulsets");
  const [statefulSets, setStatefulSets] = useState<StatefulSetInfo[]>([]);
  const [daemonSets, setDaemonSets]     = useState<DaemonSetInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([listStatefulSets(), listDaemonSets()])
      .then(([ss, ds]) => { setStatefulSets(ss); setDaemonSets(ds); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load objects"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="obj-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">StatefulSets</div>
          <div className="summ-value sv-blue">{statefulSets.length}</div>
          <div className="summ-sub">stateful workloads</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">SS Ready</div>
          <div className="summ-value sv-green">
            {statefulSets.filter((s) => s.ready_replicas === s.replicas && s.replicas > 0).length}
          </div>
          <div className="summ-sub">fully available</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">DaemonSets</div>
          <div className="summ-value sv-blue">{daemonSets.length}</div>
          <div className="summ-sub">node-level workloads</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">DS Ready</div>
          <div className="summ-value sv-green">
            {daemonSets.filter((d) => d.available === d.desired && d.desired > 0).length}
          </div>
          <div className="summ-sub">fully available</div>
        </div>
      </div>

      <div className="obj-toolbar">
        <div className="obj-tabs">
          <button className={`obj-tab${tab === "statefulsets" ? " active" : ""}`} onClick={() => setTab("statefulsets")}>
            StatefulSets
          </button>
          <button className={`obj-tab${tab === "daemonsets" ? " active" : ""}`} onClick={() => setTab("daemonsets")}>
            DaemonSets
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading objects…</span></div>
      ) : tab === "statefulsets" ? (
        statefulSets.length === 0 ? (
          <div className="obj-empty">No StatefulSets found.</div>
        ) : (
          <div className="obj-table-wrap">
            <table className="obj-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Namespace</th>
                  <th>Replicas</th>
                  <th>Service</th>
                  <th>Images</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {statefulSets.map((ss) => {
                  const ready = ss.ready_replicas === ss.replicas && ss.replicas > 0;
                  return (
                    <tr key={`${ss.namespace}/${ss.name}`}>
                      <td className="obj-name">{ss.name}</td>
                      <td className="obj-mono">{ss.namespace}</td>
                      <td>
                        <span className={`obj-badge ${ready ? "obj-ready" : "obj-not-ready"}`}>
                          {ss.ready_replicas}/{ss.replicas}
                        </span>
                      </td>
                      <td className="obj-mono obj-dim">{ss.service_name || "—"}</td>
                      <td className="obj-images">
                        {ss.images.map((img) => <span key={img} className="obj-image-tag">{img}</span>)}
                      </td>
                      <td className="obj-mono obj-dim">{fmtDate(ss.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      ) : (
        daemonSets.length === 0 ? (
          <div className="obj-empty">No DaemonSets found.</div>
        ) : (
          <div className="obj-table-wrap">
            <table className="obj-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Namespace</th>
                  <th>Desired</th>
                  <th>Ready</th>
                  <th>Available</th>
                  <th>Images</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {daemonSets.map((ds) => {
                  const ready = ds.available === ds.desired && ds.desired > 0;
                  return (
                    <tr key={`${ds.namespace}/${ds.name}`}>
                      <td className="obj-name">{ds.name}</td>
                      <td className="obj-mono">{ds.namespace}</td>
                      <td className="obj-mono">{ds.desired}</td>
                      <td>
                        <span className={`obj-badge ${ready ? "obj-ready" : "obj-not-ready"}`}>
                          {ds.ready}
                        </span>
                      </td>
                      <td className="obj-mono">{ds.available}</td>
                      <td className="obj-images">
                        {ds.images.map((img) => <span key={img} className="obj-image-tag">{img}</span>)}
                      </td>
                      <td className="obj-mono obj-dim">{fmtDate(ds.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
