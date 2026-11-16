import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  Mail,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { getOperationsSystemHealth, type OperationsSystemHealth } from "../api";
import { useAuth } from "../auth";

function formatDate(value: string | null) {
  if (!value) return "No heartbeat received yet";
  return new Date(value).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatAge(seconds: number | null) {
  if (seconds === null) return "Not available";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder ? `${minutes}m ${remainder}s ago` : `${minutes}m ago`;
}

export default function SystemHealth() {
  const { token } = useAuth();
  const [health, setHealth] = useState<OperationsSystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setHealth(await getOperationsSystemHealth(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load system health.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const workerHealthy = health?.notification_worker_status === "healthy";
  const queue = health?.notification_queue || {};

  return (
    <div className="system-health-workspace">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OPERATIONS / PLATFORM</div>
          <h1>System health</h1>
          <p>Check database connectivity, notification worker activity, and the external delivery queue.</p>
        </div>
        <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={14} className={loading ? "system-health-spin" : ""} /> Refresh
        </button>
      </div>

      {error && <div className="alert-error" role="alert">{error}</div>}

      {loading && !health ? (
        <div className="panel system-health-loading"><div className="loader" /><span>Checking platform health…</span></div>
      ) : health ? (
        <>
          {health.notification_worker_status !== "healthy" && (
            <div className="system-health-warning" role="status">
              <AlertTriangle size={17} />
              <div>
                <strong>{health.notification_worker_status === "stale" ? "Notification worker heartbeat is stale" : "Notification worker has not reported in"}</strong>
                <span>Queued external notifications may not be processed until the worker is running and connected to the database.</span>
              </div>
            </div>
          )}

          <section className="system-health-service-grid" aria-label="Core service status">
            <article className="panel system-health-service-card">
              <div className="system-health-service-icon database"><Database size={19} /></div>
              <div className="system-health-service-copy">
                <span>DATABASE</span>
                <strong>PostgreSQL / SQLAlchemy</strong>
                <small>API database query completed successfully</small>
              </div>
              <span className="system-health-status healthy"><CheckCircle2 size={13} /> Connected</span>
            </article>
            <article className="panel system-health-service-card">
              <div className="system-health-service-icon worker"><Activity size={19} /></div>
              <div className="system-health-service-copy">
                <span>BACKGROUND WORKER</span>
                <strong>Notification worker</strong>
                <small>Last heartbeat: {formatDate(health.worker_last_seen_at)}</small>
              </div>
              <span className={`system-health-status ${health.notification_worker_status}`}>
                {workerHealthy ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
                {health.notification_worker_status === "healthy" ? "Healthy" : health.notification_worker_status === "stale" ? "Stale" : "Not seen"}
              </span>
            </article>
          </section>

          <section className="system-health-detail-grid">
            <article className="panel system-health-detail-card">
              <div className="system-health-section-heading"><Clock3 size={16} /><strong>Worker heartbeat</strong></div>
              <div className="system-health-heartbeat-value">{formatAge(health.worker_age_seconds)}</div>
              <p>Heartbeat is considered stale after {health.worker_stale_after_seconds} seconds without an update.</p>
              <div className="system-health-detail-line"><span>Last update</span><strong>{formatDate(health.worker_last_seen_at)}</strong></div>
              <div className="system-health-detail-line"><span>Health checked</span><strong>{formatDate(health.checked_at)}</strong></div>
            </article>
            <article className="panel system-health-detail-card">
              <div className="system-health-section-heading"><Mail size={16} /><strong>Notification delivery queue</strong></div>
              <div className="system-health-queue-grid">
                {(["pending", "processing", "sent", "failed", "cancelled"] as const).map(status => (
                  <div className={`system-health-queue-item ${status}`} key={status}>
                    <strong>{queue[status] ?? 0}</strong>
                    <span>{status}</span>
                  </div>
                ))}
              </div>
              <p>Counts include all persisted outbox records, not only the latest page of queue activity.</p>
            </article>
          </section>
        </>
      ) : (
        <div className="panel system-health-loading">
          <AlertTriangle size={20} />
          <strong>System health is unavailable</strong>
          <span>Refresh the page or inspect API connectivity.</span>
        </div>
      )}
      <p className="system-health-footnote">This view reports API/database connectivity and the worker's latest database heartbeat. It does not verify external provider delivery, email inbox placement, or SMS handset receipt.</p>
    </div>
  );
}
