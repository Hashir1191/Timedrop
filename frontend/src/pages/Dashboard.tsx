import { useEffect, useMemo, useState } from "react";
import { ArrowRight, ArrowUpRight, CalendarClock, CalendarDays, CheckCircle2, Clock3, Package, RefreshCw, Truck, Warehouse } from "lucide-react";
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
  const { token, user } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [slots, setSlots] = useState<DeliverySlot[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [parcelData, slotData] = await Promise.all([getParcels(token), getSlots(token, todayLocal())]);
      setParcels(parcelData);
      setSlots(slotData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, [token]);

  const counts = useMemo(() => ({
    total: parcels.length,
    scheduled: parcels.filter((parcel) => parcel.status === "scheduled").length,
    out: parcels.filter((parcel) => parcel.status === "out_for_delivery").length,
    delivered: parcels.filter((parcel) => parcel.status === "delivered").length,
  }), [parcels]);
  const recent = parcels.slice(0, 4);
  const capacity = slots.reduce((sum, slot) => sum + slot.capacity, 0);
  const booked = slots.reduce((sum, slot) => sum + slot.booked_count, 0);
  const remaining = Math.max(0, capacity - booked);
  const utilization = capacity ? Math.min(100, booked / capacity * 100) : 0;

  return <div className="operations-dashboard">
    <section className="operations-hero">
      <div className="operations-hero-copy">
        <span className="operations-hero-kicker">{new Date().toLocaleDateString("en-IN", {weekday:"long"}).toUpperCase()} · OPERATIONS CONTROL</span>
        <h1>Operations,<br/><span>in sync.</span></h1>
        <p>Welcome back{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}. Here's a clear view of parcel movement and today's delivery capacity.</p>
        <div className="operations-hero-actions">
          <Link to="/intake" className="operations-hero-primary"><Package size={16}/> Receive a parcel</Link>
          <Link to="/analytics" className="operations-hero-secondary">View performance <ArrowRight size={15}/></Link>
        </div>
      </div>
      <div className="operations-hero-visual" aria-hidden="true">
        <div className="operations-orbit orbit-large"/><div className="operations-orbit orbit-small"/>
        <div className="operations-hero-package"><Package size={52} strokeWidth={1.3}/></div>
        <div className="operations-floating-stat"><span><Truck size={14}/></span><div><strong>{loading ? "—" : counts.out} on the move</strong><small>Out for delivery</small></div></div>
      </div>
      <div className="operations-hero-foot"><span><Warehouse size={13}/> Last-mile operations workspace</span><span>Live figures from recorded parcel data</span></div>
    </section>

    {error && <div className="alert-error">{error}</div>}

    <section className="operations-metrics">
      <Metric icon={Package} label="Total parcels" value={loading ? "—" : counts.total} note="All parcels in your system" tone="blue"/>
      <Metric icon={CalendarDays} label="Scheduled" value={loading ? "—" : counts.scheduled} note="Booked for delivery" tone="violet"/>
      <Metric icon={Truck} label="Out for delivery" value={loading ? "—" : counts.out} note="Currently with partners" tone="amber"/>
      <Metric icon={CheckCircle2} label="Delivered" value={loading ? "—" : counts.delivered} note="Successfully completed" tone="green"/>
    </section>

    <div className="operations-overview-grid">
      <section className="panel operations-recent-panel">
        <div className="panel-heading"><div><span className="operations-panel-kicker">LATEST MOVEMENT</span><h2>Recent parcels</h2><p>The newest parcel records across your operation.</p></div><Link to="/parcels" className="text-link">View all <ArrowUpRight size={15}/></Link></div>
        {loading ? <div className="operations-loading-list">{[1,2,3].map((item) => <div className="operations-loading-row" key={item}/>)}</div> :
          recent.length ? <div className="operations-recent-list">{recent.map((parcel) => <article className="operations-recent-item" key={parcel.id}>
            <span className="operations-recent-icon"><Package size={17}/></span>
            <div className="operations-recent-copy"><strong>{parcel.tracking_number}</strong><span>{parcel.recipient_name} · {parcel.city}, {parcel.state}</span></div>
            <StatusBadge status={parcel.status}/>
            <span className="operations-recent-date">{new Date(parcel.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}</span>
          </article>)}</div> : <EmptyState title="No parcels yet" description="Registered parcels will appear here."/>}
        <div className="operations-panel-footer"><Link to="/parcels">Open parcel register <ArrowRight size={14}/></Link><Link to="/warehouse">Warehouse inventory <ArrowRight size={14}/></Link></div>
      </section>

      <section className="panel operations-capacity-panel">
        <div className="panel-heading"><div><span className="operations-panel-kicker">TODAY'S SCHEDULE</span><h2>Delivery capacity</h2><p>Slot utilization for {new Date(todayLocal()+"T00:00:00").toLocaleDateString("en-IN",{day:"numeric",month:"long"})}.</p></div><span className="operations-capacity-icon"><CalendarClock size={18}/></span></div>
        <div className="operations-capacity-number"><strong>{loading ? "—" : booked}</strong><span>/ {loading ? "—" : capacity} booked</span></div>
        <div className="operations-capacity-track"><span style={{width:`${utilization}%`}}/></div>
        <div className="operations-capacity-meta"><span>{slots.length} active slots</span><strong>{loading ? "—" : remaining} spaces left</strong></div>
        <div className="operations-slot-list">{slots.slice(0,5).map((slot) => <div className="operations-slot-row" key={slot.id}><span><Clock3 size={13}/>{slot.start_time.slice(0,5)} – {slot.end_time.slice(0,5)}</span><strong>{slot.booked_count}/{slot.capacity}</strong><div className="operations-slot-mini"><span style={{width:`${slot.capacity ? Math.min(100,slot.booked_count/slot.capacity*100) : 0}%`}}/></div></div>)}
          {!loading && !slots.length && <p className="muted-copy">No delivery slots created for today.</p>}
        </div>
        <Link to="/slots" className="operations-capacity-link">Manage delivery slots <ArrowUpRight size={15}/></Link>
      </section>
    </div>
  </div>;
}

function Metric({icon:Icon,label,value,note,tone}:{icon:typeof Package;label:string;value:number|string;note:string;tone:string}) {
  return <article className="operations-metric"><span className={`operations-metric-icon ${tone}`}><Icon size={19}/></span><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>;
}
