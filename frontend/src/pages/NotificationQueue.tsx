import { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  BellRing,
  CheckCircle2,
  Clock3,
  Mail,
  MessageSquareText,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import {
  getNotificationDeliveries,
  retryNotificationDelivery,
  type NotificationDeliveryOperationsItem,
} from "../api";
import { useAuth } from "../auth";

type DeliveryStatus = NotificationDeliveryOperationsItem["status"];
type DeliveryChannel = NotificationDeliveryOperationsItem["channel"];

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(status: DeliveryStatus) {
  return status.replace(/_/g, " ");
}

export default function NotificationQueue() {
  const { token } = useAuth();
  const [items, setItems] = useState<NotificationDeliveryOperationsItem[]>([]);
  const [status, setStatus] = useState<DeliveryStatus | "">("");
  const [channel, setChannel] = useState<DeliveryChannel | "">("");
  const [loading, setLoading] = useState(true);
  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const result = await getNotificationDeliveries(token, {
        status: status || undefined,
        channel: channel || undefined,
        limit: 100,
      });
      setItems(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load notification deliveries.");
    } finally {
      setLoading(false);
    }
  }, [token, status, channel]);

  useEffect(() => {
    void load();
  }, [load]);

  async function retry(item: NotificationDeliveryOperationsItem) {
    if (!token || item.status !== "failed") return;
    setRetryingId(item.id);
    setError("");
    setSuccess("");
    try {
      const updated = await retryNotificationDelivery(token, item.id);
      setItems(current => current.map(entry => entry.id === item.id ? updated : entry));
      setSuccess(`Delivery #${item.id} has been requeued. The worker will re-check account eligibility before dispatch.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to requeue this delivery.");
    } finally {
      setRetryingId(null);
    }
  }

  const failedCount = items.filter(item => item.status === "failed").length;
  const processingCount = items.filter(item => item.status === "processing").length;
  const pendingCount = items.filter(item => item.status === "pending").length;

  return (
    <div className="notification-queue-workspace">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OPERATIONS / COMMUNICATIONS</div>
          <h1>Notification queue</h1>
          <p>Review external email and SMS delivery attempts, investigate failures, and safely requeue eligible jobs.</p>
        </div>
        <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}>
          <RefreshCw size={14} className={loading ? "notification-spin" : ""} /> Refresh
        </button>
      </div>

      <section className="notification-queue-summary" aria-label="Notification queue summary">
        <article className="notification-queue-stat">
          <span className="notification-queue-stat-icon blue"><BellRing size={17} /></span>
          <div><small>Loaded records</small><strong>{items.length}</strong><span>Latest 100 matching jobs</span></div>
        </article>
        <article className="notification-queue-stat">
          <span className="notification-queue-stat-icon red"><AlertCircle size={17} /></span>
          <div><small>Failed</small><strong>{failedCount}</strong><span>Need review</span></div>
        </article>
        <article className="notification-queue-stat">
          <span className="notification-queue-stat-icon violet"><Clock3 size={17} /></span>
          <div><small>Processing</small><strong>{processingCount}</strong><span>Claimed by worker</span></div>
        </article>
        <article className="notification-queue-stat">
          <span className="notification-queue-stat-icon green"><CheckCircle2 size={17} /></span>
          <div><small>Pending</small><strong>{pendingCount}</strong><span>Waiting for retry window</span></div>
        </article>
      </section>

      <section className="panel notification-queue-filters" aria-label="Filter notification deliveries">
        <div className="notification-queue-filter-heading">
          <div><strong>Delivery activity</strong><span>Recipient contact details are masked for privacy.</span></div>
          <span className="notification-queue-count">{items.length} results</span>
        </div>
        <label>
          Status
          <select value={status} onChange={event => setStatus(event.target.value as DeliveryStatus | "")}>
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
            <option value="sent">Sent</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </label>
        <label>
          Channel
          <select value={channel} onChange={event => setChannel(event.target.value as DeliveryChannel | "")}>
            <option value="">All channels</option>
            <option value="email">Email</option>
            <option value="sms">SMS</option>
          </select>
        </label>
        <button type="button" className="secondary-button notification-clear" onClick={() => { setStatus(""); setChannel(""); }}>
          Clear filters
        </button>
      </section>

      {error && <div className="alert-error" role="alert">{error}</div>}
      {success && <div className="notification-queue-success" role="status"><CheckCircle2 size={15} />{success}</div>}

      {loading ? (
        <div className="panel notification-queue-state"><div className="loader" /><span>Loading notification activity…</span></div>
      ) : items.length ? (
        <div className="notification-delivery-list">
          {items.map(item => (
            <article className={`panel notification-delivery-card status-${item.status}`} key={item.id}>
              <div className={`notification-delivery-channel ${item.channel}`}>
                {item.channel === "email" ? <Mail size={17} /> : <MessageSquareText size={17} />}
              </div>
              <div className="notification-delivery-content">
                <div className="notification-delivery-heading">
                  <div><strong>{item.subject}</strong><span>Delivery #{item.id} · {item.masked_recipient}</span></div>
                  <span className={`notification-status-pill ${item.status}`}>{statusLabel(item.status)}</span>
                </div>
                <div className="notification-delivery-meta">
                  <span>{item.channel.toUpperCase()}</span>
                  <span>{item.attempts} attempt{item.attempts === 1 ? "" : "s"}</span>
                  <span>Created {formatTimestamp(item.created_at)}</span>
                  {item.status === "pending" && <span>Next attempt {formatTimestamp(item.next_attempt_at)}</span>}
                  {item.sent_at && <span>Sent {formatTimestamp(item.sent_at)}</span>}
                </div>
                {item.last_error && <div className="notification-delivery-error"><AlertCircle size={13} /><span>{item.last_error}</span></div>}
              </div>
              {item.status === "failed" && (
                <button
                  type="button"
                  className="notification-retry-button"
                  onClick={() => void retry(item)}
                  disabled={retryingId !== null}
                >
                  <RotateCcw size={14} /> {retryingId === item.id ? "Requeuing…" : "Retry"}
                </button>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="panel notification-queue-empty">
          <div><CheckCircle2 size={23} /></div>
          <strong>No notification deliveries found</strong>
          <span>Try another status or channel filter. New external delivery jobs will appear here when a provider is configured.</span>
        </div>
      )}

      <p className="notification-queue-footnote">
        Requeuing is available only for failed jobs. SMS verification and consent are checked again by the worker immediately before dispatch.
        Provider delivery is not guaranteed by an accepted API request; consult provider logs for final handset or inbox delivery status.
      </p>
    </div>
  );
}
