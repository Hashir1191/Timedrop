import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { CalendarDays, Plus, RefreshCw } from "lucide-react";
import { createSlot, updateSlot, getSlots, getBlackoutDates } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import type { DeliveryBlackoutDate, DeliverySlot } from "../types";

function todayLocal() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
export default function Slots() {
  const { token } = useAuth();
  const [date, setDate] = useState(todayLocal());
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [blackout, setBlackout] = useState<DeliveryBlackoutDate | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [start, setStart] = useState("09:00");
  const [end, setEnd] = useState("11:00");
  const [capacity, setCapacity] = useState("10");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [slotBusy, setSlotBusy] = useState<number | null>(null);
  const [capacityDrafts, setCapacityDrafts] = useState<Record<number, string>>({});
  async function load() { if (!token || !date) return; try { setError(""); const [available, closures] = await Promise.all([getSlots(token, date, true), getBlackoutDates(token, date, date, true)]); setSlots(available); setBlackout(closures.find(item => item.is_active) ?? null); } catch (err) { setError(err instanceof Error ? err.message : "Unable to load slots."); } }
  useEffect(() => { void load(); }, [token, date]);

  async function saveCapacity(slot: DeliverySlot) {
    if (!token) return;
    const capacity = Number(capacityDrafts[slot.id] ?? slot.capacity);
    if (!Number.isInteger(capacity) || capacity < 1 || capacity > 500) {
      setError("Slot capacity must be a whole number between 1 and 500.");
      return;
    }
    setSlotBusy(slot.id); setError(""); setSuccess("");
    try {
      const updated = await updateSlot(token, slot.id, { capacity });
      setSlots(current => current.map(item => item.id === slot.id ? updated : item));
      setCapacityDrafts(current => ({ ...current, [slot.id]: String(updated.capacity) }));
      setSuccess("Delivery slot capacity updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update slot capacity.");
    } finally {
      setSlotBusy(null);
    }
  }

  async function toggleSlot(slot: DeliverySlot) {
    if (!token) return;
    setSlotBusy(slot.id); setError(""); setSuccess("");
    try {
      const updated = await updateSlot(token, slot.id, { is_active: !slot.is_active });
      setSlots(current => current.map(item => item.id === slot.id ? updated : item));
      setSuccess(updated.is_active ? "Delivery slot reactivated." : "Delivery slot paused.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update delivery slot.");
    } finally {
      setSlotBusy(null);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); if (!token) return; setBusy(true); setError(""); setSuccess("");
    try { await createSlot(token, { delivery_date: date, start_time: start, end_time: end, capacity: Number(capacity) }); setSuccess("Delivery slot created."); setShowForm(false); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to create slot."); }
    finally { setBusy(false); }
  }
  const booked = slots.reduce((n, s) => n + s.booked_count, 0);
  const total = slots.reduce((n, s) => n + s.capacity, 0);
  return <div className="slot-management-workspace"><div className="page-heading"><div><div className="eyebrow">CAPACITY PLANNING</div><h1>Delivery slots</h1><p>Create delivery windows and keep an eye on available capacity.</p></div><button className="primary-button" disabled={!!blackout} title={blackout ? "This date is closed for delivery operations." : "Create a delivery slot"} onClick={() => { setShowForm((v) => !v); setSuccess(""); }}><Plus size={17} /> {blackout ? "Date closed" : "Create slot"}</button></div>
    {error && <div className="alert-error">{error}</div>}{success && <div className="alert-success">{success}</div>}{blackout && <div className="alert-error slot-blackout-notice"><CalendarDays size={16}/> Delivery operations are closed on this date: <strong>{blackout.reason}</strong></div>}
    <div className="slot-summary"><div className="summary-icon"><CalendarDays size={20} /></div><div><span>Selected date</span><strong>{new Date(date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</strong></div><div className="summary-metrics"><div><strong>{slots.length}</strong><span>Slots</span></div><div><strong>{booked}/{total}</strong><span>Booked capacity</span></div></div><input aria-label="Select delivery date" type="date" min={todayLocal()} value={date} onChange={(e) => { setDate(e.target.value); setBlackout(null); setShowForm(false); }} /></div>
    {showForm && !blackout && <form className="panel create-slot-form" onSubmit={submit}><div className="panel-heading"><div><h2>New delivery window</h2><p>All times are interpreted as India Standard Time.</p></div></div><div className="form-grid"><label>Start time<input type="time" value={start} onChange={(e) => setStart(e.target.value)} required /></label><label>End time<input type="time" min={start} value={end} onChange={(e) => setEnd(e.target.value)} required /></label><label>Parcel capacity<input type="number" min="1" max="500" value={capacity} onChange={(e) => setCapacity(e.target.value)} required /></label><button className="primary-button" disabled={busy}>{busy ? "Creating..." : "Save delivery slot"}</button></div></form>}
    <div className="section-title-row"><h2>Available windows</h2><button className="icon-button" onClick={() => void load()} title="Refresh slots"><RefreshCw size={16} /></button></div>
    {slots.length ? <div className="slots-grid">{slots.map((slot) => <div className={`panel slot-card ${slot.is_active ? "" : "slot-card-paused"}`} key={slot.id}><div className="slot-card-top"><span className="slot-time">{slot.start_time.slice(0,5)} <span>to</span> {slot.end_time.slice(0,5)}</span><span className={!slot.is_active ? "full-pill" : blackout ? "full-pill" : slot.remaining_capacity ? "capacity-pill" : "full-pill"}>{!slot.is_active ? "Paused" : blackout ? "Date closed" : slot.remaining_capacity ? "Available" : "Fully booked"}</span></div><div className="slot-capacity"><strong>{slot.booked_count}</strong><span> of {slot.capacity} parcels booked</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${Math.min(100, slot.booked_count / slot.capacity * 100)}%` }} /></div><div className="slot-card-foot"><span>{slot.remaining_capacity} spaces remaining</span><span>Slot #{slot.id}</span></div><div className="slot-management-actions"><label>Capacity<input aria-label={`Capacity for slot ${slot.id}`} type="number" min={1} max={500} value={capacityDrafts[slot.id] ?? String(slot.capacity)} onChange={event=>setCapacityDrafts(current=>({...current,[slot.id]:event.target.value}))}/></label><button type="button" className="secondary-button" disabled={slotBusy===slot.id || Number(capacityDrafts[slot.id] ?? slot.capacity)===slot.capacity} onClick={()=>void saveCapacity(slot)}>Save</button><button type="button" className={slot.is_active ? "danger-button" : "secondary-button"} disabled={slotBusy===slot.id || (slot.is_active && slot.booked_count>0) || (!slot.is_active && !!blackout)} title={slot.is_active && slot.booked_count>0 ? "Resolve confirmed bookings before pausing this slot." : !slot.is_active && blackout ? "Reopen the blackout date before reactivating this slot." : ""} onClick={()=>void toggleSlot(slot)}>{slot.is_active ? "Pause slot" : "Reactivate"}</button></div></div>)}</div> : <div className="panel"><EmptyState title="No slots for this date" description="Create a delivery window to start accepting bookings." /></div>}
  </div>;
}