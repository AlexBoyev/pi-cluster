import { useEffect, useState } from "react";
import { getWorkloadEvents } from "../api/workloads";
import type { WorkloadEvent } from "../types/workload";
import "./EventsModal.css";

interface Props {
  workloadName: string;
  onClose: () => void;
}

function age(ts: string | null): string {
  if (!ts) return "—";
  const secs = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h`;
  return `${Math.floor(secs / 86400)}d`;
}

export default function EventsModal({ workloadName, onClose }: Props) {
  const [events, setEvents] = useState<WorkloadEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      setEvents(await getWorkloadEvents(workloadName));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchEvents(); }, [workloadName]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="em-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="em-modal">
        <div className="em-header">
          <div className="em-title">
            <span className="em-name">{workloadName}</span>
            <span className="em-sub">K8s events</span>
          </div>
          <div className="em-actions">
            <button className="em-btn-refresh" onClick={fetchEvents} disabled={loading}>
              {loading ? "…" : "Refresh"}
            </button>
            <button className="em-btn-close" onClick={onClose}>✕</button>
          </div>
        </div>

        <div className="em-body">
          {error ? (
            <div className="em-msg em-err">{error}</div>
          ) : loading ? (
            <div className="em-msg">Fetching events…</div>
          ) : events.length === 0 ? (
            <div className="em-msg em-empty">No events found for this workload.</div>
          ) : (
            <table className="em-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Reason</th>
                  <th>Object</th>
                  <th>Count</th>
                  <th>Age</th>
                  <th>Message</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e, i) => (
                  <tr key={i} className={e.type === "Warning" ? "em-warning" : ""}>
                    <td>
                      <span className={`em-type-badge em-type-${e.type.toLowerCase()}`}>
                        {e.type}
                      </span>
                    </td>
                    <td className="em-reason">{e.reason}</td>
                    <td className="em-obj">{e.object_name}</td>
                    <td className="em-count">{e.count}</td>
                    <td className="em-age">{age(e.last_time)}</td>
                    <td className="em-message">{e.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
