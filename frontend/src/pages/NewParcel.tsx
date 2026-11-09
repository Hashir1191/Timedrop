import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Package } from "lucide-react";
import { createParcel } from "../api";
import { useAuth } from "../auth";

function todayLocal(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;}

export default function NewParcel() {
 const {token}=useAuth(); const navigate=useNavigate(); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
 const [form,setForm]=useState({tracking_number:"",recipient_name:"",phone:"",address_line:"",city:"",state:"",pincode:"",delivery_instructions:"",preferred_delivery_date:""});
 function update(key:string,value:string){setForm(old=>({...old,[key]:value}));}
 async function submit(e:FormEvent){e.preventDefault();if(!token)return;setBusy(true);setError("");try{const parcel=await createParcel(token,{...form,delivery_instructions:form.delivery_instructions||undefined,preferred_delivery_date:form.preferred_delivery_date||undefined});navigate(`/schedule/${parcel.id}`);}catch(err){setError(err instanceof Error?err.message:"Unable to create parcel.");}finally{setBusy(false);}}
 return <><div className="page-heading"><div><div className="eyebrow">NEW DELIVERY</div><h1>Create a parcel</h1><p>Enter the recipient and destination details to register a parcel.</p></div></div>
 <section className="panel customer-form-panel"><div className="panel-heading"><div><h2><Package size={18}/> Parcel details</h2><p>Use accurate recipient information.</p></div></div>
 {error&&<div className="alert-error">{error}</div>}
 <form className="customer-form" onSubmit={submit}>
  <label>Tracking number<input required minLength={3} maxLength={64} value={form.tracking_number} onChange={e=>update("tracking_number",e.target.value.trim())} placeholder="TD-2026-0001"/></label>
  <label>Recipient name<input required minLength={2} value={form.recipient_name} onChange={e=>update("recipient_name",e.target.value)} placeholder="Recipient's full name"/></label>
  <label>Phone number<input required minLength={10} maxLength={20} value={form.phone} onChange={e=>update("phone",e.target.value)} placeholder="10-digit mobile number"/></label>
  <label className="span-two">Address<input required minLength={5} value={form.address_line} onChange={e=>update("address_line",e.target.value)} placeholder="House / street / locality"/></label>
  <label>City<input required value={form.city} onChange={e=>update("city",e.target.value)} placeholder="City"/></label>
  <label>State<input required value={form.state} onChange={e=>update("state",e.target.value)} placeholder="State"/></label>
  <label>PIN code<input required pattern="[1-9][0-9]{5}" maxLength={6} value={form.pincode} onChange={e=>update("pincode",e.target.value)} placeholder="6-digit PIN code"/></label>
  <label>Preferred delivery date<input type="date" min={todayLocal()} value={form.preferred_delivery_date} onChange={e=>update("preferred_delivery_date",e.target.value)}/></label>
  <label className="span-two">Delivery instructions (optional)<textarea rows={3} maxLength={500} value={form.delivery_instructions} onChange={e=>update("delivery_instructions",e.target.value)} placeholder="Landmark, gate code, or delivery notes"/></label>
  <div className="customer-form-actions"><span>After registration, you can select an available delivery slot.</span><button className="primary-button" disabled={busy}>{busy?"Saving parcel...":"Create and continue"} <ArrowRight size={16}/></button></div>
 </form></section>
 <p className="page-footnote">Only register parcels you are authorized to arrange delivery for. Use synthetic details while testing.</p></>;
}
