import { useEffect, useMemo, useRef, useState } from "react";
import { Download, FileSpreadsheet, Filter, Plus, RefreshCw, Search, UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { createMerchantParcelsBulk, getParcels } from "../api";
import { useAuth } from "../auth";
import StatusBadge from "../components/StatusBadge";
import type { Parcel, ParcelCreate } from "../types";

const HEADERS=["tracking_number","recipient_name","phone","address_line","city","state","pincode","delivery_instructions","preferred_delivery_date"];
const TEMPLATE=[HEADERS.join(","), "TD-ORDER-001,Ananya Sharma,9876543210,\"12 Civil Lines\",Prayagraj,Uttar Pradesh,211001,\"Call on arrival\",2026-12-01"].join("\n");

function parseCsv(text:string):string[][] {
 const rows:string[][]=[];let row:string[]=[];let cell="";let quoted=false;
 for(let i=0;i<text.length;i++){const ch=text[i];
  if(ch==='"'&&quoted&&text[i+1]==='"'){cell+='"';i++;}
  else if(ch==='"'){quoted=!quoted;}
  else if(ch===","&&!quoted){row.push(cell.trim());cell="";}
  else if((ch==="\n"||ch==="\r")&&!quoted){if(ch==="\r"&&text[i+1]==="\n")i++;row.push(cell.trim());if(row.some(v=>v!==""))rows.push(row);row=[];cell="";}
  else cell+=ch;
 }
 if(quoted)throw new Error("The CSV contains an unclosed quotation mark.");
 if(cell.length||row.length){row.push(cell.trim());if(row.some(v=>v!==""))rows.push(row);}
 return rows;
}
function csvValue(value:string){const escaped=value.replace(/"/g,'""');return /[",\n\r]/.test(value)?'"'+escaped+'"':escaped;}
function downloadFile(name:string,content:string,type:string){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement("a");a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}

export default function MerchantShipments(){
 const {token}=useAuth();const [parcels,setParcels]=useState<Parcel[]>([]);const [loading,setLoading]=useState(true);
 const [query,setQuery]=useState("");const [status,setStatus]=useState("all");const [error,setError]=useState("");const [notice,setNotice]=useState("");
 const [uploading,setUploading]=useState(false);const fileRef=useRef<HTMLInputElement>(null);
 async function refresh(){if(!token)return;setLoading(true);setError("");try{setParcels(await getParcels(token));}catch(e){setError(e instanceof Error?e.message:"Unable to load shipments.");}finally{setLoading(false);}}
 useEffect(()=>{void refresh();},[token]);
 const filtered=useMemo(()=>parcels.filter(p=>(status==="all"||p.status===status)&&[p.tracking_number,p.recipient_name,p.city,p.state,p.pincode].some(v=>v.toLowerCase().includes(query.trim().toLowerCase()))),[parcels,status,query]);
 async function handleFile(file?:File){
  if(!file||!token)return;setUploading(true);setError("");setNotice("");
  try{
   const rows=parseCsv(await file.text());if(rows.length<2)throw new Error("The CSV must include a header and at least one shipment.");
   const headers=rows[0].map(h=>h.toLowerCase());if(HEADERS.some(h=>!headers.includes(h)))throw new Error("Missing required columns. Download the TimeDrop CSV template and use its headers.");
   const data:ParcelCreate[]=rows.slice(1).map((row,index)=>{
    const value=(key:string)=>row[headers.indexOf(key)]??"";
    if(row.length!==headers.length)throw new Error("Row "+(index+2)+" has "+row.length+" columns; expected "+headers.length+".");
    return {tracking_number:value("tracking_number"),recipient_name:value("recipient_name"),phone:value("phone"),address_line:value("address_line"),city:value("city"),state:value("state"),pincode:value("pincode"),delivery_instructions:value("delivery_instructions")||undefined,preferred_delivery_date:value("preferred_delivery_date")||undefined};
   });
   if(data.length>50)throw new Error("Upload up to 50 shipments at a time.");
   const created=await createMerchantParcelsBulk(token,data);setNotice(created.length+" shipments created successfully. Registration receipts are available for each shipment.");await refresh();
  }catch(e){setError(e instanceof Error?e.message:"Unable to process this CSV.");}
  finally{setUploading(false);if(fileRef.current)fileRef.current.value="";}
 }
 function exportCsv(){const rows=[HEADERS,...filtered.map(p=>[p.tracking_number,p.recipient_name,p.phone,p.address_line,p.city,p.state,p.pincode,p.delivery_instructions??"",p.preferred_delivery_date??""])];downloadFile("timedrop-shipments.csv",rows.map(row=>row.map(csvValue).join(",")).join("\r\n"),"text/csv;charset=utf-8");}
 return <div className="merchant-shipments-page">
  <div className="page-heading"><div><div className="eyebrow">MERCHANT WORKSPACE</div><h1>Shipments</h1><p>Search, filter, export and create shipments for your business.</p></div><Link to="/new-shipment" className="primary-button"><Plus size={15}/> Create shipment</Link></div>
  <section className="merchant-bulk-panel"><div className="merchant-bulk-copy"><span className="merchant-bulk-icon"><FileSpreadsheet size={20}/></span><div><strong>Import shipments in bulk</strong><p>Upload a CSV with up to 50 shipments. All rows are validated before anything is created.</p></div></div><div className="merchant-bulk-actions"><button className="secondary-button" onClick={()=>downloadFile("timedrop-shipment-template.csv",TEMPLATE,"text/csv;charset=utf-8")}><Download size={14}/> Download template</button><input ref={fileRef} type="file" accept=".csv,text/csv" hidden onChange={e=>void handleFile(e.target.files?.[0])}/><button className="primary-button" disabled={uploading} onClick={()=>fileRef.current?.click()}><UploadCloud size={15}/>{uploading?"Importing…":"Upload CSV"}</button></div></section>
  {error&&<div className="alert-error" role="alert">{error}</div>}{notice&&<div className="merchant-review-notice" role="status">{notice}</div>}
  <section className="panel merchant-shipment-list"><div className="merchant-shipment-toolbar"><label className="merchant-shipment-search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search tracking ID, recipient or city"/></label><label className="merchant-shipment-filter"><Filter size={15}/><select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option><option value="registered">Registered</option><option value="scheduled">Scheduled</option><option value="out_for_delivery">Out for delivery</option><option value="delivered">Delivered</option><option value="failed">Failed</option><option value="cancelled">Cancelled</option></select></label><button className="secondary-button" onClick={exportCsv} disabled={!filtered.length}><Download size={14}/> Export</button><button className="secondary-button" onClick={()=>void refresh()} disabled={loading}><RefreshCw size={14}/></button></div>
   {loading?<div className="merchant-shipment-empty">Loading shipments…</div>:filtered.length===0?<div className="merchant-shipment-empty"><PackageIcon/><strong>{parcels.length?"No matching shipments":"No shipments yet"}</strong><span>{parcels.length?"Try another search or status filter.":"Create a shipment or import your first CSV."}</span></div>:
    <div className="table-wrap"><table className="merchant-table"><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>CREATED</th><th>PREFERRED DATE</th><th>STATUS</th></tr></thead><tbody>{filtered.map(p=><tr key={p.id}><td><span className="merchant-tracking">{p.tracking_number}</span></td><td><strong className="merchant-recipient">{p.recipient_name}</strong><small className="merchant-shipment-phone">{p.phone}</small></td><td>{p.city}, {p.state}<small className="merchant-shipment-phone">{p.pincode}</small></td><td>{new Date(p.created_at).toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"})}</td><td>{p.preferred_delivery_date?new Date(p.preferred_delivery_date+"T00:00:00").toLocaleDateString("en-IN",{day:"2-digit",month:"short",year:"numeric"}):"—"}</td><td><StatusBadge status={p.status}/></td></tr>)}</tbody></table></div>}
   <div className="merchant-shipment-foot"><span>Showing {filtered.length} of {parcels.length} shipments currently loaded</span><span>Only shipments belonging to your merchant account are shown.</span></div>
  </section>
  <p className="merchant-disclaimer">Bulk import creates parcel registrations only. Delivery slot booking and merchant pickup collection are separate workflows and are not automatically scheduled by this upload.</p>
 </div>;
}
function PackageIcon(){return <FileSpreadsheet size={24}/>;}
