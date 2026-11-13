import { useEffect, useState } from "react";
import { ClipboardCheck, PackageCheck, RefreshCw, ShieldCheck } from "lucide-react";
import { createParcelIntake, getCustodyHistory, getParcelIntakes, releaseParcelCustody } from "../api";
import { useAuth } from "../auth";
import type { CustodyEvent, ParcelIntake } from "../types";
import EmptyState from "../components/EmptyState";

const emptyForm = {
 tracking_number:"", recipient_name:"", phone:"", address_line:"", city:"",
 state:"Uttar Pradesh", pincode:"", customer_email:"", received_from:"",
 package_condition:"intact" as "intact"|"damaged"|"opened", note:"",
};

export default function Intake(){
 const {token}=useAuth();
 const [form,setForm]=useState(emptyForm);
 const [items,setItems]=useState<ParcelIntake[]>([]);
 const [selected,setSelected]=useState<number|null>(null);
 const [history,setHistory]=useState<CustodyEvent[]>([]);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [success,setSuccess]=useState("");
 async function load(){
  if(!token)return;
  try{setError("");setItems(await getParcelIntakes(token));}
  catch(err){setError(err instanceof Error?err.message:"Unable to load intake records.");}
 }
 useEffect(()=>{void load();},[token]);
 function update(key:string,value:string){setForm(old=>({...old,[key]:value}));}
 async function submit(event:React.FormEvent){
  event.preventDefault();if(!token)return;setBusy(true);setError("");setSuccess("");
  try{
   const created=await createParcelIntake(token,{
    ...form,customer_email:form.customer_email.trim()||undefined,note:form.note.trim()||undefined,
   });
   setSuccess(`Parcel ${created.tracking_number} received and recorded in custody.`);
   setForm(emptyForm);await load();await showHistory(created.id);
  }catch(err){setError(err instanceof Error?err.message:"Unable to receive parcel.");}
  finally{setBusy(false);}
 }
 async function showHistory(id:number){
  if(!token)return;setSelected(id);setError("");
  try{setHistory(await getCustodyHistory(token,id));}
  catch(err){setError(err instanceof Error?err.message:"Unable to load custody history.");}
 }
 async function release(id:number){
  if(!token)return;
  if(!window.confirm("Confirm that this parcel is physically handed over to its assigned delivery partner?"))return;
  setBusy(true);setError("");setSuccess("");
  try{await releaseParcelCustody(token,id);setSuccess("Custody handover recorded.");await showHistory(id);await load();}
  catch(err){setError(err instanceof Error?err.message:"Unable to record handover.");}
  finally{setBusy(false);}
 }
 return <>
  <div className="page-heading"><div><div className="eyebrow">WAREHOUSE OPERATIONS</div><h1>Parcel intake & custody</h1><p>Record authorized parcel receipts, inspect package condition, and maintain a handover trail.</p></div><button className="secondary-button" onClick={()=>void load()}><RefreshCw size={15}/> Refresh</button></div>
  <div className="alert-info"><ShieldCheck size={17}/> Only record parcels TimeDrop is explicitly authorized to receive and handle. Use synthetic details while testing.</div>
  {error&&<div className="alert-error">{error}</div>}
  {success&&<div className="alert-success">{success}</div>}
  <section className="panel customer-form-panel">
   <div className="panel-heading"><div><h2><PackageCheck size={18}/> Receive a parcel</h2><p>Register the parcel and create its first immutable custody event.</p></div></div>
   <form className="customer-form" onSubmit={submit}>
    <label>Tracking number<input required minLength={3} maxLength={64} value={form.tracking_number} onChange={e=>update("tracking_number",e.target.value)} placeholder="TD-2026-0001"/></label>
    <label>Recipient name<input required minLength={2} value={form.recipient_name} onChange={e=>update("recipient_name",e.target.value)} placeholder="Full name"/></label>
    <label>Recipient phone<input required minLength={10} maxLength={20} value={form.phone} onChange={e=>update("phone",e.target.value)} placeholder="Mobile number"/></label>
    <label>Customer account email (optional)<input type="email" value={form.customer_email} onChange={e=>update("customer_email",e.target.value)} placeholder="Existing customer account"/></label>
    <label className="span-two">Delivery address<input required minLength={5} value={form.address_line} onChange={e=>update("address_line",e.target.value)} placeholder="House, street and locality"/></label>
    <label>City<input required value={form.city} onChange={e=>update("city",e.target.value)}/></label>
    <label>State<input required value={form.state} onChange={e=>update("state",e.target.value)}/></label>
    <label>PIN code<input required pattern="[1-9][0-9]{5}" maxLength={6} value={form.pincode} onChange={e=>update("pincode",e.target.value)} placeholder="6-digit PIN"/></label>
    <label>Received from<input required minLength={2} value={form.received_from} onChange={e=>update("received_from",e.target.value)} placeholder="Authorized carrier / sender"/></label>
    <label>Package condition<select value={form.package_condition} onChange={e=>update("package_condition",e.target.value)}><option value="intact">Intact / sealed</option><option value="damaged">Damaged</option><option value="opened">Opened / seal broken</option></select></label>
    <label className="span-two">Intake notes (optional)<textarea rows={3} maxLength={500} value={form.note} onChange={e=>update("note",e.target.value)} placeholder="Visible damage, seal condition, receipt reference..."/></label>
    <div className="customer-form-actions"><span>Receipt is timestamped and attributed to the signed-in operations user.</span><button className="primary-button" disabled={busy}>{busy?"Saving...":"Confirm parcel receipt"} <ClipboardCheck size={16}/></button></div>
   </form>
  </section>
  <section className="panel list-panel">
   <div className="panel-heading"><div><h2>Recent intake records</h2><p>Latest 100 parcels received through operations.</p></div></div>
   {items.length?<div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>CONDITION</th><th>RECEIVED</th><th>HISTORY</th></tr></thead><tbody>{items.map(item=><tr key={item.id}><td className="tracking">{item.tracking_number}</td><td>{item.recipient_name}<span className="cell-sub">{item.customer_email||"No linked customer"}</span></td><td>{item.city}, {item.state}<span className="cell-sub">{item.pincode}</span></td><td><span className={`status-pill ${item.package_condition}`}>{item.package_condition}</span></td><td>{new Date(item.received_at).toLocaleString("en-IN")}</td><td><button className="text-link" onClick={()=>void showHistory(item.id)}>View history</button></td></tr>)}</tbody></table></div>:<EmptyState title="No parcels received yet" description="New operations intake records will appear here."/>}
  </section>
  {selected!==null&&<section className="panel list-panel"><div className="panel-heading"><div><h2>Custody history · parcel #{selected}</h2><p>Events are appended; previous records are not edited.</p></div><button className="secondary-button" onClick={()=>{setSelected(null);setHistory([]);}}>Close</button></div>
   <div className="timeline">{history.map(event=><div className="timeline-item" key={event.id}><div className="timeline-dot"/><div><strong>{event.event_type==="received"?"Received into custody":event.event_type==="released"?"Released to delivery partner":event.event_type}</strong><span className="cell-sub">{new Date(event.created_at).toLocaleString("en-IN")}</span>{event.received_from&&<p>Received from: {event.received_from}</p>}{event.package_condition&&<p>Condition: {event.package_condition}</p>}{event.handed_to&&<p>Handed to: {event.handed_to}</p>}{event.note&&<p>{event.note}</p>}</div></div>)}</div>
   {history.length===1&&history[0].event_type==="received"&&<div className="customer-form-actions"><span>Release becomes available after a delivery partner is assigned.</span><button className="secondary-button" disabled={busy} onClick={()=>void release(selected)}>Record partner handover</button></div>}
  </section>}
 </>;
}
