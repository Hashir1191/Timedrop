import { useEffect, useState } from "react";
import { FileClock, Filter, History, RefreshCw, UserRound } from "lucide-react";
import { getOperationsAuditLog } from "../api";
import { useAuth } from "../auth";
import type { OperationsAuditEvent } from "../types";

function formatTimestamp(value: string) {
  return new Date(value).toLocaleString("en-IN", {
    day: "numeric", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function actionLabel(action: string) {
  return action.replace(/\./g, " · ").replace(/_/g, " ");
}

export default function AuditLog() {
  const { token } = useAuth();
  const [events, setEvents] = useState<OperationsAuditEvent[]>([]);
  const [entityType, setEntityType] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const result = await getOperationsAuditLog(token, {
        entity_type: entityType || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        limit: 100,
      });
      setEvents(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load the operations audit log.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token, entityType, fromDate, toDate]);

  return <div className="audit-log-workspace">
    <div className="page-heading">
      <div><div className="eyebrow">OPERATIONS / GOVERNANCE</div><h1>Audit log</h1><p>Review important changes made across delivery operations and account management.</p></div>
      <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button>
    </div>

    <div className="audit-log-summary">
      <div className="audit-log-summary-icon"><History size={20}/></div>
      <div><strong>{events.length} recent event{events.length===1?"":"s"}</strong><span>Showing up to the latest 100 matching changes. Field values and personal contact details are not stored in this log.</span></div>
    </div>

    <section className="panel audit-filters">
      <div className="audit-filter-title"><Filter size={16}/><strong>Filter activity</strong></div>
      <label>Area<select value={entityType} onChange={event=>setEntityType(event.target.value)}><option value="">All areas</option><option value="delivery_partner">Delivery partners</option><option value="service_area">Service areas</option><option value="blackout_date">Blackout dates</option><option value="delivery_slot">Delivery slots</option></select></label>
      <label>From<input type="date" value={fromDate} onChange={event=>setFromDate(event.target.value)}/></label>
      <label>To<input type="date" value={toDate} onChange={event=>setToDate(event.target.value)}/></label>
      <button type="button" className="secondary-button audit-clear" onClick={()=>{setEntityType("");setFromDate("");setToDate("");}}>Clear filters</button>
    </section>

    {error && <div className="alert-error">{error}</div>}
    {loading ? <div className="panel table-loading">Loading audit activity…</div> : events.length ? (
      <div className="audit-event-list">
        {events.map(event=><article className="panel audit-event" key={event.id}>
          <div className="audit-event-icon"><FileClock size={18}/></div>
          <div className="audit-event-main">
            <div className="audit-event-top"><span className="audit-action">{actionLabel(event.action)}</span><time>{formatTimestamp(event.created_at)}</time></div>
            <strong>{event.summary}</strong>
            <div className="audit-event-meta"><span><UserRound size={12}/>{event.actor_name}</span><span>{event.entity_type.replace(/_/g," ")} #{event.entity_id}</span></div>
            {event.changed_fields.length>0&&<div className="audit-field-tags">{event.changed_fields.map(field=><span key={field}>{field.replace(/_/g," ")}</span>)}</div>}
          </div>
        </article>)}
      </div>
    ) : <div className="panel audit-empty"><History size={24}/><strong>No matching activity</strong><span>Changes to partners, service areas, blackout dates and delivery slots will appear here.</span></div>}
    <p className="page-footnote">Audit events are append-only. The log records who made a change, what record was affected, and which fields changed; it deliberately excludes submitted values such as phone numbers, email addresses and passwords.</p>
  </div>;
}
