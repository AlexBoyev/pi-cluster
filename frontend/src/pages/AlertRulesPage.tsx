import { FormEvent, useEffect, useState } from "react";
import { createRule, deleteRule, getAlertRules, RuleFormData, updateRule } from "../api/prom_rules";
import { useAuth } from "../context/AuthContext";
import type { AlertRule, RuleGroup } from "../types/prom_rules";
import "./AlertRulesPage.css";
import "./NotificationsPage.css";

const EMPTY_FORM: RuleFormData = {
  group: "", alert: "", expr: "", for: "5m", severity: "warning", summary: "", description: "",
};

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

function RuleRow({
  rule, group, isAdmin, onSaved, onDeleted,
}: {
  rule: AlertRule; group: string; isAdmin: boolean;
  onSaved: () => void; onDeleted: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sev = severityCls(rule.labels);

  const [form, setForm] = useState({
    expr: rule.query,
    for: fmtDuration(rule.duration),
    severity: rule.labels.severity || "warning",
    summary: rule.annotations.summary || "",
    description: rule.annotations.description || "",
  });

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await updateRule(group, rule.name, form);
      setEditing(false);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update rule");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteRule(group, rule.name);
      onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete rule");
      setDeleting(false);
      setConfirmDel(false);
    }
  }

  const gridCls = `ar-row-grid${isAdmin ? " ar-grid-admin" : ""}`;

  return (
    <div className={`ar-row-group ${rule.state === "firing" ? "ar-row-firing" : ""}`}>
      <div className={gridCls} onClick={() => setExpanded((e) => !e)}>
        <span className="ar-expander">{expanded ? "▾" : "▸"}</span>
        <div className="ar-rule-name">
          {rule.name}
          {sev && <span className={`ar-sev ${sev}`}>{rule.labels.severity || rule.labels.level}</span>}
        </div>
        <div>
          <span className={`ar-state-badge ${stateCls(rule.state)}`}>{rule.state}</span>
          {rule.alerts.length > 0 && (
            <span className="ar-alert-count">×{rule.alerts.length}</span>
          )}
        </div>
        <div className="ar-mono ar-dim">{fmtDuration(rule.duration)}</div>
        <div className="ar-anno ar-dim">{rule.annotations.summary || rule.annotations.description || "—"}</div>
        {isAdmin && (
          <div onClick={(e) => e.stopPropagation()}>
            <div className="notif-actions">
              <button className="notif-btn-toggle" onClick={() => setEditing((v) => !v)}>
                {editing ? "Cancel" : "Edit"}
              </button>
              {confirmDel ? (
                <div className="notif-confirm">
                  <button className="notif-btn-del-confirm" onClick={handleDelete} disabled={deleting}>
                    {deleting ? "…" : "Delete"}
                  </button>
                  <button className="notif-btn-cancel" onClick={() => setConfirmDel(false)}>Cancel</button>
                </div>
              ) : (
                <button className="notif-btn-del" onClick={() => setConfirmDel(true)}>Delete</button>
              )}
            </div>
          </div>
        )}
      </div>
      {editing && (
        <div className="ar-row-detail">
          {error && <div className="err-banner">{error}</div>}
          <form className="notif-form" onSubmit={handleSave} style={{ padding: "0.6rem 0" }}>
            <div className="notif-field notif-field-wide">
              <label className="notif-label">PromQL expression</label>
              <input
                className="notif-input notif-mono"
                value={form.expr}
                onChange={(e) => setForm((f) => ({ ...f, expr: e.target.value }))}
                required
                disabled={saving}
              />
            </div>
            <div className="notif-field">
              <label className="notif-label">For</label>
              <input
                className="notif-input notif-mono"
                style={{ width: "80px" }}
                placeholder="5m"
                value={form.for}
                onChange={(e) => setForm((f) => ({ ...f, for: e.target.value }))}
                required
                disabled={saving}
              />
            </div>
            <div className="notif-field">
              <label className="notif-label">Severity</label>
              <select
                className="notif-input"
                value={form.severity}
                onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value }))}
                disabled={saving}
              >
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="notif-field notif-field-wide">
              <label className="notif-label">Summary</label>
              <input
                className="notif-input"
                value={form.summary}
                onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
                disabled={saving}
              />
            </div>
            <div className="notif-field notif-field-wide">
              <label className="notif-label">Description</label>
              <input
                className="notif-input"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                disabled={saving}
              />
            </div>
            <div className="notif-field notif-field-submit">
              <button className="notif-btn-primary" type="submit" disabled={saving}>
                {saving ? "Saving…" : "Save & publish"}
              </button>
            </div>
          </form>
        </div>
      )}
      {expanded && !editing && (
        <div className="ar-row-detail">
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
        </div>
      )}
    </div>
  );
}

