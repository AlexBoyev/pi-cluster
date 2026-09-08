import { useState } from "react";
import "./StressTestModal.css";
import { runStressTest } from "../api/nodes";
import type { NodeStressResult, StressTestReport, StressVerdict } from "../types/stress_test";

interface Props {
  onClose: () => void;
}

const DURATION_SECONDS = 30;

const VERDICT_LABEL: Record<StressVerdict, string> = {
  clean: "Clean",
  undervoltage_under_load: "Undervoltage",
  throttled_under_load: "Throttled",
  crashed_or_unreachable: "Lost contact",
  unknown: "Unknown",
};

function VerdictBadge({ verdict }: { verdict: StressVerdict }) {
  return <span className={`stm-badge stm-badge-${verdict}`}>{VERDICT_LABEL[verdict]}</span>;
}

function NodeResultCard({ n }: { n: NodeStressResult }) {
  return (
    <div className={`stm-node-card stm-node-${n.verdict}`}>
      <div className="stm-node-head">
        <span className="stm-node-name">{n.node_name}</span>
        <VerdictBadge verdict={n.verdict} />
      </div>
      {!n.reachable ? (
        <div className="stm-node-error">{n.error ?? "Node stopped responding during the test."}</div>
      ) : (
        <div className="stm-node-stats">
          <div className="stm-stat">
            <span className="stm-stat-label">Peak temp</span>
            <span className="stm-stat-value">{n.max_temp_celsius != null ? `${n.max_temp_celsius.toFixed(1)}°C` : "—"}</span>
          </div>
          <div className="stm-stat">
            <span className="stm-stat-label">Min voltage</span>
            <span className="stm-stat-value">{n.min_volts != null ? `${n.min_volts.toFixed(3)}V` : "—"}</span>
          </div>
          <div className="stm-stat">
            <span className="stm-stat-label">Baseline → final</span>
            <span className="stm-stat-value stm-mono">
              {n.baseline?.throttled_hex ?? "—"} → {n.final?.throttled_hex ?? "—"}
            </span>
          </div>
          <div className="stm-stat">
            <span className="stm-stat-label">Cores loaded</span>
            <span className="stm-stat-value">{n.ncores ?? "—"}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function StressTestModal({ onClose }: Props) {
  const [phase, setPhase] = useState<"confirm" | "running" | "done" | "error">("confirm");
  const [report, setReport] = useState<StressTestReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const start = async () => {
    setPhase("running");
    try {
      const r = await runStressTest(DURATION_SECONDS);
      setReport(r);
      setPhase("done");
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Stress test request failed");
      setPhase("error");
    }
  };

  return (
    <div className="stm-overlay" onClick={(e) => { if (e.target === e.currentTarget && phase !== "running") onClose(); }}>
      <div className="stm-box">
        {phase === "confirm" && (
          <>
            <div className="stm-title">Run cluster stress test?</div>
            <div className="stm-message">
              Loads all CPU cores on every node for {DURATION_SECONDS} seconds and samples <code>vcgencmd</code> (voltage,
              throttling, temperature) throughout. This does not reboot anything on purpose — but on hardware that's already
              running marginal power, sustained load can trigger a real undervoltage brownout and a node can crash and
              reboot on its own. That's a genuine result the report will show, not something this can guarantee against.
            </div>
            <div className="stm-actions">
              <button className="stm-btn-cancel" onClick={onClose}>Cancel</button>
              <button className="stm-btn-confirm" onClick={start}>Run {DURATION_SECONDS}s Test</button>
            </div>
          </>
        )}

        {phase === "running" && (
          <div className="stm-running">
            <div className="stm-spinner" />
            <div className="stm-title">Stress test running…</div>
            <div className="stm-message">Loading every node for {DURATION_SECONDS}s and sampling power/thermal state. Please wait.</div>
          </div>
        )}

        {phase === "error" && (
          <>
            <div className="stm-title">Stress test failed</div>
            <div className="stm-message">{errorMsg}</div>
            <div className="stm-actions">
              <button className="stm-btn-cancel" onClick={onClose}>Close</button>
            </div>
          </>
        )}

        {phase === "done" && report && (
          <>
            <div className="stm-title">Stress test results</div>
            <div className={`stm-summary ${report.any_undervoltage || report.any_node_unreachable ? "stm-summary-bad" : "stm-summary-ok"}`}>
              {report.summary}
            </div>
            <div className="stm-node-grid">
              {report.nodes.map((n) => <NodeResultCard key={n.node_name} n={n} />)}
            </div>
            <div className="stm-actions">
              <button className="stm-btn-confirm" onClick={onClose}>Close</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
