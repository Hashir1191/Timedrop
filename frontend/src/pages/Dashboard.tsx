import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, CalendarDays, CheckCircle2, Clock3, Package, RefreshCw, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { getParcels, getSlots } from "../api";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../auth";
import type { DeliverySlot, Parcel } from "../types";

function todayLocal() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
export default function Dashboard() {
  const { token } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  async function refresh() {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const [parcelData, slotData] = await Promise.all([getParcels(token), getSlots(token, todayLocal())]);
      setParcels(parcelData); setSlots(slotData);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load dashboard."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, [token]);
  const counts = useMemo(() => ({
    total: parcels.length,
    scheduled: parcels.filter((p) => p.status === "scheduled").length,
    out: parcels.filter((p) => p.status === "out_for_delivery").length,
    delivered: parcels.filter((p) => p.status === "delivered").length,
  }), [parcels]);
  const recent = parcels.slice(0, 5);
  const capacity = slots.reduce((sum, slot) => sum + slot.capacity, 0);
  const booked = slots.reduce((sum, slot) => sum + slot.booked_count, 0);
  return <><div className="page-heading"><div><div className="eyebrow">{new Date().toLocaleDateString("en-IN", { weekday: "long" }).toUpperCase()} — OPERATIONS OVERVIEW</div><h1>Good to see you.</h1><p>Here's what's happening across your deliveries today.</p></div><button className="secondary-button" onClick={() => void refresh()}><RefreshCw size={15} /> Refresh</button></div>
    {error && <div className="alert-error">{error}</div>}
    <div className="stats-grid">
      <Stat icon={Package} label="Total parcels" value={loading ? "—" : counts.total} note="All parcels in your system" tone="blue" />
      <Stat icon={CalendarDays} label="Scheduled" value={loading ? "—" : counts.scheduled} note="Ready for a delivery slot" tone="violet" />
      <Stat icon={Truck} label="Out for delivery" value={loading ? "—" : counts.out} note="Currently on the move" tone="amber" />
      <Stat icon={CheckCircle2} label="Delivered" value={loading ? "—" : counts.delivered} note="Successfully completed" tone="green" />
    </div>
    <div className="dashboard-grid"><section className="panel recent-panel"><div className="panel-heading"><div><h2>Recent parcels</h2><p>Your latest parcel activity</p></div><Link to="/parcels" className="text-link">View all <ArrowUpRight size={15} /></Link></div>{loading ? <div className="table-loading">Loading parcels...</div> : recent.length ? <div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>STATUS</th></tr></thead><tbody>{recent.map((parcel) => <tr key={parcel.id}><td className="tracking">{parcel.tracking_number}</td><td>{parcel.recipient_name}</td><td>{parcel.city}, {parcel.state}</td><td><StatusBadge status={parcel.status} /></td></tr>)}</tbody></table></div> : <EmptyState title="No parcels yet" description="Parcels will appear here once they are registered." />}</section>
    <section className="panel capacity-panel"><div className="panel-heading"><div><h2>Today's capacity</h2><p>Delivery slot utilization</p></div><Clock3 size={18} className="muted-icon" /></div><div className="capacity-number"><strong>{booked}</strong><span> / {capacity} booked</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${capacity ? Math.min(100, booked / capacity * 100) : 0}%` }} /></div><div className="capacity-meta"><span>{slots.length} active slots</span><span>{Math.max(0, capacity - booked)} spaces left</span></div><div className="slot-preview">{slots.slice(0, 4).map((slot) => <div className="slot-row" key={slot.id}><span>{slot.start_time.slice(0, 5)} – {slot.end_time.slice(0, 5)}</span><strong>{slot.booked_count}/{slot.capacity}</strong></div>)}{!loading && !slots.length && <p className="muted-copy">No delivery slots created for today.</p>}</div><Link to="/slots" className="secondary-button full-button">Manage delivery slots <ArrowUpRight size={15} /></Link></section></div>
  </>;
}
function Stat({ icon: Icon, label, value, note, tone }: { icon: typeof Package; label: string; value: number | string; note: string; tone: string }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={19} /></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>;
}