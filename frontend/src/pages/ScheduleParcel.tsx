import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, CalendarClock, CheckCircle2, Clock3, RefreshCw, ShieldCheck } from "lucide-react";
import { bookParcel, cancelBooking, getParcelBooking, getParcels, getSlots, getBlackoutStatus, rescheduleBooking } from "../api";
import { useAuth } from "../auth";
import type { Booking, DeliverySlot, Parcel } from "../types";
import StatusBadge from "../components/StatusBadge";

function dateLocal() {
  const date = new Date();
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
function formatDate(value: string) {
  return new Date(value + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "long", year: "numeric" });
}
function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export default function ScheduleParcel() {
  const { parcelId } = useParams();
  const id = Number(parcelId);
  const { token } = useAuth();
  const [parcel, setParcel] = useState<Parcel | null>(null);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [date, setDate] = useState(dateLocal());
  const [selected, setSelected] = useState("");
  const [blackoutReason, setBlackoutReason] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [slotError, setSlotError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(true);
  const [slotRefreshKey, setSlotRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    async function loadParcel() {
      if (!token || !Number.isSafeInteger(id) || id <= 0) {
        setError("Invalid parcel reference.");
        setLoading(false);
        return;
      }
      setLoading(true);
      setError("");
      setParcel(null);
      setBooking(null);
      try {
        const rows = await getParcels(token);
        const found = rows.find((item) => item.id === id);
        if (!found) throw new Error("Parcel not found.");
        const currentBooking = await getParcelBooking(token, id).catch((err: unknown) => {
          if (err && typeof err === "object" && "status" in err && (err as { status: number }).status === 404) return null;
          throw err;
        });
        if (active) {
          setParcel(found);
          setBooking(currentBooking);
        }
      } catch (err) {
        if (active) setError(errorMessage(err, "Unable to load parcel."));
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadParcel();
    return () => { active = false; };
  }, [token, id]);

  useEffect(() => {
    let active = true;
    async function loadSlots() {
      if (!token) return;
      setLoadingSlots(true);
      setSlotError("");
      setSelected("");
      try {
        const [available, closure] = await Promise.all([getSlots(token, date), getBlackoutStatus(token, date)]);
        if (active) {
          setSlots(available);
          setBlackoutReason(closure.is_blackout ? closure.reason : null);
        }
      } catch (err) {
        if (active) {
          setSlots([]);
          setBlackoutReason(null);
          setSlotError(errorMessage(err, "Unable to load delivery slots."));
        }
      } finally {
        if (active) setLoadingSlots(false);
      }
    }
    void loadSlots();
    return () => { active = false; };
  }, [token, date, slotRefreshKey]);

  async function submit() {
    if (!token || !selected || busy || loadingSlots) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = booking
        ? await rescheduleBooking(token, id, Number(selected))
        : await bookParcel(token, id, Number(selected));
      setBooking(updated);
      setMessage(booking ? "Your delivery slot has been changed." : "Your delivery slot is confirmed.");
      setSlotRefreshKey((key) => key + 1);
    } catch (err) {
      setError(errorMessage(err, "Unable to save booking."));
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!token || !booking || busy || !window.confirm("Cancel this delivery booking?")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await cancelBooking(token, id);
      setBooking(null);
      setParcel((current) => current ? { ...current, status: "registered" } : current);
      setMessage("Your booking has been cancelled.");
      setSlotRefreshKey((key) => key + 1);
    } catch (err) {
      setError(errorMessage(err, "Unable to cancel booking."));
    } finally {
      setBusy(false);
    }
  }

  const selectedSlot = useMemo(() => slots.find((slot) => String(slot.id) === selected) ?? null, [slots, selected]);
  const terminal = ["delivered", "failed", "cancelled"].includes(parcel?.status ?? "");
  if (loading) return <div className="customer-schedule-workspace"><div className="customer-schedule-skeleton"/><div className="customer-schedule-skeleton"/></div>;
  if (!parcel) return <div className="customer-schedule-workspace"><div className="alert-error" role="alert">{error || "Parcel not found."}</div><Link to="/my-parcels" className="text-link"><ArrowLeft size={14}/> Back to parcels</Link></div>;

  return <div className="customer-schedule-workspace">
    <div className="page-heading customer-schedule-heading"><div><div className="eyebrow">DELIVERY SCHEDULING · STEP 2 OF 2</div><h1>{booking ? "Manage your delivery" : "Choose a delivery time"}</h1><p>Confirm a suitable delivery window for <strong>{parcel.tracking_number}</strong>.</p></div><Link to="/my-parcels" className="secondary-button"><ArrowLeft size={15}/> My parcels</Link></div>
    <div className="customer-schedule-progress"><span className="done"><CheckCircle2 size={14}/> Parcel details</span><i/><span className="current"><CalendarClock size={14}/> Delivery slot</span></div>
    {error && <div className="alert-error" role="alert">{error}</div>}
    {message && <div className="alert-success" role="status"><CheckCircle2 size={15}/>{message}</div>}

    <section className="customer-schedule-parcel">
      <div className="customer-schedule-parcel-main"><span className="customer-schedule-package-icon"><CalendarClock size={21}/></span><div><span>PARCEL / RECIPIENT</span><strong>{parcel.tracking_number}</strong><small>{parcel.recipient_name}</small></div><StatusBadge status={parcel.status}/></div>
      <div className="customer-schedule-address"><span>DELIVERY DESTINATION</span><strong>{parcel.address_line}</strong><small>{parcel.city}, {parcel.state} · {parcel.pincode}</small></div>
      {booking && <div className="customer-confirmed-booking"><span className="customer-confirmed-icon"><CheckCircle2 size={17}/></span><div><small>CONFIRMED DELIVERY WINDOW</small><strong>{formatDate(booking.delivery_date)}</strong><span>{booking.start_time.slice(0, 5)} – {booking.end_time.slice(0, 5)}</span></div><button type="button" className="customer-cancel-booking" disabled={busy} onClick={() => void cancel()}>Cancel booking</button></div>}
    </section>

    <section className="customer-slot-section">
      <div className="customer-slot-section-heading"><div><span className="customer-aside-kicker">AVAILABLE DELIVERY WINDOWS</span><h2>{booking ? "Choose a new time" : "Select your preferred time"}</h2><p>Only slots with remaining capacity can be selected.</p></div><span className="customer-slot-legend"><i/> Available</span></div>
      <div className="customer-slot-date-panel"><label htmlFor="customer-delivery-date"><CalendarClock size={16}/> Select delivery date</label><input id="customer-delivery-date" type="date" min={dateLocal()} value={date} onChange={(event) => setDate(event.target.value)}/><span>{formatDate(date)}</span></div>
      {slotError ? <div className="customer-slot-load-error" role="alert"><AlertCircle size={17}/><span>{slotError}</span><button type="button" className="secondary-button" onClick={() => setSlotRefreshKey((key) => key + 1)}><RefreshCw size={14}/> Retry slots</button></div> :
        loadingSlots ? <div className="customer-slot-loading" role="status" aria-label="Loading available delivery windows">{[1, 2, 3, 4].map((item) => <div key={item}/>)}</div> :
        slots.some((slot) => slot.remaining_capacity > 0) ? <div className="customer-slot-grid">{slots.map((slot) => <button type="button" key={slot.id} disabled={slot.remaining_capacity <= 0 || busy || terminal} onClick={() => setSelected(String(slot.id))} className={`customer-slot-option ${selected === String(slot.id) ? "selected" : ""} ${slot.remaining_capacity <= 0 ? "unavailable" : ""}`}>
          <span className="customer-slot-option-icon"><Clock3 size={16}/></span><strong>{slot.start_time.slice(0, 5)} – {slot.end_time.slice(0, 5)}</strong><small>{slot.remaining_capacity > 0 ? `${slot.remaining_capacity} spaces remaining` : "Fully booked"}</small>{selected === String(slot.id) && <span className="customer-slot-selected"><CheckCircle2 size={14}/></span>}
        </button>)}</div> :
        <div className="customer-no-slots"><CalendarClock size={24}/><strong>{blackoutReason ? "Deliveries are closed on this date" : "No available slots for this date"}</strong><span>{blackoutReason || "Choose another date to see more delivery windows."}</span></div>
      }
      {selectedSlot && <div className="customer-selected-summary"><span><CheckCircle2 size={16}/> Selected delivery window</span><strong>{formatDate(date)} · {selectedSlot.start_time.slice(0, 5)} – {selectedSlot.end_time.slice(0, 5)}</strong></div>}
      <div className="customer-schedule-submit"><div><ShieldCheck size={17}/><span>Your booking is confirmed only after you select and submit an available slot.</span></div><button className="primary-button" disabled={!selected || busy || terminal || loadingSlots || Boolean(slotError)} onClick={() => void submit()}>{busy ? "Saving booking…" : booking ? "Confirm reschedule" : "Confirm delivery slot"} <CheckCircle2 size={15}/></button></div>
      {terminal && <p className="page-footnote">This parcel cannot be scheduled because its status is {parcel.status}.</p>}
    </section>
  </div>;
}
