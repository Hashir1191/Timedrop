import { useEffect, useState } from "react";
import { CalendarClock, RefreshCw, XCircle } from "lucide-react";
import { cancelBooking, getParcels, getSlots, rescheduleBooking } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { DeliverySlot, Parcel } from "../types";

function todayLocal() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`; }
export default function Bookings() {
  const { token } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [date, setDate] = useState(todayLocal());
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  async function load() {
    if (!token) return;
    try { setError(""); const [p, s] = await Promise.all([getParcels(token), getSlots(token, date)]); setParcels(p.filter((x) => x.status === "scheduled")); setSlots(s); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load bookings."); }
  }
  useEffect(() => { void load(); }, [token, date]);
  async function cancel(parcel: Parcel) {
    if (!token || !window.confirm(`Cancel the active delivery booking for ${parcel.tracking_number}?`)) return;
    setBusy(parcel.id); setError("");
    try { await cancelBooking(token, parcel.id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to cancel booking."); }
    finally { setBusy(null); }
  }
  async function move(parcel: Parcel, slotId: number) {
    if (!token) return; setBusy(parcel.id); setError("");
    try { await rescheduleBooking(token, parcel.id, slotId); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to reschedule booking."); }
    finally { setBusy(null); }
  }
  return <><div className="page-heading"><div><div className="eyebrow">DELIVERY COORDINATION</div><h1>Bookings</h1><p>Review scheduled parcels and manage their delivery appointments.</p></div><button className="secondary-button" onClick={() => void load()}><RefreshCw size={15} /> Refresh</button></div>
    {error && <div className="alert-error">{error}</div>}
    <div className="filter-date"><CalendarClock size={17} /><label htmlFor="booking-date">Available destination slots for</label><input id="booking-date" type="date" min={todayLocal()} value={date} onChange={(e) => setDate(e.target.value)} /></div>
    {parcels.length ? <div className="booking-list">{parcels.map((parcel) => <div className="panel booking-card" key={parcel.id}><div className="booking-main"><div className="booking-icon"><CalendarClock size={20} /></div><div><strong>{parcel.tracking_number}</strong><span>{parcel.recipient_name} · {parcel.city}</span></div></div><StatusBadge status={parcel.status} /><div className="booking-actions"><select defaultValue="" disabled={busy === parcel.id} onChange={(e) => { if (e.target.value) void move(parcel, Number(e.target.value)); }}><option value="">Reschedule to...</option>{slots.filter((s) => s.remaining_capacity > 0).map((s) => <option key={s.id} value={s.id}>{s.start_time.slice(0,5)}–{s.end_time.slice(0,5)} · {s.remaining_capacity} left</option>)}</select><button className="danger-button" disabled={busy === parcel.id} onClick={() => void cancel(parcel)}><XCircle size={15} /> Cancel</button></div></div>)}</div> : <div className="panel"><EmptyState title="No scheduled parcels" description="Parcels with an active scheduled status will appear here." /></div>}
    <p className="page-footnote">This view lists parcels with a scheduled status. Slot/date details are not currently exposed by the backend booking-list API.</p>
  </>;
}