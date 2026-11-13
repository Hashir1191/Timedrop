import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CalendarClock, CheckCircle2, Clock3, ShieldCheck } from "lucide-react";
import { bookParcel, cancelBooking, getParcelBooking, getParcels, getSlots, rescheduleBooking } from "../api";
import { useAuth } from "../auth";
import type { Booking, DeliverySlot, Parcel } from "../types";
import StatusBadge from "../components/StatusBadge";

function dateLocal(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;}
function formatDate(value:string){return new Date(value+"T00:00:00").toLocaleDateString("en-IN",{weekday:"short",day:"numeric",month:"long",year:"numeric"});}

export default function ScheduleParcel(){
 const {parcelId}=useParams();const id=Number(parcelId);const {token}=useAuth();
 const [parcel,setParcel]=useState<Parcel|null>(null);const [booking,setBooking]=useState<Booking|null>(null);const [slots,setSlots]=useState<DeliverySlot[]>([]);
 const [date,setDate]=useState(dateLocal());const [selected,setSelected]=useState("");const [error,setError]=useState("");const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);const [loadingSlots,setLoadingSlots]=useState(true);

 async function load(){
  if(!token||!id)return;setLoading(true);setError("");
  try{
   const ps=await getParcels(token);const found=ps.find(item=>item.id===id);
   if(!found)throw new Error("Parcel not found.");
   setParcel(found);
   try{setBooking(await getParcelBooking(token,id));}
   catch(err){if(err instanceof Error&&"status" in err&&(err as {status:number}).status===404)setBooking(null);else throw err;}
  }catch(err){setError(err instanceof Error?err.message:"Unable to load parcel.");}
  finally{setLoading(false);}
 }
 async function loadSlots(day:string){
  if(!token)return;setLoadingSlots(true);setSelected("");
  try{setSlots(await getSlots(token,day));}
  catch(err){setSlots([]);setError(err instanceof Error?err.message:"Unable to load delivery slots.");}
  finally{setLoadingSlots(false);}
 }
 useEffect(()=>{void load();},[token,id]);
 useEffect(()=>{void loadSlots(date);},[token,date]);

 async function submit(){
  if(!token||!selected)return;setBusy(true);setError("");setMessage("");
  try{
   const updated=booking?await rescheduleBooking(token,id,Number(selected)):await bookParcel(token,id,Number(selected));
   setBooking(updated);setMessage(booking?"Your delivery slot has been changed.":"Your delivery slot is confirmed.");
   await loadSlots(date);
  }catch(err){setError(err instanceof Error?err.message:"Unable to save booking.");}
  finally{setBusy(false);}
 }
 async function cancel(){
  if(!token||!booking||!window.confirm("Cancel this delivery booking?"))return;
  setBusy(true);setError("");setMessage("");
  try{await cancelBooking(token,id);setBooking(null);setParcel(current=>current?{...current,status:"registered"}:current);setMessage("Your booking has been cancelled.");await loadSlots(date);}
  catch(err){setError(err instanceof Error?err.message:"Unable to cancel booking.");}
  finally{setBusy(false);}
 }

 const selectedSlot=useMemo(()=>slots.find(slot=>String(slot.id)===selected)??null,[slots,selected]);
 const terminal=["delivered","failed","cancelled"].includes(parcel?.status??"");
 if(loading)return <div className="customer-schedule-workspace"><div className="customer-schedule-skeleton"/><div className="customer-schedule-skeleton"/></div>;
 if(!parcel)return <div className="customer-schedule-workspace"><div className="alert-error">{error||"Parcel not found."}</div><Link to="/my-parcels" className="text-link"><ArrowLeft size={14}/> Back to parcels</Link></div>;

 return <div className="customer-schedule-workspace">
  <div className="page-heading customer-schedule-heading"><div><div className="eyebrow">DELIVERY SCHEDULING · STEP 2 OF 2</div><h1>{booking?"Manage your delivery":"Choose a delivery time"}</h1><p>Confirm a suitable delivery window for <strong>{parcel.tracking_number}</strong>.</p></div><Link to="/my-parcels" className="secondary-button"><ArrowLeft size={15}/> My parcels</Link></div>
  <div className="customer-schedule-progress"><span className="done"><CheckCircle2 size={14}/> Parcel details</span><i/><span className="current"><CalendarClock size={14}/> Delivery slot</span></div>
  {error&&<div className="alert-error">{error}</div>}{message&&<div className="alert-success"><CheckCircle2 size={15}/>{message}</div>}

  <section className="customer-schedule-parcel">
   <div className="customer-schedule-parcel-main"><span className="customer-schedule-package-icon"><CalendarClock size={21}/></span><div><span>PARCEL / RECIPIENT</span><strong>{parcel.tracking_number}</strong><small>{parcel.recipient_name}</small></div><StatusBadge status={parcel.status}/></div>
   <div className="customer-schedule-address"><span>DELIVERY DESTINATION</span><strong>{parcel.address_line}</strong><small>{parcel.city}, {parcel.state} · {parcel.pincode}</small></div>
   {booking&&<div className="customer-confirmed-booking"><span className="customer-confirmed-icon"><CheckCircle2 size={17}/></span><div><small>CONFIRMED DELIVERY WINDOW</small><strong>{formatDate(booking.delivery_date)}</strong><span>{booking.start_time.slice(0,5)} – {booking.end_time.slice(0,5)}</span></div><button type="button" className="customer-cancel-booking" disabled={busy} onClick={()=>void cancel()}>Cancel booking</button></div>}
  </section>

  <section className="customer-slot-section">
   <div className="customer-slot-section-heading"><div><span className="customer-aside-kicker">AVAILABLE DELIVERY WINDOWS</span><h2>{booking?"Choose a new time":"Select your preferred time"}</h2><p>Only slots with remaining capacity can be selected.</p></div><span className="customer-slot-legend"><i/> Available</span></div>
   <div className="customer-slot-date-panel"><label htmlFor="customer-delivery-date"><CalendarClock size={16}/> Select delivery date</label><input id="customer-delivery-date" type="date" min={dateLocal()} value={date} onChange={event=>setDate(event.target.value)}/><span>{formatDate(date)}</span></div>
   {loadingSlots?<div className="customer-slot-loading">{[1,2,3,4].map(item=><div key={item}/>)}</div>:
    slots.filter(slot=>slot.remaining_capacity>0).length?<div className="customer-slot-grid">{slots.map(slot=><button type="button" key={slot.id} disabled={slot.remaining_capacity<=0||busy||terminal} onClick={()=>setSelected(String(slot.id))} className={`customer-slot-option ${selected===String(slot.id)?"selected":""} ${slot.remaining_capacity<=0?"unavailable":""}`}>
      <span className="customer-slot-option-icon"><Clock3 size={16}/></span><strong>{slot.start_time.slice(0,5)} – {slot.end_time.slice(0,5)}</strong><small>{slot.remaining_capacity>0?`${slot.remaining_capacity} spaces remaining`:"Fully booked"}</small>{selected===String(slot.id)&&<span className="customer-slot-selected"><CheckCircle2 size={14}/></span>}
     </button>)}</div>:<div className="customer-no-slots"><CalendarClock size={24}/><strong>No available slots for this date</strong><span>Choose another date to see more delivery windows.</span></div>
   }
   {selectedSlot&&<div className="customer-selected-summary"><span><CheckCircle2 size={16}/> Selected delivery window</span><strong>{formatDate(date)} · {selectedSlot.start_time.slice(0,5)} – {selectedSlot.end_time.slice(0,5)}</strong></div>}
   <div className="customer-schedule-submit"><div><ShieldCheck size={17}/><span>Your booking is confirmed only after you select and submit an available slot.</span></div><button className="primary-button" disabled={!selected||busy||terminal} onClick={()=>void submit()}>{busy?"Saving booking…":booking?"Confirm reschedule":"Confirm delivery slot"} <CheckCircle2 size={15}/></button></div>
   {terminal&&<p className="page-footnote">This parcel cannot be scheduled because its status is {parcel.status}.</p>}
  </section>
 </div>;
}
