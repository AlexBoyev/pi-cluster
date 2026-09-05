import { FormEvent, useEffect, useState } from "react";
import {
  createChannel,
  deleteChannel,
  listChannels,
  testChannel,
  updateChannel,
} from "../api/notifications";
import type { ChannelType, NotificationChannel } from "../types/notification";
import "./NotificationsPage.css";

export default function NotificationsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [testingId, setTestingId]   = useState<number | null>(null);
  const [testResult, setTestResult] = useState<{ id: number; ok: boolean } | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [confirmDel, setConfirmDel] = useState<number | null>(null);

  const [form, setForm] = useState<{
    name: string; channel_type: ChannelType; url: string; email_address: string; enabled: boolean;
  }>({ name: "", channel_type: "webhook", url: "", email_address: "", enabled: true });

  async function refresh() {
    setLoading(true);
    try {
      setChannels(await listChannels());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load channels");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { refresh(); }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await createChannel({
        name: form.name,
        channel_type: form.channel_type,
        url: form.channel_type === "webhook" ? form.url : undefined,
        email_address: form.channel_type === "email" ? form.email_address : undefined,
        enabled: form.enabled,
      });
      setForm({ name: "", channel_type: "webhook", url: "", email_address: "", enabled: true });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create channel");
    } finally {
      setCreating(false);
    }
  }

  async function handleToggle(ch: NotificationChannel) {
    try {
      await updateChannel(ch.id, { enabled: !ch.enabled });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update channel");
    }
  }

  async function handleTest(ch: NotificationChannel) {
    setTestingId(ch.id);
    setTestResult(null);
    try {
      const { ok } = await testChannel(ch.id);
      setTestResult({ id: ch.id, ok });
    } catch {
      setTestResult({ id: ch.id, ok: false });
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete(ch: NotificationChannel) {
    setDeletingId(ch.id);
    try {
      await deleteChannel(ch.id);
      setConfirmDel(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete channel");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="notif-page">
      {error && <div className="err-banner">{error}</div>}

      <div className="summary-row">
        <div className="summ-card sc-blue">
          <div className="summ-label">Channels</div>
          <div className="summ-value sv-blue">{channels.length}</div>
          <div className="summ-sub">webhook endpoints</div>
        </div>
        <div className="summ-card sc-green">
          <div className="summ-label">Enabled</div>
          <div className="summ-value sv-green">{channels.filter((c) => c.enabled).length}</div>
          <div className="summ-sub">active channels</div>
        </div>
      </div>

      <div className="section-header">
        <span className="section-title">Add Notification Channel</span>
      </div>

      <div className="notif-form-card">
        <form className="notif-form" onSubmit={handleCreate}>
          <div className="notif-field">
            <label className="notif-label">Name</label>
            <input
              className="notif-input"
              placeholder="Slack alerts"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
              disabled={creating}
            />
          </div>
          <div className="notif-field">
            <label className="notif-label">Type</label>
            <select
              className="notif-input"
              value={form.channel_type}
              onChange={(e) => setForm((f) => ({ ...f, channel_type: e.target.value as ChannelType }))}
              disabled={creating}
            >
              <option value="webhook">Webhook</option>
              <option value="email">Email</option>
            </select>
          </div>
          {form.channel_type === "webhook" ? (
            <div className="notif-field notif-field-wide">
              <label className="notif-label">Webhook URL</label>
              <input
                className="notif-input notif-mono"
                placeholder="https://hooks.slack.com/services/…"
                value={form.url}
                onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))}
                required
                disabled={creating}
              />
            </div>
          ) : (
            <div className="notif-field notif-field-wide">
              <label className="notif-label">Destination email</label>
              <input
                className="notif-input notif-mono"
                type="email"
                placeholder="you@example.com"
                value={form.email_address}
                onChange={(e) => setForm((f) => ({ ...f, email_address: e.target.value }))}
                required
                disabled={creating}
              />
            </div>
          )}
          <div className="notif-field notif-field-check">
            <label className="notif-label">Enabled</label>
            <input
              type="checkbox"
              className="notif-check"
              checked={form.enabled}
              onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
              disabled={creating}
            />
          </div>
          <div className="notif-field notif-field-submit">
            <button className="notif-btn-primary" type="submit" disabled={creating}>
              {creating ? "Adding…" : "Add"}
            </button>
          </div>
        </form>
      </div>

      <div className="section-header" style={{ marginTop: "1.75rem" }}>
        <span className="section-title">Channels</span>
      </div>

      {loading ? (
        <div className="loading"><div className="spinner" /><span>Loading…</span></div>
      ) : channels.length === 0 ? (
        <div className="notif-empty">No notification channels configured.</div>
      ) : (
        <div className="notif-table-wrap">
          <table className="notif-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Destination</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => (
                <tr key={ch.id} className={ch.enabled ? "" : "notif-row-disabled"}>
                  <td className="notif-name">{ch.name}</td>
                  <td>{ch.channel_type === "email" ? "Email" : "Webhook"}</td>
                  <td className="notif-mono notif-url">
                    {ch.channel_type === "email" ? ch.email_address : ch.url}
                  </td>
                  <td>
                    <span className={`notif-status-badge ${ch.enabled ? "nsb-active" : "nsb-disabled"}`}>
                      {ch.enabled ? "Enabled" : "Disabled"}
                    </span>
                  </td>
                  <td className="notif-date">
                    {new Date(ch.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className="notif-actions">
                      <button
                        className={`notif-btn-toggle${ch.enabled ? "" : " notif-btn-enable"}`}
                        onClick={() => handleToggle(ch)}
                      >
                        {ch.enabled ? "Disable" : "Enable"}
                      </button>
                      <button
                        className="notif-btn-test"
                        onClick={() => handleTest(ch)}
                        disabled={testingId === ch.id}
                      >
                        {testingId === ch.id ? "Testing…" : "Test"}
                      </button>
                      {testResult?.id === ch.id && (
                        <span className={`notif-test-result ${testResult.ok ? "ntr-ok" : "ntr-fail"}`}>
                          {testResult.ok ? "✓ OK" : "✗ Failed"}
                        </span>
                      )}
                      {confirmDel === ch.id ? (
                        <div className="notif-confirm">
                          <button
                            className="notif-btn-del-confirm"
                            onClick={() => handleDelete(ch)}
                            disabled={deletingId === ch.id}
                          >
                            {deletingId === ch.id ? "…" : "Delete"}
                          </button>
                          <button className="notif-btn-cancel" onClick={() => setConfirmDel(null)}>Cancel</button>
                        </div>
                      ) : (
                        <button className="notif-btn-del" onClick={() => setConfirmDel(ch.id)}>Delete</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="notif-help">
        <div className="notif-help-title">Webhook payload format</div>
        <pre className="notif-help-pre">{`{
  "event": "alert_firing",
  "alert": "HighCpuUsage",
  "severity": "warning",
  "summary": "CPU above 80%",
  "node": "pi-node2"
}`}</pre>
        <div className="notif-help-sub">
          Fired for cluster alerts (Prometheus/AlertManager) and security events
          (e.g. <code>event: "new_login_ip"</code> when an account logs in from an
          address it hasn't used before). Webhooks get this JSON payload; email
          channels get an equivalent plain-text message instead. Webhook URLs are
          compatible with Slack, Discord, and custom endpoints.
        </div>
      </div>
    </div>
  );
}
