import { useEffect,useState } from "react";
import { Link,useParams } from "react-router-dom";
import { ArrowLeft,CalendarClock,CheckCircle2,RefreshCw } from "lucide-react";
import { bookParcel,cancelBooking,getParcelBooking,getParcels,getSlots,rescheduleBooking } from "../api";
import { useAuth } from "../auth";
import type { Booking,DeliverySlot,Parcel } from "../types";
import StatusBadge from "../components/StatusBadge";

function dateLocal(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;}
export default function ScheduleParcel(){
 const {parcelId}=useParams();const id=Number(parcelId);const {token}=useAuth();
 const [parcel,setParcel]=useState<Parcel|null>(null);const [booking,setBooking]=useState<Booking|null>(null);const [slots,setSlots]=useState<DeliverySlot[]>([]);
 const [date,setDate]=useState(dateLocal());const [selected,setSelected]=useState("");const [error,setError]=useState("");const [message,setMessage]=useState("");const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);
 async function load(){if(!token||!id)return;setLoading(true);setError("");try{const ps=await getParcels(token);const p=ps.find(x=>x.id===id);if(!p)throw new Error("Parcel not found.");setParcel(p);try{setBooking(await getParcelBooking(token,id));}catch(e){if(e instanceof Error&&"status" in e&&(e as {status:number}).status===404)setBooking(null);else throw e;} }catch(e){setError(e instanceof Error?e.message:"Unable to load parcel.");}finally{setLoading(false);}}
 async function loadSlots(day:string){if(!token)return;setError("");setSelected("");try{setSlots(await getSlots(token,day));}catch(e){setSlots([]);setError(e instanceof Error?e.message:"Unable to load delivery slots.");}}
 useEffect(()=>{void load();},[token,id]);
 useEffect(()=>{void loadSlots(date);},[token,date]);
 async function submit(){if(!token||!selected)return;setBusy(true);setError("");setMessage("");try{const updated=booking?await rescheduleBooking(token,id,Number(selected)):await bookParcel(token,id,Number(selected));setBooking(updated);setMessage(booking?"Your delivery slot has been changed.":"Your delivery slot is confirmed.");await loadSlots(date);}catch(e){setError(e instanceof Error?e.message:"Unable to save booking.");}finally{setBusy(false);}}
 async function cancel(){if(!token||!booking||!window.confirm("Cancel this delivery booking?"))return;setBusy(true);setError("");setMessage("");try{await cancelBooking(token,id);setBooking(null);setMessage("Your booking has been cancelled.");await loadSlots(date);}catch(e){setError(e instanceof Error?e.message:"Unable to cancel booking.");}finally{setBusy(false);}}
 if(loading)return <div className="table-loading">Loading parcel...</div>;
 if(!parcel)return <><div className="alert-error">{error||"Parcel not found."}</div><Link to="/my-parcels" className="text-link"><ArrowLeft size={14}/> Back to parcels</Link></>;
 return <><div className="page-heading"><div><div className="eyebrow">DELIVERY SCHEDULING</div><h1>Choose a delivery time</h1><p>Parcel <strong>{parcel.tracking_number}</strong> · {parcel.recipient_name}</p></div><Link to="/my-parcels" className="secondary-button"><ArrowLeft size={15}/> My parcels</Link></div>
 {error&&<div className="alert-error">{error}</div>}{message&&<div className="alert-success">{message}</div>}
 <section className="panel schedule-current"><div><div className="eyebrow">PARCEL STATUS</div><h2>{parcel.tracking_number}</h2><p>{parcel.address_line}, {parcel.city}, {parcel.state} {parcel.pincode}</p><StatusBadge status={parcel.status}/></div>
 <div className="current-booking">{booking?<><span>YOUR CONFIRMED SLOT</span><strong>{new Date(booking.delivery_date+"T00:00:00").toLocaleDateString("en-IN",{day:"numeric",month:"long",year:"numeric"})}</strong><strong>{booking.start_time.slice(0,5)} – {booking.end_time.slice(0,5)}</strong><button className="secondary-button cancel-booking" onClick={()=>void cancel()} disabled={busy}>Cancel booking</button></>:<><span>NO ACTIVE BOOKING</span><strong>Choose an available time below</strong></>}</div></section>
 <section className="panel slot-picker-panel"><div className="panel-heading"><div><h2><CalendarClock size={18}/> Available delivery slots</h2><p>Select a date to see the windows operations has opened.</p></div><RefreshCw size={17} className="muted-icon"/></div>
 <label className="slot-date-field">Delivery date<input type="date" min={dateLocal()} value={date} onChange={e=>setDate(e.target.value)}/></label>
 {slots.length?<div className="customer-slot-grid">{slots.map(s=><button type="button" key={s.id} disabled={s.remaining_capacity<=0||busy} onClick={()=>setSelected(String(s.id))} className={`customer-slot ${selected===String(s.id)?"selected":""} ${s.remaining_capacity<=0?"unavailable":""}`}><strong>{s.start_time.slice(0,5)} – {s.end_time.slice(0,5)}</strong><span>{s.remaining_capacity>0?`${s.remaining_capacity} spaces left`:"Fully booked"}</span></button>)}</div>:<div className="empty-state"><div className="empty-icon"><CalendarClock size={20}/></div><strong>No slots available for this date</strong><span>Try another date or check again later.</span></div>}
 <div className="schedule-submit-row"><span>{selected?"A slot is selected. Confirm to save your booking.":"Select one available slot to continue."}</span><button className="primary-button" disabled={!selected||busy||["delivered","cancelled"].includes(parcel.status)} onClick={()=>void submit()}>{busy?"Saving...":booking?"Confirm reschedule":"Confirm booking"}</button></div>
 {["delivered","cancelled"].includes(parcel.status)&&<p className="page-footnote">This parcel cannot be scheduled because its status is {parcel.status}.</p>}
 </section></>;
}
