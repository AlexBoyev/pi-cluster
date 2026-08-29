import { useEffect, useState } from "react";
import { listLimitRanges, listResourceQuotas } from "../api/quotas";
import type { LimitRangeInfo, ResourceQuotaInfo } from "../types/quota";
import "./QuotasPage.css";

type Tab = "quotas" | "limitranges";

function parseQty(s: string): number {
  if (!s || s === "0") return 0;
  if (s.endsWith("m"))  return parseFloat(s) / 1000;
  if (s.endsWith("Ki")) return parseFloat(s) * 1024;
  if (s.endsWith("Mi")) return parseFloat(s) * 1024 ** 2;
  if (s.endsWith("Gi")) return parseFloat(s) * 1024 ** 3;
  if (s.endsWith("k"))  return parseFloat(s) * 1000;
  if (s.endsWith("M"))  return parseFloat(s) * 1_000_000;
  if (s.endsWith("G"))  return parseFloat(s) * 1_000_000_000;
  return parseFloat(s) || 0;
}

function UsageBar({ used, hard }: { used: string; hard: string }) {
  const usedN = parseQty(used);
  const hardN = parseQty(hard);
  if (!hardN) return <span className="q-mono q-dim">{used}</span>;
  const pct = Math.min((usedN / hardN) * 100, 100);
  const cls = pct >= 90 ? "q-bar-crit" : pct >= 70 ? "q-bar-warn" : "q-bar-ok";
  return (
    <div className="q-usage">
      <div className="q-bar-track">
        <div className={`q-bar-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="q-usage-label">{used} / {hard} ({pct.toFixed(0)}%)</span>
    </div>
  );
}

export default function QuotasPage() {
  const [tab, setTab]           = useState<Tab>("quotas");
  const [quotas, setQuotas]     = useState<ResourceQuotaInfo[]>([]);
  const [limits, setLimits]     = useState<LimitRangeInfo[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [nsFilter, setNsFilter] = useState("");

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([listResourceQuotas(), listLimitRanges()])
      .then(([qr, lr]) => {
        if (qr.status === "fulfilled") setQuotas(qr.value);
        if (lr.status === "fulfilled") setLimits(lr.value);
        const errs = [qr, lr].filter((r): r is PromiseRejectedResult => r.status === "rejected");
        if (errs.length) setError(errs[0].reason instanceof Error ? errs[0].reason.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, []);

  const namespaces = Array.from(new Set([
    ...quotas.map((q) => q.namespace),
    ...limits.map((l) => l.namespace),
  ])).sort();

  const filteredQuotas = nsFilter ? quotas.filter((q) => q.namespace === nsFilter) : quotas;
  const filteredLimits = nsFilter ? limits.filter((l) => l.namespace === nsFilter) : limits;

  return (
    <div className="q-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Resource Quotas</div>
          <div className="summ-value sv-blue">{quotas.length}</div>
          <div className="summ-sub">namespace limits</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Limit Ranges</div>
          <div className="summ-value sv-amber">{limits.length}</div>
          <div className="summ-sub">per-container limits</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">Namespaces</div>
          <div className="summ-value sv-blue">{namespaces.length}</div>
          <div className="summ-sub">with quota policies</div>
        </div>
      </div>

      <div className="q-toolbar">
        <div className="q-tabs">
          <button className={`q-tab${tab === "quotas" ? " active" : ""}`} onClick={() => setTab("quotas")}>
            Resource Quotas
          </button>
          <button className={`q-tab${tab === "limitranges" ? " active" : ""}`} onClick={() => setTab("limitranges")}>
            Limit Ranges
          </button>
        </div>
        {namespaces.length > 1 && (
          <div className="q-ns-wrap">
            <label className="q-ns-lbl">Namespace:</label>
            <select className="q-ns-select" value={nsFilter} onChange={(e) => setNsFilter(e.target.value)}>
              <option value="">All</option>
              {namespaces.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        )}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading quotas…</span></div>
      ) : tab === "quotas" ? (
        filteredQuotas.length === 0 ? (
          <div className="q-empty">No ResourceQuotas found. Add one with <code>kubectl create quota</code>.</div>
        ) : (
          <div className="q-quota-list">
            {filteredQuotas.map((rq) => (
              <div key={`${rq.namespace}/${rq.name}`} className="q-card">
                <div className="q-card-header">
                  <span className="q-card-name">{rq.name}</span>
                  <span className="q-card-ns">{rq.namespace}</span>
                </div>
                <table className="q-table">
                  <thead>
                    <tr><th>Resource</th><th>Usage</th></tr>
                  </thead>
                  <tbody>
                    {rq.resources.map((r) => (
                      <tr key={r.resource}>
                        <td className="q-mono q-resource">{r.resource}</td>
                        <td><UsageBar used={r.used} hard={r.hard} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )
      ) : (
        filteredLimits.length === 0 ? (
          <div className="q-empty">No LimitRanges found.</div>
        ) : (
          <div className="q-quota-list">
            {filteredLimits.map((lr) => (
              <div key={`${lr.namespace}/${lr.name}`} className="q-card">
                <div className="q-card-header">
                  <span className="q-card-name">{lr.name}</span>
                  <span className="q-card-ns">{lr.namespace}</span>
                </div>
                {lr.limits.length === 0 ? (
                  <div className="q-empty" style={{ padding: "0.5rem 0" }}>No limit entries.</div>
                ) : (
                  <table className="q-table">
                    <thead>
                      <tr><th>Type</th><th>Resource</th><th>Default Req</th><th>Default</th><th>Min</th><th>Max</th></tr>
                    </thead>
                    <tbody>
                      {lr.limits.map((item, i) => (
                        <tr key={i}>
                          <td><span className="q-type-badge">{item.type}</span></td>
                          <td className="q-mono q-resource">{item.resource}</td>
                          <td className="q-mono q-dim">{item.default_request ?? "—"}</td>
                          <td className="q-mono q-dim">{item.default ?? "—"}</td>
                          <td className="q-mono q-dim">{item.min ?? "—"}</td>
                          <td className="q-mono q-dim">{item.max ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
