import { useEffect, useMemo, useState, type FormEvent } from "react";
import { CalendarX, CheckCircle2, Plus, RefreshCw, ShieldAlert, ToggleLeft, ToggleRight } from "lucide-react";
import { createBlackoutDate, getBlackoutDates, updateBlackoutDate } from "../api";
import { useAuth } from "../auth";
import type { DeliveryBlackoutDate } from "../types";

function todayLocal() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
}

function formatDate(value: string) {
  return new Date(value + "T00:00:00").toLocaleDateString("en-IN", {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  });
}

export default function BlackoutDates() {
  const { token } = useAuth();
  const [items, setItems] = useState<DeliveryBlackoutDate[]>([]);
  const [form, setForm] = useState({ delivery_date: "", reason: "" });
  const [includeInactive, setIncludeInactive] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setItems(await getBlackoutDates(token, "", "", true));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load blackout dates.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  const visibleItems = useMemo(
    () => includeInactive ? items : items.filter((item) => item.is_active),
    [items, includeInactive],
  );
  const activeCount = items.filter((item) => item.is_active).length;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await createBlackoutDate(token, {
        delivery_date: form.delivery_date,
        reason: form.reason.trim(),
      });
      setItems((current) => [...current, created].sort((a, b) => a.delivery_date.localeCompare(b.delivery_date)));
      setForm({ delivery_date: "", reason: "" });
      setNotice(`${formatDate(created.delivery_date)} is now closed for new delivery slots and bookings.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create blackout date.");
    } finally {
      setBusy(false);
    }
  }

  async function toggle(item: DeliveryBlackoutDate) {
    if (!token) return;
    setUpdatingId(item.id);
    setError("");
    setNotice("");
    try {
      const updated = await updateBlackoutDate(token, item.id, { is_active: !item.is_active });
      setItems((current) => current.map((entry) => entry.id === item.id ? updated : entry));
      setNotice(updated.is_active
        ? `${formatDate(updated.delivery_date)} is closed for new bookings.`
        : `${formatDate(updated.delivery_date)} is open for slot creation and booking again.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update blackout date.");
    } finally {
      setUpdatingId(null);
    }
  }

  return <div className="blackout-workspace">
    <div className="page-heading">
      <div><div className="eyebrow">OPERATIONS / CAPACITY PLANNING</div><h1>Blackout dates</h1><p>Close delivery operations on holidays, planned shutdowns or dates with no available capacity.</p></div>
      <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button>
    </div>
    {error && <div className="alert-error">{error}</div>}
    {notice && <div className="alert-success">{notice}</div>}

    <div className="stats-grid blackout-stats">
      <div className="stat-card"><div className="stat-icon blue"><CalendarX size={18}/></div><div className="stat-label">Dates configured</div><div className="stat-value">{items.length}</div><div className="stat-note">Operations calendar entries</div></div>
      <div className="stat-card"><div className="stat-icon amber"><ShieldAlert size={18}/></div><div className="stat-label">Active closures</div><div className="stat-value">{activeCount}</div><div className="stat-note">Blocking new slots and bookings</div></div>
      <div className="stat-card"><div className="stat-icon green"><CheckCircle2 size={18}/></div><div className="stat-label">Open entries</div><div className="stat-value">{items.length - activeCount}</div><div className="stat-note">Paused or re-opened dates</div></div>
    </div>

    <section className="panel customer-form-panel blackout-create">
      <div className="panel-heading"><div><h2><Plus size={17}/> Schedule a closure</h2><p>Choose a date and record why delivery operations will be closed.</p></div></div>
      <form className="customer-form" onSubmit={submit}>
        <label>Delivery date<input type="date" min={todayLocal()} required value={form.delivery_date} onChange={(event) => setForm({ ...form, delivery_date: event.target.value })}/></label>
        <label className="span-two">Reason<input required minLength={3} maxLength={255} value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} placeholder="e.g. Public holiday, planned maintenance, severe weather"/></label>
        <div className="customer-form-actions"><span>Existing confirmed bookings must be resolved before a date can be closed.</span><button className="primary-button" disabled={busy}><CalendarX size={15}/>{busy ? "Saving closure…" : "Close delivery date"}</button></div>
      </form>
    </section>

    <div className="section-title-row blackout-list-heading"><h2>Operations calendar</h2><label className="blackout-filter"><input type="checkbox" checked={includeInactive} onChange={(event) => setIncludeInactive(event.target.checked)}/> Include inactive entries</label></div>
    {loading ? <div className="panel table-loading">Loading blackout dates…</div> : visibleItems.length ? (
      <div className="blackout-list">
        {visibleItems.map((item) => <article className="panel blackout-card" key={item.id}>
          <div className="blackout-date-icon"><CalendarX size={19}/></div>
          <div className="blackout-date-copy"><strong>{formatDate(item.delivery_date)}</strong><span>{item.reason}</span><small>Calendar entry #{item.id}</small></div>
          <span className={`blackout-status ${item.is_active ? "active" : "inactive"}`}><span/>{item.is_active ? "Closed" : "Inactive"}</span>
          <button type="button" className="secondary-button blackout-toggle" disabled={updatingId === item.id} onClick={() => void toggle(item)}>{item.is_active ? <><ToggleRight size={15}/> Reopen date</> : <><ToggleLeft size={15}/> Reactivate closure</>}</button>
        </article>)}
      </div>
    ) : <div className="panel blackout-empty"><CalendarX size={23}/><strong>No blackout dates configured</strong><span>Delivery slots can be created on any future date unless operations adds a closure.</span></div>}
    <p className="page-footnote">A blackout blocks new slot creation and booking. TimeDrop will not cancel or modify confirmed bookings; a closure cannot be activated while confirmed bookings remain for that date.</p>
  </div>;
}
