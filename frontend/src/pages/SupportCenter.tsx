import { FormEvent, useEffect, useState } from "react";
import { LifeBuoy, MessageCircle, PlusCircle, RefreshCw, Send, ShieldAlert } from "lucide-react";
import { createSupportCase, getSupportCases, replySupportCase } from "../api";
import { useAuth } from "../auth";
import type { SupportCase } from "../types";

const categories=[
  {value:"missing_parcel",label:"Parcel missing"},
  {value:"suspected_theft",label:"Suspected theft"},
  {value:"damaged_parcel",label:"Parcel arrived damaged"},
  {value:"delivery_not_received",label:"Marked delivered, not received"},
  {value:"app_bug",label:"App issue or bug"},
  {value:"other",label:"Something else"},
];
const dateLabel=(value:string)=>new Date(value).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"});

export default function SupportCenter(){
  const {token}=useAuth();
  const [cases,setCases]=useState<SupportCase[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  const [category,setCategory]=useState("missing_parcel");
  const [subject,setSubject]=useState("");
  const [description,setDescription]=useState("");
  const [parcelId,setParcelId]=useState("");
  const [busy,setBusy]=useState(false);
  const [reply,setReply]=useState<Record<number,string>>({});

  async function load(){
    if(!token)return;
    setLoading(true);setError("");
    try{setCases(await getSupportCases(token));}
    catch(err){setError(err instanceof Error?err.message:"Unable to load your support cases.");}
    finally{setLoading(false);}
  }
  useEffect(()=>{void load();},[token]);

  async function submit(event:FormEvent){
    event.preventDefault();if(!token)return;
    setBusy(true);setError("");
    try{
      await createSupportCase(token,{category,subject,description,...(parcelId?{parcel_id:Number(parcelId)}:{})});
      setSubject("");setDescription("");setParcelId("");
      await load();
    }catch(err){setError(err instanceof Error?err.message:"Unable to submit your report.");}
    finally{setBusy(false);}
  }
  async function sendReply(caseId:number){
    if(!token||!reply[caseId]?.trim())return;
    setBusy(true);setError("");
    try{await replySupportCase(token,caseId,reply[caseId].trim());setReply(current=>({...current,[caseId]:""}));await load();}
    catch(err){setError(err instanceof Error?err.message:"Unable to send your reply.");}
    finally{setBusy(false);}
  }

  return <div className="support-page">
    <div className="page-heading"><div><div className="eyebrow">HELP WHEN YOU NEED IT</div><h1>Support centre</h1><p>Report a delivery problem, raise a claim or tell us when something in TimeDrop is not working.</p></div><button className="secondary-button" onClick={()=>void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button></div>
    {error&&<div className="alert-error" role="alert">{error}</div>}
    <div className="support-customer-grid">
      <section className="support-form-card">
        <div className="support-card-heading"><span><LifeBuoy size={18}/></span><div><h2>Raise a support request</h2><p>Our team will review your report and reply here.</p></div></div>
        <form onSubmit={submit} className="support-form">
          <label>What do you need help with?<select value={category} onChange={event=>setCategory(event.target.value)}>{categories.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label>Tracking number (optional)<input inputMode="text" value={parcelId} onChange={event=>setParcelId(event.target.value.replace(/\D/g,""))} placeholder="Enter parcel ID if you know it"/></label>
          <label>Subject<input value={subject} onChange={event=>setSubject(event.target.value)} minLength={5} maxLength={160} required placeholder="Briefly describe the issue"/></label>
          <label>Tell us what happened<textarea value={description} onChange={event=>setDescription(event.target.value)} minLength={10} maxLength={5000} required rows={5} placeholder="Include dates, delivery details and anything that will help us investigate."/></label>
          <button className="primary-button" type="submit" disabled={busy}>{busy?"Submitting…":<><Send size={15}/> Submit report</>}</button>
        </form>
        <div className="support-safety-note"><ShieldAlert size={15}/><span>For a suspected theft or missing parcel, report it as soon as possible. TimeDrop will review the delivery history and evidence before making a decision.</span></div>
      </section>
      <section className="support-case-list">
        <div className="support-card-heading"><span><MessageCircle size={18}/></span><div><h2>Your support cases</h2><p>Track updates and reply to our team.</p></div><strong>{cases.length}</strong></div>
        {loading&&!cases.length?<div className="support-empty">Loading your cases…</div>:cases.length===0?<div className="support-empty">You have no support requests yet. If something goes wrong, you can report it here.</div>:cases.map(item=><article className="support-case-card" key={item.id}>
          <div className="support-case-top"><strong>{item.case_number}</strong><span className={"support-status "+item.status}>{item.status.replaceAll("_"," ")}</span></div>
          <h3>{item.subject}</h3>
          <p>{item.description}</p>
          <div className="support-case-meta"><span>{item.category.replaceAll("_"," ")}</span><span>{dateLabel(item.updated_at)}</span>{item.tracking_number&&<span>{item.tracking_number}</span>}</div>
          <div className="support-case-messages">{item.messages.map(message=><div className={"support-message "+(message.author_id===item.customer_id?"own":"")} key={message.id}><strong>{message.author_name}</strong><p>{message.body}</p><small>{dateLabel(message.created_at)}</small></div>)}</div>
          {!["resolved","closed"].includes(item.status)&&<div className="support-reply"><textarea rows={2} value={reply[item.id]||""} onChange={event=>setReply(current=>({...current,[item.id]:event.target.value}))} placeholder="Add a reply or more details…"/><button className="secondary-button" onClick={()=>void sendReply(item.id)} disabled={busy||!reply[item.id]?.trim()}><Send size={14}/> Reply</button></div>}
        </article>)}
      </section>
    </div>
  </div>;
}
