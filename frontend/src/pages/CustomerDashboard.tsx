import { useEffect, useState } from "react";
import { ArrowUpRight, Package, PlusCircle, Truck, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";
import { getParcels } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { Parcel } from "../types";

export default function CustomerDashboard() {
  const { token, user } = useAuth();
  const [parcels,setParcels] = useState<Parcel[]>([]);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  useEffect(() => {
    if (!token) return;
    getParcels(token).then(setParcels).catch((e) => setError(e instanceof Error ? e.message : "Unable to load parcels.")).finally(() => setLoading(false));
  },[token]);
  const active = parcels.filter(p => !["delivered","cancelled"].includes(p.status)).length;
  const delivered = parcels.filter(p => p.status === "delivered").length;
  return <>
    <div className="page-heading"><div><div className="eyebrow">YOUR DELIVERY SPACE</div><h1>Hello, {user?.full_name?.split(" ")[0] || "there"}.</h1><p>Track your parcels and choose a delivery time that works for you.</p></div><Link className="primary-button" to="/new-parcel"><PlusCircle size={16}/> Create parcel</Link></div>
    {error && <div className="alert-error">{error}</div>}
    <div className="stats-grid customer-stats">
      <CustomerStat icon={Package} label="Total parcels" value={loading ? "—" : parcels.length}/>
      <CustomerStat icon={Truck} label="In progress" value={loading ? "—" : active}/>
      <CustomerStat icon={CheckCircle2} label="Delivered" value={loading ? "—" : delivered}/>
    </div>
    <section className="panel recent-panel customer-parcel-panel">
      <div className="panel-heading"><div><h2>Your recent parcels</h2><p>Updates from your delivery list</p></div><Link to="/my-parcels" className="text-link">View all <ArrowUpRight size={15}/></Link></div>
      {loading ? <div className="table-loading">Loading your parcels...</div> : parcels.length ? <div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>STATUS</th><th></th></tr></thead><tbody>{parcels.slice(0,6).map(p=><tr key={p.id}><td className="tracking">{p.tracking_number}</td><td>{p.recipient_name}<span className="cell-sub">{p.phone}</span></td><td>{p.city}, {p.state}<span className="cell-sub">{p.pincode}</span></td><td><StatusBadge status={p.status}/></td><td><Link className="text-link" to={`/schedule/${p.id}`}>Manage <ArrowUpRight size={14}/></Link></td></tr>)}</tbody></table></div> : <EmptyState title="No parcels yet" description="Create your first parcel to start arranging a delivery."/>}
    </section>
    <div className="customer-help-note"><Package size={18}/><span><strong>Good to know</strong> You can book or change a delivery slot whenever operations has made availability available.</span></div>
  </>;
}
function CustomerStat({icon:Icon,label,value}:{icon:typeof Package;label:string;value:number|string}) {
 return <div className="stat-card"><div className="stat-icon blue"><Icon size={19}/></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div></div>;
}
