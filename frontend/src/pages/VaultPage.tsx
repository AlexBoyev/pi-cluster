import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import "./VaultPage.css";

interface VaultData {
  postgresql: { host: string; port: number; database: string; username: string; password: string };
  redis: { url: string };
  ssh: { username: string; password: string };
  grafana: { url: string; username: string; password: string };
  jenkins: { url: string; username: string; password: string };
  argocd: { url: string; username: string; password: string };
  prometheus: { url: string; note: string };
  app_admin: { username: string; password: string; note: string };
  jwt: { secret_key: string };
}

interface CredRow {
  label: string;
  value: string;
  secret?: boolean;
}

interface CredGroup {
  title: string;
  rows: CredRow[];
}

function buildGroups(v: VaultData): CredGroup[] {
  return [
    {
      title: "PostgreSQL",
      rows: [
        { label: "Host", value: v.postgresql.host },
        { label: "Port", value: String(v.postgresql.port) },
        { label: "Database", value: v.postgresql.database },
        { label: "Username", value: v.postgresql.username },
        { label: "Password", value: v.postgresql.password, secret: true },
      ],
    },
    {
      title: "Redis",
      rows: [{ label: "URL", value: v.redis.url, secret: true }],
    },
    {
      title: "SSH",
      rows: [
        { label: "Username", value: v.ssh.username },
        { label: "Password", value: v.ssh.password, secret: true },
      ],
    },
    {
      title: "Grafana",
      rows: [
        { label: "URL", value: v.grafana.url },
        { label: "Username", value: v.grafana.username },
        { label: "Password", value: v.grafana.password, secret: true },
      ],
    },
    {
      title: "Jenkins",
      rows: [
        { label: "URL", value: v.jenkins.url },
        { label: "Username", value: v.jenkins.username },
        { label: "Password", value: v.jenkins.password, secret: true },
      ],
    },
    {
      title: "ArgoCD",
      rows: [
        { label: "URL", value: v.argocd.url },
        { label: "Username", value: v.argocd.username },
        { label: "Password", value: v.argocd.password, secret: true },
      ],
    },
    {
      title: "Prometheus",
      rows: [
        { label: "URL", value: v.prometheus.url },
        { label: "Auth", value: v.prometheus.note },
      ],
    },
    {
      title: "App Admin",
      rows: [
        { label: "Username", value: v.app_admin.username },
        { label: "Password", value: v.app_admin.password, secret: true },
        { label: "Note", value: v.app_admin.note },
      ],
    },
    {
      title: "JWT",
      rows: [{ label: "Secret Key", value: v.jwt.secret_key, secret: true }],
    },
  ];
}

function CredentialRow({ label, value, secret }: CredRow) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <tr className="vault-row">
      <td className="vault-label">{label}</td>
      <td className="vault-value">
        <span className="vault-val-text">
          {secret && !revealed ? "•".repeat(Math.min(value.length, 24)) : value}
        </span>
      </td>
      <td className="vault-actions">
        {secret && (
          <button className="vault-btn" onClick={() => setRevealed((r) => !r)} title={revealed ? "Hide" : "Reveal"}>
            {revealed ? "hide" : "show"}
          </button>
        )}
        <button className="vault-btn vault-btn-copy" onClick={copy}>
          {copied ? "✓" : "copy"}
        </button>
      </td>
    </tr>
  );
}

export default function VaultPage() {
  const [data, setData] = useState<VaultData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<VaultData>("/vault")
      .then((d) => { setData(d); setError(null); })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="vault-loading"><div className="spinner" /> Loading credentials…</div>;
  if (error) return <div className="vault-error">⚠ {error} — vault is only accessible on the LAN.</div>;
  if (!data) return null;

  const groups = buildGroups(data);

  return (
    <div className="vault-page">
      <div className="vault-banner">
        <span className="vault-banner-icon">⚿</span>
        <div>
          <div className="vault-banner-title">Key Vault</div>
          <div className="vault-banner-sub">Admin-only · LAN access only · Handle with care</div>
        </div>
      </div>

      <div className="vault-grid">
        {groups.map((g) => (
          <div key={g.title} className="vault-card">
            <div className="vault-card-title">{g.title}</div>
            <table className="vault-table">
              <tbody>
                {g.rows.map((r) => (
                  <CredentialRow key={r.label} {...r} />
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </div>
  );
}
