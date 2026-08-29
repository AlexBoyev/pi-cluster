import { useEffect, useState } from "react";
import { listClusterRoleBindings, listClusterRoles, listServiceAccounts } from "../api/rbac";
import type { ClusterRoleBindingInfo, ClusterRoleInfo, ServiceAccountInfo } from "../types/rbac";
import "./RBACPage.css";

type Tab = "roles" | "bindings" | "serviceaccounts";

function fmtDate(s: string | null): string {
  if (!s) return "—";
  return new Date(s).toLocaleDateString();
}

export default function RBACPage() {
  const [tab, setTab] = useState<Tab>("roles");
  const [hideSystem, setHideSystem] = useState(true);

  const [roles, setRoles]       = useState<ClusterRoleInfo[]>([]);
  const [bindings, setBindings] = useState<ClusterRoleBindingInfo[]>([]);
  const [sas, setSAs]           = useState<ServiceAccountInfo[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [expandedRole, setExpandedRole] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      listClusterRoles(hideSystem),
      listClusterRoleBindings(hideSystem),
      listServiceAccounts(),
    ])
      .then(([r, b, s]) => { setRoles(r); setBindings(b); setSAs(s); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load RBAC"))
      .finally(() => setLoading(false));
  }, [hideSystem]);

  const nsGroups = sas.reduce<Record<string, ServiceAccountInfo[]>>((acc, sa) => {
    const ns = sa.namespace ?? "default";
    (acc[ns] ??= []).push(sa);
    return acc;
  }, {});

  return (
    <div className="rbac-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">ClusterRoles</div>
          <div className="summ-value sv-blue">{roles.length}</div>
          <div className="summ-sub">{hideSystem ? "non-system" : "all"}</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">Bindings</div>
          <div className="summ-value sv-blue">{bindings.length}</div>
          <div className="summ-sub">{hideSystem ? "non-system" : "all"}</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">ServiceAccounts</div>
          <div className="summ-value sv-green">{sas.length}</div>
          <div className="summ-sub">across all namespaces</div>
        </div>
        <div className="summ-card sc-blue">
          <div className="summ-label">Namespaces</div>
          <div className="summ-value sv-blue">{Object.keys(nsGroups).length}</div>
          <div className="summ-sub">with service accounts</div>
        </div>
      </div>

      <div className="rbac-toolbar">
        <div className="rbac-tabs">
          <button className={`rbac-tab${tab === "roles" ? " active" : ""}`} onClick={() => setTab("roles")}>
            ClusterRoles
          </button>
          <button className={`rbac-tab${tab === "bindings" ? " active" : ""}`} onClick={() => setTab("bindings")}>
            ClusterRoleBindings
          </button>
          <button className={`rbac-tab${tab === "serviceaccounts" ? " active" : ""}`} onClick={() => setTab("serviceaccounts")}>
            Service Accounts
          </button>
        </div>
        {(tab === "roles" || tab === "bindings") && (
          <label className="rbac-toggle">
            <input type="checkbox" checked={hideSystem} onChange={(e) => setHideSystem(e.target.checked)} />
            Hide system roles
          </label>
        )}
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading RBAC…</span></div>
      ) : tab === "roles" ? (
        roles.length === 0 ? (
          <div className="rbac-empty">No ClusterRoles found.</div>
        ) : (
          <div className="rbac-table-wrap">
            <table className="rbac-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Name</th>
                  <th>Rules</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {roles.map((r) => (
                  <>
                    <tr key={r.name} className="rbac-row" onClick={() => setExpandedRole(expandedRole === r.name ? null : r.name)}>
                      <td className="rbac-expander">{expandedRole === r.name ? "▾" : "▸"}</td>
                      <td className="rbac-name">{r.name}</td>
                      <td className="rbac-mono">{r.rules_count}</td>
                      <td className="rbac-mono rbac-dim">{fmtDate(r.created_at)}</td>
                    </tr>
                    {expandedRole === r.name && r.rules.map((rule, i) => (
                      <tr key={`${r.name}-rule-${i}`} className="rbac-rule-row">
                        <td></td>
                        <td colSpan={3}>
                          <div className="rbac-rule">
                            <div className="rbac-rule-section">
                              <span className="rbac-rule-lbl">Resources</span>
                              <div className="rbac-tags">
                                {rule.resources.map((res) => <span key={res} className="rbac-tag">{res}</span>)}
                              </div>
                            </div>
                            <div className="rbac-rule-section">
                              <span className="rbac-rule-lbl">Verbs</span>
                              <div className="rbac-tags">
                                {rule.verbs.map((v) => <span key={v} className={`rbac-tag rbac-verb ${v === "*" ? "rbac-verb-all" : ""}`}>{v}</span>)}
                              </div>
                            </div>
                            {rule.api_groups.filter(Boolean).length > 0 && (
                              <div className="rbac-rule-section">
                                <span className="rbac-rule-lbl">API Groups</span>
                                <div className="rbac-tags">
                                  {rule.api_groups.map((g) => <span key={g} className="rbac-tag rbac-group">{g || "core"}</span>)}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : tab === "bindings" ? (
        bindings.length === 0 ? (
          <div className="rbac-empty">No ClusterRoleBindings found.</div>
        ) : (
          <div className="rbac-table-wrap">
            <table className="rbac-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Subjects</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {bindings.map((b) => (
                  <tr key={b.name}>
                    <td className="rbac-name">{b.name}</td>
                    <td className="rbac-mono">
                      <span className="rbac-role-kind">{b.role_kind}</span>
                      {" / "}
                      {b.role_name}
                    </td>
                    <td>
                      <div className="rbac-subjects">
                        {b.subjects.map((s, i) => (
                          <div key={i} className="rbac-subject">
                            <span className="rbac-subj-kind">{s.kind}</span>
                            <span className="rbac-subj-name">{s.name}</span>
                            {s.namespace && <span className="rbac-subj-ns">{s.namespace}</span>}
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="rbac-mono rbac-dim">{fmtDate(b.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      ) : (
        sas.length === 0 ? (
          <div className="rbac-empty">No Service Accounts found.</div>
        ) : (
          <div className="rbac-sa-grid">
            {Object.entries(nsGroups).sort(([a], [b]) => a.localeCompare(b)).map(([ns, accounts]) => (
              <div key={ns} className="rbac-ns-group">
                <div className="rbac-ns-header">{ns}</div>
                <div className="rbac-table-wrap">
                  <table className="rbac-table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Secrets</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {accounts.map((sa) => (
                        <tr key={sa.name}>
                          <td className="rbac-name">{sa.name}</td>
                          <td className="rbac-mono">{sa.secrets_count}</td>
                          <td className="rbac-mono rbac-dim">{fmtDate(sa.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
