import { useEffect, useRef, useState } from "react";
import { getWorkloadLogs } from "../api/workloads";
import type { WorkloadLogs } from "../types/workload";
import "./LogsModal.css";

interface Props {
  workloadName: string;
  onClose: () => void;
}

export default function LogsModal({ workloadName, onClose }: Props) {
  const [data, setData] = useState<WorkloadLogs | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const preRef = useRef<HTMLPreElement>(null);

  const fetchLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getWorkloadLogs(workloadName);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [workloadName]);

  useEffect(() => {
    if (preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight;
    }
  }, [data]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="lm-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="lm-modal">
        <div className="lm-header">
          <div className="lm-title">
            <span className="lm-name">{workloadName}</span>
            {data && <span className="lm-pod">pod: {data.pod_name}</span>}
          </div>
          <div className="lm-actions">
            <button className="lm-btn-refresh" onClick={fetchLogs} disabled={loading}>
              {loading ? "…" : "Refresh"}
            </button>
            <button className="lm-btn-close" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="lm-body">
          {error ? (
            <div className="lm-error">{error}</div>
          ) : loading && !data ? (
            <div className="lm-loading">Fetching logs…</div>
          ) : (
            <pre className="lm-pre" ref={preRef}>
              {data?.logs || "(no output)"}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