export default function AlertRulesPage() {
  const { role } = useAuth();
  const isAdmin = role === "admin";

  const [groups, setGroups]   = useState<RuleGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [stateFilter, setStateFilter] = useState<"all" | "firing" | "pending" | "inactive">("all");
  const [search, setSearch]   = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating]     = useState(false);
  const [createForm, setCreateForm] = useState<RuleFormData>(EMPTY_FORM);

  function refresh() {
    setLoading(true);
    getAlertRules()
      .then((res) => {
        if (res.status === "success") setGroups(res.data.groups);
        else setError("Prometheus returned an error");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load alert rules"))
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createRule(createForm);
      setCreateForm(EMPTY_FORM);
      setShowCreate(false);
      refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    } finally {
      setCreating(false);
    }
  }

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
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <span className="ar-count">{filtered.length} rules · {groups.length} groups</span>
          {isAdmin && (
            <button className="notif-btn-primary" onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? "Cancel" : "+ Add Rule"}
            </button>
          )}
        </div>
      </div>

      {showCreate && isAdmin && (
        <div className="notif-form-card" style={{ marginBottom: "1rem" }}>
          <form className="notif-form" onSubmit={handleCreate}>
            <div className="notif-field">
              <label className="notif-label">Group</label>
              <input
                className="notif-input"
                placeholder="node-health"
                value={createForm.group}
                onChange={(e) => setCreateForm((f) => ({ ...f, group: e.target.value }))}
                required
                disabled={creating}
              />
            </div>
            <div className="notif-field">
              <label className="notif-label">Alert name</label>
              <input
                className="notif-input"
                placeholder="HighDiskIO"
                value={createForm.alert}
                onChange={(e) => setCreateForm((f) => ({ ...f, alert: e.target.value }))}
                required
                disabled={creating}
              />
            </div>
            <div className="notif-field notif-field-wide">
              <label className="notif-label">PromQL expression</label>
              <input
                className="notif-input notif-mono"
                placeholder={'up{job="node-exporter"} == 0'}
                value={createForm.expr}
                onChange={(e) => setCreateForm((f) => ({ ...f, expr: e.target.value }))}
                required
                disabled={creating}
              />
            </div>
            <div className="notif-field">
              <label className="notif-label">For</label>
              <input
                className="notif-input notif-mono"
                style={{ width: "80px" }}
                placeholder="5m"
                value={createForm.for}
                onChange={(e) => setCreateForm((f) => ({ ...f, for: e.target.value }))}
                required
                disabled={creating}
              />
            </div>
            <div className="notif-field">
              <label className="notif-label">Severity</label>
              <select
                className="notif-input"
                value={createForm.severity}
                onChange={(e) => setCreateForm((f) => ({ ...f, severity: e.target.value }))}
                disabled={creating}
              >
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="notif-field notif-field-wide">
              <label className="notif-label">Summary</label>
              <input
                className="notif-input"
                placeholder="High disk I/O on {{ $labels.node_name }}"
                value={createForm.summary}
                onChange={(e) => setCreateForm((f) => ({ ...f, summary: e.target.value }))}
                disabled={creating}
              />
            </div>
            <div className="notif-field notif-field-wide">
              <label className="notif-label">Description</label>
              <input
                className="notif-input"
                value={createForm.description}
                onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))}
                disabled={creating}
              />
            </div>
            <div className="notif-field notif-field-submit">
              <button className="notif-btn-primary" type="submit" disabled={creating}>
                {creating ? "Publishing…" : "Create & publish"}
              </button>
            </div>
          </form>
          <div className="notif-help-sub" style={{ marginTop: "0.6rem" }}>
            Writes directly to <code>prometheus/alerts.yml</code>, commits and pushes it, then
            reloads Prometheus — takes a few seconds. An existing group name adds to that group;
            a new name creates one.
          </div>
        </div>
      )}

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
              <div className="ar-rows-wrap">
                <div className="ar-rows">
                  <div className={`ar-row-head${isAdmin ? " ar-grid-admin" : ""}`}>
                    <span></span>
                    <span>Rule</span>
                    <span>State</span>
                    <span>For</span>
                    <span>Summary</span>
                    {isAdmin && <span></span>}
                  </div>
                  {rules.map((r) => (
                    <RuleRow
                      key={r.name}
                      rule={r}
                      group={groupName}
                      isAdmin={isAdmin}
                      onSaved={refresh}
                      onDeleted={refresh}
                    />
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
