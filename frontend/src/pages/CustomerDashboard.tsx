import { useEffect, useState } from "react";
import { ArrowRight, ArrowUpRight, CalendarClock, CheckCircle2, Clock3, Package, Plus, ShieldCheck, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { getParcels } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { Parcel } from "../types";

export default function CustomerDashboard() {
  const { token, user } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let active = true;
    getParcels(token)
      .then((rows) => { if (active) setParcels(rows); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : "Unable to load parcels."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  const active = parcels.filter((parcel) => !["delivered", "cancelled"].includes(parcel.status)).length;
  const delivered = parcels.filter((parcel) => parcel.status === "delivered").length;
  const recent = parcels.slice(0, 4);

  return <div className="customer-dashboard">
    <section className="customer-hero">
      <div className="customer-hero-copy">
        <span className="customer-hero-kicker">YOUR DELIVERY SPACE</span>
        <h1>Good things are<br/><span>on their way.</span></h1>
        <p>Welcome back, {user?.full_name?.split(" ")[0] || "there"}. Keep every parcel and delivery plan in one clear place.</p>
        <div className="customer-hero-actions">
          <Link className="customer-hero-primary" to="/new-parcel"><Plus size={17}/> Create a parcel</Link>
          <Link className="customer-hero-secondary" to="/my-parcels">Track my parcels <ArrowRight size={16}/></Link>
        </div>
      </div>
      <div className="customer-hero-art" aria-hidden="true">
        <div className="customer-orbit orbit-one"/>
        <div className="customer-orbit orbit-two"/>
        <div className="customer-package"><Package size={54} strokeWidth={1.25}/></div>
        <div className="customer-floating-card"><span><CheckCircle2 size={14}/></span><div><strong>Delivery, organized</strong><small>Your parcels at a glance</small></div></div>
        <div className="customer-floating-dot"/>
      </div>
      <div className="customer-hero-foot"><span><ShieldMark/> Secure parcel management</span><span>One place for every delivery</span></div>
    </section>

    {error && <div className="alert-error">{error}</div>}

    <section className="customer-overview">
      <div className="customer-section-heading">
        <div><span className="customer-section-kicker">AT A GLANCE</span><h2>Your delivery overview</h2></div>
        <Link to="/my-parcels" className="customer-subtle-link">View parcel history <ArrowUpRight size={15}/></Link>
      </div>
      <div className="customer-metric-grid">
        <CustomerMetric icon={Package} label="Total parcels" value={loading ? "—" : parcels.length} tone="blue" note="All registered parcels"/>
        <CustomerMetric icon={Truck} label="In progress" value={loading ? "—" : active} tone="violet" note="Not yet completed"/>
        <CustomerMetric icon={CheckCircle2} label="Delivered" value={loading ? "—" : delivered} tone="green" note="Successfully completed"/>
      </div>
    </section>

    <section className="customer-recent-section">
      <div className="customer-section-heading">
        <div><span className="customer-section-kicker">LATEST ACTIVITY</span><h2>Recent parcels</h2><p>Your most recently registered deliveries.</p></div>
        <Link to="/my-parcels" className="customer-subtle-link">See all <ArrowRight size={15}/></Link>
      </div>
      {loading ? <div className="customer-parcel-skeletons">{[1,2,3].map((item) => <div className="customer-parcel-skeleton" key={item}/>)}</div> :
        recent.length ? <div className="customer-recent-grid">{recent.map((parcel) => <article className="customer-recent-card" key={parcel.id}>
          <div className="customer-recent-card-top"><span className="customer-parcel-icon"><Package size={18}/></span><StatusBadge status={parcel.status}/></div>
          <span className="customer-tracking-label">TRACKING NUMBER</span>
          <strong className="customer-tracking-number">{parcel.tracking_number}</strong>
          <div className="customer-recent-recipient"><strong>{parcel.recipient_name}</strong><span>{parcel.city}, {parcel.state}</span></div>
          <div className="customer-recent-card-foot"><span><Clock3 size={13}/> {new Date(parcel.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</span><Link to={["delivered","cancelled"].includes(parcel.status)?"/my-parcels":`/schedule/${parcel.id}`}>{parcel.status==="delivered"?"View parcel":"Manage delivery"} <ArrowUpRight size={14}/></Link></div>
        </article>)}</div> : <div className="customer-empty-panel"><EmptyState title="Your parcel space is ready" description="Create your first parcel and start arranging a delivery."/><Link className="primary-button" to="/new-parcel"><Plus size={16}/> Create your first parcel</Link></div>
      }
    </section>

    <section className="customer-help-strip"><span className="customer-help-icon"><CalendarClock size={18}/></span><div><strong>Choose a time that suits you</strong><p>When delivery slots are available, you can book or reschedule them from your parcel list.</p></div><Link to="/my-parcels">Manage deliveries <ArrowRight size={15}/></Link></section>
  </div>;
}

function CustomerMetric({icon:Icon,label,value,tone,note}:{icon:typeof Package;label:string;value:number|string;tone:string;note:string}) {
  return <article className="customer-metric-card"><span className={`customer-metric-icon ${tone}`}><Icon size={19}/></span><div className="customer-metric-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>;
}

function ShieldMark() { return <span className="customer-shield-mark"><ShieldCheck size={13}/></span>; }
