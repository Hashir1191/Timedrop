import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, MessageCircle, RefreshCw, Send, Shield, UserCheck } from "lucide-react";
import { getSupportQueue, replyAdminSupportCase, updateSupportCase } from "../api";
import { useAuth } from "../auth";
import type { SupportCase } from "../types";

const statuses=["open","triaged","in_progress","waiting_customer","resolved","closed"];
const priorities=["low","normal","high","urgent"];
const dateLabel=(value:string)=>new Date(value).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"});

export default function SupportInbox(){
 const {token,user}=useAuth();
 const [cases,setCases]=useState<SupportCase[]>([]);
 const [selected,setSelected]=useState<number|null>(null);
 const [statusFilter,setStatusFilter]=useState("");
 const [loading,setLoading]=useState(true);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [reply,setReply]=useState("");
 const [internal,setInternal]=useState(false);
 const active=cases.find(item=>item.id===selected)??null;

 async function load(){
  if(!token)return;
  setLoading(true);setError("");
  try{const rows=await getSupportQueue(token,statusFilter||undefined);setCases(rows);if(selected&&!rows.some(item=>item.id===selected))setSelected(rows[0]?.id??null);else if(!selected&&rows.length)setSelected(rows[0].id);}
  catch(err){setError(err instanceof Error?err.message:"Unable to load the support queue.");}
  finally{setLoading(false);}
 }
 useEffect(()=>{void load();},[token,statusFilter]);

 async function update(data:{status?:string;priority?:string;assigned_to_id?:number|null}){
  if(!token||!active)return;setBusy(true);setError("");
  try{const saved=await updateSupportCase(token,active.id,data);setCases(current=>current.map(item=>item.id===saved.id?saved:item));}
  catch(err){setError(err instanceof Error?err.message:"Unable to update this case.");}
  finally{setBusy(false);}
 }
 async function sendReply(){
  if(!token||!active||!reply.trim())return;setBusy(true);setError("");
  try{const saved=await replyAdminSupportCase(token,active.id,reply.trim(),internal);setCases(current=>current.map(item=>item.id===saved.id?saved:item));setReply("");}
  catch(err){setError(err instanceof Error?err.message:"Unable to send the case reply.");}
  finally{setBusy(false);}
 }

 return <div className="support-page">
  <div className="page-heading"><div><div className="eyebrow">CUSTOMER CARE OPERATIONS</div><h1>Support inbox</h1><p>Investigate parcel claims, resolve delivery exceptions and keep customer communication auditable.</p></div><button className="secondary-button" onClick={()=>void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button></div>
  {error&&<div className="alert-error" role="alert">{error}</div>}
  <div className="support-admin-layout">
   <section className="support-admin-queue"><div className="support-admin-toolbar"><strong>Case queue</strong><select value={statusFilter} onChange={event=>setStatusFilter(event.target.value)}><option value="">All statuses</option>{statuses.map(value=><option key={value} value={value}>{value.replace(/_/g," ")}</option>)}</select></div>
    {loading&&!cases.length?<div className="support-empty">Loading cases…</div>:cases.length===0?<div className="support-empty">No support cases match this filter.</div>:cases.map(item=><button type="button" className={"support-admin-case "+(selected===item.id?"selected":"")} key={item.id} onClick={()=>setSelected(item.id)}><span><strong>{item.case_number}</strong><em className={"support-status "+item.status}>{item.status.replace(/_/g," ")}</em></span><b>{item.subject}</b><small>{item.customer_name}{item.tracking_number?" · "+item.tracking_number:""}</small><span className={"support-priority "+item.priority}>{item.priority} priority</span></button>)}
   </section>
   <section className="support-admin-detail">
    {!active?<div className="support-empty">Select a case to review its details.</div>:<>
     <div className="support-detail-heading"><div><span>{active.case_number}</span><h2>{active.subject}</h2><p>{active.customer_name} · {active.tracking_number||"No linked parcel"} · Opened {dateLabel(active.created_at)}</p></div><AlertCircle size={22}/></div>
     <div className="support-case-description">{active.description}</div>
     <div className="support-admin-controls">
      <label>Status<select value={active.status} disabled={busy} onChange={event=>void update({status:event.target.value})}>{statuses.map(value=><option key={value} value={value}>{value.replace(/_/g," ")}</option>)}</select></label>
      <label>Priority<select value={active.priority} disabled={busy} onChange={event=>void update({priority:event.target.value})}>{priorities.map(value=><option key={value} value={value}>{value}</option>)}</select></label>
      <button className="secondary-button" disabled={busy||active.assigned_to_id===user?.id} onClick={()=>{if(user)void update({assigned_to_id:user.id});}}><UserCheck size={14}/> {active.assigned_to_id===user?.id?"Assigned to you":"Assign to me"}</button>
     </div>
     <div className="support-detail-messages"><h3><MessageCircle size={15}/> Conversation & internal notes</h3>{active.messages.map(message=><article className={"support-message "+(message.is_internal?"internal":"")} key={message.id}><strong>{message.author_name}{message.is_internal?" · Internal note":""}</strong><p>{message.body}</p><small>{dateLabel(message.created_at)}</small></article>)}</div>
     <div className="support-admin-reply"><textarea rows={3} value={reply} onChange={event=>setReply(event.target.value)} placeholder={internal?"Add a private note for the operations team…":"Write a response visible to the customer…"}/><label className="support-internal-toggle"><input type="checkbox" checked={internal} onChange={event=>setInternal(event.target.checked)}/><Shield size={14}/> Internal note (not visible to customer)</label><button className="primary-button" disabled={busy||!reply.trim()} onClick={()=>void sendReply()}><Send size={14}/> {internal?"Save internal note":"Send customer reply"}</button></div>
     {active.status==="resolved"&&<div className="support-resolved-note"><CheckCircle2 size={15}/> This case is marked resolved.</div>}
    </>}
   </section>
  </div>
 </div>;
}
