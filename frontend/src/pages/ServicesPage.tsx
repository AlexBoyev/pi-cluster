import { useEffect, useState } from "react";
import { listIngresses, listServices } from "../api/services";
import { listNamespaces } from "../api/namespaces";
import type { IngressInfo, ServiceInfo } from "../types/service";
import "./ServicesPage.css";

function fmtDate(s: string | null) {
  if (!s) return "—";
  return new Date(s).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function SvcTypeBadge({ type }: { type: string }) {
  const cls = type === "LoadBalancer" ? "st-lb" : type === "NodePort" ? "st-np" : "st-cip";
  return <span className={`svc-type-badge ${cls}`}>{type}</span>;
}

export default function ServicesPage() {
  const [services, setServices] = useState<ServiceInfo[]>([]);
  const [ingresses, setIngresses] = useState<IngressInfo[]>([]);
  const [namespaces, setNamespaces] = useState<string[]>([]);
  const [ns, setNs] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"services" | "ingresses">("services");

  const refresh = async () => {
    setLoading(true);
    try {
      const [svcs, ings] = await Promise.all([
        listServices(ns || undefined),
        listIngresses(ns || undefined),
      ]);
      setServices(svcs);
      setIngresses(ings);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load network resources");
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

  const svcTypes = services.reduce<Record<string, number>>((acc, s) => {
    acc[s.type] = (acc[s.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="svc-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Services</div>
          <div className="summ-value sv-blue">{services.length}</div>
          <div className="summ-sub">{Object.entries(svcTypes).map(([t, c]) => `${c} ${t}`).join(", ") || "none"}</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Ingresses</div>
          <div className="summ-value sv-green">{ingresses.length}</div>
          <div className="summ-sub">{ingresses.filter(i => i.tls_hosts.length > 0).length} with TLS</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Hosts exposed</div>
          <div className="summ-value sv-amber">
            {new Set(ingresses.flatMap(i => i.rules.map(r => r.host).filter(Boolean))).size}
          </div>
          <div className="summ-sub">unique hostnames</div>
        </div>
      </div>

      <div className="svc-toolbar">
        <div className="svc-tabs">
          <button className={`svc-tab${tab === "services" ? " active" : ""}`} onClick={() => setTab("services")}>
            Services ({services.length})
          </button>
          <button className={`svc-tab${tab === "ingresses" ? " active" : ""}`} onClick={() => setTab("ingresses")}>
            Ingresses ({ingresses.length})
          </button>
        </div>
        <div className="svc-ns-wrap">
          <label className="svc-ns-lbl">Namespace:</label>
          <select className="svc-ns-select" value={ns} onChange={(e) => setNs(e.target.value)}>
            <option value="">All namespaces</option>
            {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading…</span></div>
      ) : tab === "services" ? (
        services.length === 0 ? (
          <div className="svc-empty">No services found.</div>
        ) : (
          <div className="svc-table-wrap">
            <table className="svc-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Namespace</th>
                  <th>Type</th>
                  <th>Cluster IP</th>
                  <th>Ports</th>
                  <th>Selector</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {services.map((s) => (
                  <tr key={`${s.namespace}/${s.name}`}>
                    <td className="svc-name">{s.name}</td>
                    <td className="svc-mono">{s.namespace}</td>
                    <td><SvcTypeBadge type={s.type} /></td>
                    <td className="svc-mono">{s.cluster_ip || "—"}</td>
                    <td>
                      <div className="svc-ports">
                        {s.ports.map((p, i) => (
                          <span key={i} className="svc-port-tag">
                            {p.port}{p.node_port ? `:${p.node_port}` : ""}
                            <span className="svc-port-proto">{p.protocol}</span>
                          </span>
                        ))}
                        {s.ports.length === 0 && <span className="svc-dim">—</span>}
                      </div>
                    </td>
                    <td>
                      <div className="svc-selectors">
                        {Object.entries(s.selector).slice(0, 2).map(([k, v]) => (
                          <span key={k} className="svc-sel-tag">{k}={v}</span>
                        ))}
                        {Object.keys(s.selector).length === 0 && <span className="svc-dim">—</span>}
                      </div>
                    </td>
                    <td className="svc-date">{fmtDate(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        ingresses.length === 0 ? (
          <div className="svc-empty">No ingresses found.</div>
        ) : (
          <div className="svc-table-wrap">
            <table className="svc-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Namespace</th>
                  <th>Class</th>
                  <th>Rules</th>
                  <th>TLS</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {ingresses.map((ing) => (
                  <tr key={`${ing.namespace}/${ing.name}`}>
                    <td className="svc-name">{ing.name}</td>
                    <td className="svc-mono">{ing.namespace}</td>
                    <td className="svc-mono">{ing.ingress_class || "—"}</td>
                    <td>
                      <div className="ing-rules">
                        {ing.rules.map((r, i) => (
                          <div key={i} className="ing-rule">
                            <span className="ing-host">{r.host || "*"}</span>
                            {r.paths.map((p, j) => (
                              <span key={j} className="ing-path">
                                {p.path} → {p.backend_service || "?"}{p.backend_port ? `:${p.backend_port}` : ""}
                              </span>
                            ))}
                          </div>
                        ))}
                        {ing.rules.length === 0 && <span className="svc-dim">—</span>}
                      </div>
                    </td>
                    <td>
                      {ing.tls_hosts.length > 0 ? (
                        <span className="ing-tls-badge">TLS ✓</span>
                      ) : (
                        <span className="svc-dim">—</span>
                      )}
                    </td>
                    <td className="svc-date">{fmtDate(ing.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
