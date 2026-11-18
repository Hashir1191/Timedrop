import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, CalendarClock, CheckCircle2, MapPin, Package, ShieldCheck } from "lucide-react";
import { ApiError, checkPincodeServiceability, createParcel } from "../api";
import { useAuth } from "../auth";

function todayLocal(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;}

export default function NewParcel() {
 const {token}=useAuth(); const navigate=useNavigate(); const [busy,setBusy]=useState(false); const [error,setError]=useState(""); const [trackingError,setTrackingError]=useState("");
 const [coverage,setCoverage]=useState<import("../types").ServiceabilityCheck|null>(null); const [checkingCoverage,setCheckingCoverage]=useState(false); const [coverageError,setCoverageError]=useState("");
 const coverageRequestId=useRef(0); const currentPincode=useRef("");
 useEffect(()=>()=>{coverageRequestId.current+=1;},[]);
 const [form,setForm]=useState({tracking_number:"",recipient_name:"",phone:"",address_line:"",city:"",state:"",pincode:"",delivery_instructions:"",preferred_delivery_date:""});
 function update(key:string,value:string){setForm(old=>({...old,[key]:value}));if(key==="tracking_number")setTrackingError("");if(key==="pincode"){currentPincode.current=value;coverageRequestId.current+=1;setCoverage(null);setCoverageError("");setCheckingCoverage(false);}}
 async function checkCoverage(pincode=form.pincode):Promise<boolean|null>{
  if(!token||! /^[1-9][0-9]{5}$/.test(pincode))return null;
  if(coverage?.pincode===pincode)return coverage.serviceable;
  const requestId=++coverageRequestId.current;
  setCheckingCoverage(true);setCoverageError("");
  try{
   const result=await checkPincodeServiceability(token,pincode);
   if(requestId!==coverageRequestId.current||currentPincode.current!==pincode)return null;
   if(result.pincode!==pincode){setCoverageError("The serviceability response did not match the entered PIN code. Please retry.");return null;}
   setCoverage(result);return result.serviceable;
  }catch(err){
   if(requestId===coverageRequestId.current&&currentPincode.current===pincode)setCoverageError(err instanceof Error?err.message:"Unable to check delivery coverage.");
   return null;
  }finally{if(requestId===coverageRequestId.current)setCheckingCoverage(false);}
 }
 async function submit(e:FormEvent){e.preventDefault();if(!token||busy)return;const submittedPincode=form.pincode;setBusy(true);setError("");try{
  const isServiceable=await checkCoverage(submittedPincode);
  if(isServiceable===null)return;
  if(currentPincode.current!==submittedPincode)return;
  if(!isServiceable){setError("This PIN code is not currently covered by TimeDrop. Please use a supported delivery area.");return;}
  const parcel=await createParcel(token,{...form,pincode:submittedPincode,delivery_instructions:form.delivery_instructions||undefined,preferred_delivery_date:form.preferred_delivery_date||undefined});navigate(`/schedule/${parcel.id}`);
 }catch(err){if(err instanceof ApiError&&err.status===409&&/tracking number/i.test(err.message)){setTrackingError(err.message);setError("This tracking number is already registered. Enter a unique parcel reference.");}else{setError(err instanceof Error?err.message:"Unable to create parcel.");}}finally{setBusy(false);}}
 return <div className="customer-booking-workspace">
  <div className="page-heading customer-booking-heading"><div><div className="eyebrow">NEW DELIVERY · STEP 1 OF 2</div><h1>Create a parcel</h1><p>Start with the recipient and destination. You can choose a delivery time next.</p></div><span className="customer-booking-step"><span>01</span> Parcel details <i/> <span>02</span> Delivery slot</span></div>
  {error&&<div className="alert-error">{error}</div>}
  <div className="customer-booking-layout">
   <section className="panel customer-form-panel customer-create-form-panel">
    <div className="panel-heading"><div><span className="customer-form-kicker">PARCEL INFORMATION</span><h2><Package size={18}/> Delivery details</h2><p>Make sure the tracking number and recipient details are accurate.</p></div><span className="customer-form-step-mark">01 / 02</span></div>
    <form className="customer-form customer-create-form" onSubmit={submit}>
     <fieldset className="customer-create-fields" disabled={busy}>
     <div className="customer-form-section-label"><span>01</span><div><strong>Parcel reference</strong><small>Identify the shipment.</small></div></div>
     <label>Tracking number<input required minLength={3} maxLength={64} value={form.tracking_number} onChange={e=>update("tracking_number",e.target.value.trim())} aria-invalid={Boolean(trackingError)} aria-describedby={trackingError?"tracking-number-feedback":undefined} placeholder="TD-2026-0001"/>{trackingError&&<small id="tracking-number-feedback" className="tracking-number-error" role="alert">{trackingError}</small>}</label>
     <div className="customer-form-section-label"><span>02</span><div><strong>Recipient information</strong><small>Who will receive this parcel?</small></div></div>
     <label>Recipient full name<input required minLength={2} value={form.recipient_name} onChange={e=>update("recipient_name",e.target.value)} placeholder="Recipient's full name"/></label>
     <label>Contact phone<input required minLength={10} maxLength={20} value={form.phone} onChange={e=>update("phone",e.target.value)} placeholder="10-digit mobile number"/></label>
     <div className="customer-form-section-label"><span>03</span><div><strong>Delivery destination</strong><small>Where should the parcel arrive?</small></div></div>
     <label className="span-two">Street address<input required minLength={5} value={form.address_line} onChange={e=>update("address_line",e.target.value)} placeholder="House number, street and locality"/></label>
     <label>City<input required value={form.city} onChange={e=>update("city",e.target.value)} placeholder="City"/></label>
     <label>State<input required value={form.state} onChange={e=>update("state",e.target.value)} placeholder="State"/></label>
     <label>PIN code<input required pattern="[1-9][0-9]{5}" maxLength={6} value={form.pincode} onChange={e=>update("pincode",e.target.value.replace(/\D/g,"").slice(0,6))} onBlur={()=>void checkCoverage()} aria-describedby="pincode-feedback" placeholder="6-digit PIN code"/><small id="pincode-feedback" className="serviceability-hint" aria-live="polite">{checkingCoverage?"Checking delivery coverage…":coverage?.pincode===form.pincode?(coverage.serviceable?`Available in ${coverage.city}, ${coverage.state}`:coverage.message):coverageError||"Enter a valid 6-digit PIN code to check delivery coverage."}</small>{coverageError&&<button type="button" className="secondary-button serviceability-retry" onClick={()=>void checkCoverage()} disabled={checkingCoverage||busy}>Retry coverage check</button>}</label>
     <label>Preferred delivery date<input type="date" min={todayLocal()} value={form.preferred_delivery_date} onChange={e=>update("preferred_delivery_date",e.target.value)}/></label>
     <label className="span-two">Delivery instructions <span className="customer-optional-label">OPTIONAL</span><textarea rows={3} maxLength={500} value={form.delivery_instructions} onChange={e=>update("delivery_instructions",e.target.value)} placeholder="Landmark, gate code or helpful delivery notes"/></label>
     </fieldset>
     <div className="customer-form-actions"><span>Next, you'll choose an available delivery slot.</span><button className="primary-button" disabled={busy}>{busy?"Creating parcel…":"Continue to delivery slot"} <ArrowRight size={16}/></button></div>
    </form>
   </section>
   <aside className="customer-booking-aside">
    <div className="customer-booking-aside-card customer-booking-progress">
     <span className="customer-aside-kicker">YOUR CHECKLIST</span><h3>Two simple steps</h3>
     <div className="customer-progress-step active"><span><CheckCircle2 size={15}/></span><div><strong>Parcel details</strong><small>Recipient and destination</small></div><b>01</b></div>
     <div className="customer-progress-line"/>
     <div className="customer-progress-step"><span><CalendarClock size={15}/></span><div><strong>Choose delivery slot</strong><small>Select an available window</small></div><b>02</b></div>
    </div>
    <div className="customer-booking-aside-card">
     <span className="customer-aside-icon"><MapPin size={18}/></span><h3>Accurate addresses help</h3><p>Include the house number, street, locality and correct PIN code so operations can plan the delivery.</p>
    </div>
    <div className="customer-booking-aside-card customer-booking-security">
     <span className="customer-aside-icon"><ShieldCheck size={18}/></span><h3>Your details stay protected</h3><p>Recipient contact details are used for parcel coordination and delivery updates.</p>
    </div>
   </aside>
  </div>
  <p className="page-footnote">Only register parcels you are authorized to arrange delivery for. Use synthetic details while testing.</p>
 </div>;
}
