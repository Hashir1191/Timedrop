import { useEffect,useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, CalendarClock } from "lucide-react";
import { getParcels } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { Parcel } from "../types";

export default function CustomerParcels() {
 const {token}=useAuth(); const [parcels,setParcels]=useState<Parcel[]>([]); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
 async function load(){if(!token)return;setLoading(true);setError("");try{setParcels(await getParcels(token));}catch(e){setError(e instanceof Error?e.message:"Unable to load parcels.");}finally{setLoading(false);}}
 useEffect(()=>{void load();},[token]);
 return <><div className="page-heading"><div><div className="eyebrow">PARCEL HISTORY</div><h1>My parcels</h1><p>Every parcel you've registered with TimeDrop.</p></div><button className="secondary-button" onClick={()=>void load()}><RefreshCw size={15}/> Refresh</button></div>
 {error&&<div className="alert-error">{error}</div>}
 <section className="panel list-panel">{loading?<div className="table-loading">Loading parcels...</div>:parcels.length?<div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>CREATED</th><th>STATUS</th><th>DELIVERY</th></tr></thead><tbody>{parcels.map(p=><tr key={p.id}><td className="tracking">{p.tracking_number}</td><td><strong className="cell-strong">{p.recipient_name}</strong><span className="cell-sub">{p.phone}</span></td><td>{p.city}, {p.state}<span className="cell-sub">{p.pincode}</span></td><td>{new Date(p.created_at).toLocaleDateString("en-IN")}</td><td><StatusBadge status={p.status}/></td><td><Link className="text-link" to={`/schedule/${p.id}`}><CalendarClock size={14}/> {p.status==="scheduled"?"Change slot":"Book a slot"}</Link></td></tr>)}</tbody></table></div>:<EmptyState title="No parcels registered" description="Create a parcel to see it listed here."/>}</section></>;
}
