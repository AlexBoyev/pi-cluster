import { useEffect, useState } from "react";
import { getAlertRules } from "../api/prom_rules";
import type { AlertRule, RuleGroup } from "../types/prom_rules";
import "./AlertRulesPage.css";

function stateCls(s: string): string {
  if (s === "firing")  return "ar-firing";
  if (s === "pending") return "ar-pending";
  return "ar-inactive";
}

function severityCls(labels: Record<string, string>): string {
  const sev = labels.severity || labels.level || "";
  if (sev === "critical" || sev === "page") return "ar-sev-crit";
  if (sev === "warning")  return "ar-sev-warn";
  if (sev === "info")     return "ar-sev-info";
  return "";
}

function fmtDuration(s: number): string {
  if (!s) return "—";
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

function RuleRow({ rule }: { rule: AlertRule }) {
  const [expanded, setExpanded] = useState(false);
  const sev = severityCls(rule.labels);

  return (
    <>
      <tr className={`ar-rule-row ${rule.state === "firing" ? "ar-row-firing" : ""}`} onClick={() => setExpanded((e) => !e)}>
        <td className="ar-expander">{expanded ? "▾" : "▸"}</td>
        <td className="ar-rule-name">
          {rule.name}
          {sev && <span className={`ar-sev ${sev}`}>{rule.labels.severity || rule.labels.level}</span>}
        </td>
        <td>
          <span className={`ar-state-badge ${stateCls(rule.state)}`}>{rule.state}</span>
          {rule.alerts.length > 0 && (
            <span className="ar-alert-count">×{rule.alerts.length}</span>
          )}
        </td>
        <td className="ar-mono ar-dim">{fmtDuration(rule.duration)}</td>
        <td className="ar-anno ar-dim">{rule.annotations.summary || rule.annotations.description || "—"}</td>
      </tr>
      {expanded && (
        <tr className="ar-detail-row">
          <td />
          <td colSpan={4}>
            <div className="ar-detail">
              <div className="ar-detail-section">
                <div className="ar-detail-lbl">PromQL Expression</div>
                <pre className="ar-expr">{rule.query}</pre>
              </div>
              {Object.keys(rule.labels).length > 0 && (
                <div className="ar-detail-section">
                  <div className="ar-detail-lbl">Labels</div>
                  <div className="ar-tags">
                    {Object.entries(rule.labels).map(([k, v]) => (
                      <span key={k} className="ar-label-tag">{k}=<span className="ar-label-val">{v}</span></span>
                    ))}
                  </div>
                </div>
              )}
              {rule.alerts.length > 0 && (
                <div className="ar-detail-section">
                  <div className="ar-detail-lbl">Active Alerts ({rule.alerts.length})</div>
                  <div className="ar-active-alerts">
                    {rule.alerts.map((a, i) => (
                      <div key={i} className="ar-active-alert">
                        <div className="ar-tags">
                          {Object.entries(a.labels).map(([k, v]) => (
                            <span key={k} className="ar-label-tag">{k}=<span className="ar-label-val">{v}</span></span>
                          ))}
                        </div>
                        <span className="ar-active-since">since {new Date(a.activeAt).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function AlertRulesPage() {
  const [groups, setGroups]   = useState<RuleGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [stateFilter, setStateFilter] = useState<"all" | "firing" | "pending" | "inactive">("all");
  const [search, setSearch]   = useState("");

  useEffect(() => {
    getAlertRules()
      .then((res) => {
        if (res.status === "success") setGroups(res.data.groups);
        else setError("Prometheus returned an error");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load alert rules"))
      .finally(() => setLoading(false));
  }, []);

  const allRules = groups.flatMap((g) =>
    g.rules.filter((r) => r.type === "alerting").map((r) => ({ ...r, _group: g.name }))
  );

  const filtered = allRules
    .filter((r) => stateFilter === "all" || r.state === stateFilter)
    .filter((r) => !search || r.name.toLowerCase().includes(search.toLowerCase()));

  const firing  = allRules.filter((r) => r.state === "firing").length;
  const pending = allRules.filter((r) => r.state === "pending").length;
  const inactive = allRules.filter((r) => r.state === "inactive").length;

  const groupedFiltered = filtered.reduce<Record<string, typeof filtered>>((acc, r) => {
    (acc[r._group] ??= []).push(r);
    return acc;
  }, {});

  return (
    <div className="ar-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Total Rules</div>
          <div className="summ-value sv-blue">{allRules.length}</div>
          <div className="summ-sub">alert rules</div>
        </div>
        <div className="summ-card sc-red">
          <div className="summ-label">Firing</div>
          <div className="summ-value sv-red">{firing}</div>
          <div className="summ-sub">active alerts</div>
        </div>
        <div className="summ-card sc-amber">
          <div className="summ-label">Pending</div>
          <div className="summ-value sv-amber">{pending}</div>
          <div className="summ-sub">below threshold</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Inactive</div>
          <div className="summ-value sv-green">{inactive}</div>
          <div className="summ-sub">not triggered</div>
        </div>
      </div>

      <div className="ar-toolbar">
        <div className="ar-filters">
          <input
            className="ar-search"
            placeholder="Search rules…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="ar-state-tabs">
            {(["all", "firing", "pending", "inactive"] as const).map((s) => (
              <button
                key={s}
                className={`ar-state-tab${stateFilter === s ? " active" : ""}${s !== "all" ? ` ar-tab-${s}` : ""}`}
                onClick={() => setStateFilter(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        <span className="ar-count">{filtered.length} rules · {groups.length} groups</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading alert rules from Prometheus…</span></div>
      ) : filtered.length === 0 ? (
        <div className="ar-empty">
          {allRules.length === 0
            ? "No alert rules found. Check that Prometheus is reachable and rules are configured."
            : "No rules match the current filter."}
        </div>
      ) : (
        <div className="ar-groups">
          {Object.entries(groupedFiltered).map(([groupName, rules]) => (
            <div key={groupName} className="ar-group">
              <div className="ar-group-header">
                <span className="ar-group-name">{groupName}</span>
                <span className="ar-group-count">{rules.length} rules</span>
                {rules.some((r) => r.state === "firing") && (
                  <span className="ar-group-firing">● FIRING</span>
                )}
              </div>
              <div className="ar-table-wrap">
                <table className="ar-table">
                  <thead>
                    <tr>
                      <th></th>
                      <th>Rule</th>
                      <th>State</th>
                      <th>For</th>
                      <th>Summary</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rules.map((r) => <RuleRow key={r.name} rule={r} />)}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
