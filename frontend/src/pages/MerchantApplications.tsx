import { useEffect, useState } from "react";
import { Building2, CheckCircle2, Clock3, RefreshCw, ShieldAlert, XCircle } from "lucide-react";
import { useAuth } from "../auth";
import { decideMerchantApplication, getMerchantApplications, type MerchantApplication } from "../api";

const dateLabel=(value:string)=>new Date(value).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"});
export default function MerchantApplications(){
 const {token}=useAuth();
 const [rows,setRows]=useState<MerchantApplication[]>([]);
 const [filter,setFilter]=useState("pending");
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState<number|null>(null);
 const [error,setError]=useState("");
 const [notice,setNotice]=useState("");
 async function load(){
  if(!token)return;setLoading(true);setError("");
  try{setRows(await getMerchantApplications(token,filter));}
  catch(e){setError(e instanceof Error?e.message:"Unable to load merchant applications.");}
  finally{setLoading(false);}
 }
 useEffect(()=>{void load();},[token,filter]);
 async function decide(id:number,action:"approve"|"reject"|"suspend"|"reactivate"){
  if(!token)return;setBusy(id);setError("");setNotice("");
  try{await decideMerchantApplication(token,id,action);setNotice("Merchant application updated.");await load();}
  catch(e){setError(e instanceof Error?e.message:"Unable to update this application.");}
  finally{setBusy(null);}
 }
 return <div className="merchant-review-page">
  <div className="page-heading"><div><div className="eyebrow">BUSINESS ACCOUNT CONTROL</div><h1>Merchant applications</h1><p>Review business details and control access to the merchant workspace.</p></div><button className="secondary-button" onClick={()=>void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button></div>
  <div className="merchant-review-toolbar"><label>Application status <select value={filter} onChange={e=>setFilter(e.target.value)}><option value="pending">Pending review</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="suspended">Suspended</option></select></label><span><Building2 size={15}/> {rows.length} applications</span></div>
  {error&&<div className="alert-error" role="alert">{error}</div>}{notice&&<div className="merchant-review-notice" role="status">{notice}</div>}
  {loading?<div className="merchant-review-empty">Loading applications…</div>:rows.length===0?<div className="merchant-review-empty"><Building2 size={26}/><strong>No applications found</strong><span>Applications matching this status will appear here.</span></div>:
   <div className="merchant-review-list">{rows.map(item=><article className="merchant-review-card" key={item.id}>
    <div className="merchant-review-card-head"><div><span className="merchant-review-id">APPLICATION #{item.id}</span><h2>{item.business_name}</h2><p>{item.business_type}</p></div><span className={"merchant-review-status "+item.status}>{item.status}</span></div>
    <div className="merchant-review-grid"><div><small>Contact person</small><strong>{item.contact_name}</strong></div><div><small>Email</small><strong>{item.email}</strong></div><div><small>Phone</small><strong>{item.phone_number}</strong></div><div><small>Pickup location</small><strong>{item.pickup_address}, {item.pickup_city}, {item.pickup_state} – {item.pickup_pincode}</strong></div></div>
    <div className="merchant-review-card-foot"><span><Clock3 size={13}/> Submitted {dateLabel(item.created_at)}</span>{item.review_note&&<em>Review note: {item.review_note}</em>}
     <div className="merchant-review-actions">{item.status==="pending"?<><button className="primary-button" disabled={busy===item.id} onClick={()=>void decide(item.id,"approve")}><CheckCircle2 size={14}/> Approve merchant</button><button className="secondary-button danger" disabled={busy===item.id} onClick={()=>void decide(item.id,"reject")}><XCircle size={14}/> Reject</button></>:item.status==="approved"?<button className="secondary-button danger" disabled={busy===item.id} onClick={()=>void decide(item.id,"suspend")}><ShieldAlert size={14}/> Suspend access</button>:item.status==="suspended"?<button className="primary-button" disabled={busy===item.id} onClick={()=>void decide(item.id,"reactivate")}><CheckCircle2 size={14}/> Reactivate</button>:null}</div>
    </div>
   </article>)}</div>}
 </div>;
}
