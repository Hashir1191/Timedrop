import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, ArrowRight, Building2, LockKeyhole } from "lucide-react";
import BrandLogo from "../components/BrandLogo";
import { submitMerchantApplication } from "../api";

export default function MerchantApply(){
 const [form,setForm]=useState({email:"",full_name:"",password:"",phone_number:"",business_name:"",business_type:"",pickup_address:"",pickup_city:"",pickup_state:"",pickup_pincode:""});
 const [error,setError]=useState("");const [busy,setBusy]=useState(false);const [submitted,setSubmitted]=useState(false);
 const update=(key:keyof typeof form,value:string)=>setForm(current=>({...current,[key]:value}));
 async function submit(event:FormEvent){
  event.preventDefault();setBusy(true);setError("");
  try{await submitMerchantApplication(form);setSubmitted(true);}
  catch(e){setError(e instanceof Error?e.message:"Unable to submit your application.");}
  finally{setBusy(false);}
 }
 return <div className="merchant-apply-screen"><div className="merchant-apply-panel">
  <Link to="/" className="merchant-apply-brand"><BrandLogo className="brand-logo"/></Link>
  <Link to="/login" className="merchant-apply-back"><ArrowLeft size={14}/> Back to sign in</Link>
  {submitted?<div className="merchant-apply-success"><span><Building2 size={24}/></span><div className="eyebrow">APPLICATION RECEIVED</div><h1>Thank you for applying.</h1><p>Your business application is now pending review by the TimeDrop operations team. You will be able to sign in after it is approved.</p><Link to="/" className="primary-button">Return to home <ArrowRight size={15}/></Link></div>:<>
   <div className="eyebrow">JOIN THE TIMEDROP NETWORK</div><h1>Apply as a merchant</h1><p className="merchant-apply-intro">Share your business and pickup details. Our operations team will review your application before activating merchant access.</p>
   <form onSubmit={submit} className="merchant-apply-form">
    <h2>Account details</h2>
    <div className="merchant-apply-fields"><Field label="Contact person" value={form.full_name} onChange={v=>update("full_name",v)} required/><Field label="Business email" type="email" value={form.email} onChange={v=>update("email",v)} required/><Field label="Phone number" value={form.phone_number} onChange={v=>update("phone_number",v)} required/><Field label="Password (12+ characters)" type="password" value={form.password} onChange={v=>update("password",v)} required minLength={12}/></div>
    <h2>Business details</h2><div className="merchant-apply-fields"><Field label="Business name" value={form.business_name} onChange={v=>update("business_name",v)} required/><Field label="Business type" placeholder="Retail, ecommerce, pharmacy…" value={form.business_type} onChange={v=>update("business_type",v)} required/></div>
    <h2>Pickup address</h2><div className="merchant-apply-fields"><Field label="Address" value={form.pickup_address} onChange={v=>update("pickup_address",v)} required/><Field label="City" value={form.pickup_city} onChange={v=>update("pickup_city",v)} required/><Field label="State" value={form.pickup_state} onChange={v=>update("pickup_state",v)} required/><Field label="PIN code" value={form.pickup_pincode} onChange={v=>update("pickup_pincode",v)} required pattern="[1-9][0-9]{5}" maxLength={6}/></div>
    {error&&<div className="form-error" role="alert">{error}</div>}
    <button className="primary-button" disabled={busy}>{busy?"Submitting…":"Submit application"} <ArrowRight size={15}/></button>
   </form><div className="merchant-apply-security"><LockKeyhole size={14}/> Your password is stored as a secure hash. Merchant access stays disabled until approval.</div>
  </>}
 </div></div>;
}
function Field({label,value,onChange,type="text",...props}:{label:string;value:string;onChange:(value:string)=>void;type?:"text"|"email"|"password";required?:boolean;minLength?:number;maxLength?:number;pattern?:string;placeholder?:string}){
 const id=label.toLowerCase().replace(/[^a-z0-9]+/g,"-");
 return <label className="merchant-apply-field" htmlFor={id}>{label}<input id={id} type={type} value={value} onChange={e=>onChange(e.target.value)} {...props}/></label>;
}
