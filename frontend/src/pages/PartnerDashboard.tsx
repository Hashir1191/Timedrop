import { useEffect, useState } from "react";
import { CheckCircle2, MapPin, Package, RefreshCw, Truck } from "lucide-react";
import { getMyAssignments, updateAssignmentStatus } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { DeliveryAssignment } from "../types";

export default function PartnerDashboard() {
  const { token } = useAuth();
  const [items,setItems] = useState<DeliveryAssignment[]>([]);
  const [error,setError] = useState("");
  const [busy,setBusy] = useState<number|null>(null);
  async function load(){ if(!token)return; setError(""); try{setItems(await getMyAssignments(token));}catch(e){setError(e instanceof Error?e.message:"Unable to load your assignments.");}}
  useEffect(()=>{void load();},[token]);
  async function update(id:number,status:"accepted"|"out_for_delivery"|"delivered"|"failed"){
    if(!token)return;
    let failure_reason:string|undefined;
    if(status==="failed"){failure_reason=window.prompt("Enter the reason delivery failed:")?.trim();if(!failure_reason||failure_reason.length<3)return;}
    setBusy(id);setError("");
    try{await updateAssignmentStatus(token,id,{status,...(failure_reason?{failure_reason}:{})});await load();}
    catch(e){setError(e instanceof Error?e.message:"Unable to update delivery status.");}
    finally{setBusy(null);}
  }
  const active=items.filter(i=>["assigned","accepted","out_for_delivery"].includes(i.status));
  return <>
    <div className="page-heading"><div><div className="eyebrow">DELIVERY PARTNER PORTAL</div><h1>My deliveries</h1><p>View your assigned parcels and keep delivery progress up to date.</p></div><button className="secondary-button" onClick={()=>void load()}><RefreshCw size={14}/> Refresh</button></div>
    {error&&<div className="alert-error">{error}</div>}
    <div className="stats-grid customer-stats"><div className="stat-card"><div className="stat-icon blue"><Package size={18}/></div><div className="stat-label">Total assigned</div><div className="stat-value">{items.length}</div></div><div className="stat-card"><div className="stat-icon amber"><Truck size={18}/></div><div className="stat-label">In progress</div><div className="stat-value">{active.length}</div></div><div className="stat-card"><div className="stat-icon green"><CheckCircle2 size={18}/></div><div className="stat-label">Delivered</div><div className="stat-value">{items.filter(i=>i.status==="delivered").length}</div></div></div>
    <div className="section-title-row"><h2>Assigned parcels</h2><span className="result-count">{active.length} active</span></div>
    {items.length===0?<div className="panel"><EmptyState title="No deliveries assigned" description="Your new delivery assignments will appear here."/></div>:<div className="booking-list">{items.map(item=><article className="panel partner-job" key={item.id}>
      <div className="partner-job-head"><div><div className="tracking">{item.tracking_number}</div><strong>{item.recipient_name}</strong></div><StatusBadge status={item.status}/></div>
      <div className="partner-address"><MapPin size={16}/><div><strong>{item.address_line}</strong><span>{item.city}, {item.state} · {item.pincode}</span><span>{item.phone}</span></div></div>
      <div className="partner-window">Delivery window: <strong>{new Date(item.delivery_date+"T00:00:00").toLocaleDateString("en-IN")}</strong> · {item.start_time.slice(0,5)}–{item.end_time.slice(0,5)}</div>
      {item.status==="assigned"&&<div className="booking-actions"><button className="primary-button" disabled={busy===item.id} onClick={()=>void update(item.id,"accepted")}>Accept assignment</button><button className="danger-button" disabled={busy===item.id} onClick={()=>void update(item.id,"failed")}>Cannot deliver</button></div>}
      {item.status==="accepted"&&<div className="booking-actions"><button className="primary-button" disabled={busy===item.id} onClick={()=>void update(item.id,"out_for_delivery")}>Start delivery</button></div>}
      {item.status==="out_for_delivery"&&<div className="booking-actions"><button className="primary-button" disabled={busy===item.id} onClick={()=>void update(item.id,"delivered")}>Mark delivered</button><button className="danger-button" disabled={busy===item.id} onClick={()=>void update(item.id,"failed")}>Delivery failed</button></div>}
    </article>)}</div>}
  </>;
}
