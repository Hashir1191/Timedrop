import { useEffect, useMemo, useState } from "react";
import { ArrowDownToLine, ArrowRight, ArrowUpRight, CheckCircle2, Clock3, Package, Plus, RefreshCw, Truck, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { getParcels } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { Parcel } from "../types";

export default function MerchantDashboard() {
  const { token, user } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    if (!token) return;
    setLoading(true); setError("");
    try { setParcels(await getParcels(token)); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to load your shipments."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, [token]);

  const stats = useMemo(() => ({
    total: parcels.length,
    pending: parcels.filter(p => ["registered", "scheduled"].includes(p.status)).length,
    transit: parcels.filter(p => p.status === "out_for_delivery").length,
    delivered: parcels.filter(p => p.status === "delivered").length,
    failed: parcels.filter(p => p.status === "failed").length,
  }), [parcels]);
  const recent = parcels.slice(0, 6);
  const successRate = stats.total ? Math.round(stats.delivered / stats.total * 100) : 0;

  return <div className="merchant-dashboard">
    <section className="merchant-welcome">
      <div className="merchant-welcome-copy">
        <span className="merchant-kicker">MERCHANT OVERVIEW · {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" }).toUpperCase()}</span>
        <h1>Your business,<br/><span>moving forward.</span></h1>
        <p>Good to see you{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}. Here's what's happening with your deliveries today.</p>
        <div className="merchant-welcome-actions">
          <Link to="/new-shipment" className="merchant-primary-action"><Plus size={16}/> Create shipment</Link>
          <Link to="/shipments" className="merchant-secondary-action">View all shipments <ArrowRight size={15}/></Link>
        </div>
      </div>
      <div className="merchant-welcome-art" aria-hidden="true">
        <div className="merchant-art-orbit orbit-a"/><div className="merchant-art-orbit orbit-b"/>
        <div className="merchant-art-package"><Package size={54} strokeWidth={1.25}/></div>
        <div className="merchant-art-float"><span><Truck size={15}/></span><div><strong>{loading ? "—" : stats.transit} on the move</strong><small>Out for delivery</small></div></div>
      </div>
      <div className="merchant-welcome-foot"><span><CheckCircle2 size={13}/> Your shipping workspace</span><span>Shipment figures update from your account</span></div>
    </section>

    {error && <div className="alert-error" role="alert"><span>{error}</span><button className="secondary-button" onClick={() => void refresh()}><RefreshCw size={14}/> Try again</button></div>}

    <section className="merchant-stats-grid">
      <Metric icon={Package} label="Total shipments" value={loading ? "—" : stats.total} note="All shipments created" tone="blue"/>
      <Metric icon={Clock3} label="Awaiting delivery" value={loading ? "—" : stats.pending} note="Registered or scheduled" tone="violet"/>
      <Metric icon={Truck} label="In transit" value={loading ? "—" : stats.transit} note="Currently out for delivery" tone="amber"/>
      <Metric icon={CheckCircle2} label="Delivered" value={loading ? "—" : stats.delivered} note="Successfully completed" tone="green"/>
    </section>

    <div className="merchant-content-grid">
      <section className="panel merchant-shipments-panel">
        <div className="panel-heading"><div><span className="merchant-panel-kicker">SHIPMENT ACTIVITY</span><h2>Recent shipments</h2><p>Keep an eye on your latest customer deliveries.</p></div><Link to="/shipments" className="text-link">View all <ArrowUpRight size={15}/></Link></div>
        {loading ? <div className="merchant-loading">{[1,2,3,4].map(i => <div key={i}/>)}</div> :
          recent.length ? <div className="table-wrap"><table className="merchant-table"><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>DATE</th><th>STATUS</th></tr></thead><tbody>{recent.map(p => <tr key={p.id}><td><span className="merchant-tracking">{p.tracking_number}</span></td><td><strong className="merchant-recipient">{p.recipient_name}</strong></td><td>{p.city}, {p.state}</td><td>{new Date(p.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short"})}</td><td><StatusBadge status={p.status}/></td></tr>)}</tbody></table></div> :
          <EmptyState title="No shipments yet" description="Create your first shipment to see its progress here."/>}
        <div className="merchant-panel-footer"><Link to="/new-shipment"><Plus size={14}/> Create a shipment</Link><span>{stats.failed} failed deliveries</span></div>
      </section>

      <div className="merchant-side-column">
        <section className="panel merchant-performance-panel">
          <div className="panel-heading"><div><span className="merchant-panel-kicker">DELIVERY PERFORMANCE</span><h2>Delivery success</h2><p>Based on all your shipments.</p></div><span className="merchant-performance-icon"><ChartIcon/></span></div>
          <div className="merchant-success-number"><strong>{loading ? "—" : successRate + "%"}</strong><span>delivered successfully</span></div>
          <div className="merchant-progress"><span style={{width: `${successRate}%`}}/></div>
          <div className="merchant-performance-meta"><span>{stats.delivered} delivered</span><span>{stats.total} total</span></div>
        </section>
        <section className="merchant-quick-panel">
          <span className="merchant-panel-kicker">QUICK ACTIONS</span><h2>What would you like to do?</h2>
          <Link to="/new-shipment"><span className="merchant-quick-icon blue"><Plus size={17}/></span><span><strong>Create shipment</strong><small>Book a new customer delivery</small></span><ArrowRight size={15}/></Link>
          <Link to="/shipments"><span className="merchant-quick-icon violet"><Package size={17}/></span><span><strong>Manage shipments</strong><small>Review your parcel activity</small></span><ArrowRight size={15}/></Link>
          <div className="merchant-quick-disabled"><span className="merchant-quick-icon green"><Wallet size={17}/></span><span><strong>Billing & invoices</strong><small>Billing will be available in the next phase</small></span><span className="merchant-coming-soon">COMING SOON</span></div>
        </section>
      </div>
    </div>
    <p className="merchant-disclaimer"><ArrowDownToLine size={13}/> Shipment metrics reflect parcel records currently available to this merchant account. Billing totals will appear once merchant pricing is configured.</p>
  </div>;
}

function ChartIcon(){ return <span className="merchant-chart-glyph"><span/><span/><span/></span>; }
function Metric({icon:Icon,label,value,note,tone}:{icon:typeof Package;label:string;value:number|string;note:string;tone:string}) {
  return <article className="merchant-metric-card"><span className={`merchant-metric-icon ${tone}`}><Icon size={19}/></span><span className="merchant-metric-label">{label}</span><strong className="merchant-metric-value">{value}</strong><span className="merchant-metric-note">{note}</span></article>;
}
