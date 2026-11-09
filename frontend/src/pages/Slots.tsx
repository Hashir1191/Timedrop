import { FormEvent, useEffect, useState } from "react";
import { CalendarDays, Plus, RefreshCw } from "lucide-react";
import { createSlot, getSlots } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import type { DeliverySlot } from "../types";

function todayLocal() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
export default function Slots() {
  const { token } = useAuth();
  const [date, setDate] = useState(todayLocal());
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("11:00");
  const [capacity, setCapacity] = useState("10");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() { if (!token || !date) return; try { setError(""); setSlots(await getSlots(token, date)); } catch (err) { setError(err instanceof Error ? err.message : "Unable to load slots."); } }
  useEffect(() => { void load(); }, [token, date]);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!token) return; setBusy(true); setError(""); setSuccess("");
    try { await createSlot(token, { delivery_date: date, start_time: start, end_time: end, capacity: Number(capacity) }); setSuccess("Delivery slot created."); setShowForm(false); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to create slot."); }
    finally { setBusy(false); }
  }
  const booked = slots.reduce((n, s) => n + s.booked_count, 0);
  const total = slots.reduce((n, s) => n + s.capacity, 0);
  return <><div className="page-heading"><div><div className="eyebrow">CAPACITY PLANNING</div><h1>Delivery slots</h1><p>Create delivery windows and keep an eye on available capacity.</p></div><button className="primary-button" onClick={() => { setShowForm((v) => !v); setSuccess(""); }}><Plus size={17} /> Create slot</button></div>
    {error && <div className="alert-error">{error}</div>}{success && <div className="alert-success">{success}</div>}
    <div className="slot-summary"><div className="summary-icon"><CalendarDays size={20} /></div><div><span>Selected date</span><strong>{new Date(date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</strong></div><div className="summary-metrics"><div><strong>{slots.length}</strong><span>Slots</span></div><div><strong>{booked}/{total}</strong><span>Booked capacity</span></div></div><input aria-label="Select delivery date" type="date" min={todayLocal()} value={date} onChange={(e) => setDate(e.target.value)} /></div>
    {showForm && <form className="panel create-slot-form" onSubmit={submit}><div className="panel-heading"><div><h2>New delivery window</h2><p>All times are interpreted as India Standard Time.</p></div></div><div className="form-grid"><label>Start time<input type="time" value={start} onChange={(e) => setStart(e.target.value)} required /></label><label>End time<input type="time" min={start} value={end} onChange={(e) => setEnd(e.target.value)} required /></label><label>Parcel capacity<input type="number" min="1" max="500" value={capacity} onChange={(e) => setCapacity(e.target.value)} required /></label><button className="primary-button" disabled={busy}>{busy ? "Creating..." : "Save delivery slot"}</button></div></form>}
    <div className="section-title-row"><h2>Available windows</h2><button className="icon-button" onClick={() => void load()} title="Refresh slots"><RefreshCw size={16} /></button></div>
    {slots.length ? <div className="slots-grid">{slots.map((slot) => <div className="panel slot-card" key={slot.id}><div className="slot-card-top"><span className="slot-time">{slot.start_time.slice(0,5)} <span>to</span> {slot.end_time.slice(0,5)}</span><span className={slot.remaining_capacity ? "capacity-pill" : "full-pill"}>{slot.remaining_capacity ? "Available" : "Fully booked"}</span></div><div className="slot-capacity"><strong>{slot.booked_count}</strong><span> of {slot.capacity} parcels booked</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${slot.booked_count / slot.capacity * 100}%` }} /></div><div className="slot-card-foot"><span>{slot.remaining_capacity} spaces remaining</span><span>Slot #{slot.id}</span></div></div>)}</div> : <div className="panel"><EmptyState title="No slots for this date" description="Create a delivery window to start accepting bookings." /></div>}
  </>;
}