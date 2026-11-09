import { useEffect, useState } from "react";
import { CalendarClock, RefreshCw, XCircle } from "lucide-react";
import { cancelBooking, getAdminBookings, getSlots, rescheduleBooking } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { AdminBooking, DeliverySlot } from "../types";

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function formatDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function Bookings() {
  const { token } = useAuth();
  const [bookings, setBookings] = useState<AdminBooking[]>([]);
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [statusFilter, setStatusFilter] = useState<"booked" | "cancelled" | "all">("booked");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [slotDate, setSlotDate] = useState(todayLocal());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);

  async function loadBookings() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const result = await getAdminBookings(token, statusFilter, deliveryDate);
      setBookings(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load booking records.");
    } finally {
      setLoading(false);
    }
  }

  async function loadSlots() {
    if (!token) return;
    try {
      setSlots(await getSlots(token, slotDate));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load destination slots.");
    }
  }

  useEffect(() => { void loadBookings(); }, [token, statusFilter, deliveryDate]);
  useEffect(() => { void loadSlots(); }, [token, slotDate]);

  async function cancel(booking: AdminBooking) {
    if (!token || !window.confirm(`Cancel the delivery booking for ${booking.parcel.tracking_number}?`)) return;
    setBusy(booking.parcel_id);
    setError("");
    try {
      await cancelBooking(token, booking.parcel_id);
      await loadBookings();
      await loadSlots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to cancel booking.");
    } finally {
      setBusy(null);
    }
  }

  async function move(booking: AdminBooking, slotId: number) {
    if (!token) return;
    setBusy(booking.parcel_id);
    setError("");
    try {
      await rescheduleBooking(token, booking.parcel_id, slotId);
      await loadBookings();
      await loadSlots();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reschedule booking.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">DELIVERY COORDINATION</div>
          <h1>Bookings</h1>
          <p>Manage actual delivery bookings with their parcel and slot details.</p>
        </div>
        <button className="secondary-button" onClick={() => { void loadBookings(); void loadSlots(); }}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {error && <div className="alert-error">{error}</div>}

      <div className="filter-date">
        <CalendarClock size={17} />
        <label htmlFor="booking-status">Booking status</label>
        <select id="booking-status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as "booked" | "cancelled" | "all")}>
          <option value="booked">Active bookings</option>
          <option value="cancelled">Cancelled history</option>
          <option value="all">All bookings</option>
        </select>
        <label htmlFor="booking-date">Delivery date</label>
        <input id="booking-date" type="date" value={deliveryDate} onChange={(e) => setDeliveryDate(e.target.value)} />
      </div>

      <div className="filter-date">
        <CalendarClock size={17} />
        <label htmlFor="slot-date">Show available replacement slots for</label>
        <input id="slot-date" type="date" min={todayLocal()} value={slotDate} onChange={(e) => setSlotDate(e.target.value)} />
      </div>

      {loading ? (
        <div className="panel"><div className="table-loading">Loading booking records...</div></div>
      ) : bookings.length ? (
        <div className="booking-list">
          {bookings.map((booking) => {
            const parcel = booking.parcel;
            const slot = booking.slot;
            const isActive = booking.status === "booked";
            return (
              <div className="panel booking-card" key={booking.id}>
                <div className="booking-main">
                  <div className="booking-icon"><CalendarClock size={20} /></div>
                  <div>
                    <strong>{parcel.tracking_number}</strong>
                    <span>{parcel.recipient_name} · {parcel.phone}</span>
                    <span>{parcel.city}, {parcel.state} · {parcel.pincode}</span>
                  </div>
                </div>
                <div className="booking-details">
                  <strong>{formatDate(slot.delivery_date)}</strong>
                  <span>{slot.start_time.slice(0, 5)}–{slot.end_time.slice(0, 5)}</span>
                  <span>Slot #{slot.id} · {slot.booked_count}/{slot.capacity} booked</span>
                </div>
                <div className="booking-status">
                  <span className={isActive ? "status-badge status-scheduled" : "status-badge status-cancelled"}><span />{booking.status}</span>
                  <StatusBadge status={parcel.status} />
                </div>
                {isActive && (
                  <div className="booking-actions">
                    <select
                      key={`${booking.id}-${booking.slot_id}-${slotDate}`}
                      defaultValue=""
                      disabled={busy === booking.parcel_id}
                      onChange={(e) => { if (e.target.value) void move(booking, Number(e.target.value)); }}
                    >
                      <option value="">Reschedule to...</option>
                      {slots.filter((s) => s.remaining_capacity > 0 && s.id !== booking.slot_id).map((s) => (
                        <option key={s.id} value={s.id}>
                          {formatDate(s.delivery_date)} · {s.start_time.slice(0, 5)}–{s.end_time.slice(0, 5)} · {s.remaining_capacity} left
                        </option>
                      ))}
                    </select>
                    <button className="danger-button" disabled={busy === booking.parcel_id} onClick={() => void cancel(booking)}>
                      <XCircle size={15} /> Cancel
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="panel">
          <EmptyState
            title={statusFilter === "cancelled" ? "No cancelled bookings" : "No bookings found"}
            description="Try changing the booking status or delivery-date filters."
          />
        </div>
      )}
      <p className="page-footnote">
        Booking records come directly from the delivery_bookings table. A cancelled row remains visible until that parcel is booked again; the current one-booking-per-parcel model reuses that row on rebooking.
      </p>
    </>
  );
}
