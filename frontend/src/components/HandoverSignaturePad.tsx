import { useRef, useState } from "react";
import type { PointerEvent } from "react";
import { CheckCircle2, Eraser, PenLine, ShieldCheck } from "lucide-react";
import { submitHandoverSignature } from "../api";

const ACKNOWLEDGEMENT="I confirm that I have physically received the parcel identified in this handover. The parcel condition and handover record have been shown to me. I understand that any later loss or damage will be reviewed through TimeDrop's documented investigation and dispute process.";

export default function HandoverSignaturePad({token,assignmentId,signerName,onSigned}:{token:string;assignmentId:number;signerName:string;onSigned:()=>void}){
 const canvasRef=useRef<HTMLCanvasElement|null>(null);
 const drawing=useRef(false);
 const [hasInk,setHasInk]=useState(false);
 const [consent,setConsent]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [saved,setSaved]=useState(false);

 function point(event:PointerEvent<HTMLCanvasElement>){
  const canvas=event.currentTarget;
  const rect=canvas.getBoundingClientRect();
  return {x:(event.clientX-rect.left)*(canvas.width/rect.width),y:(event.clientY-rect.top)*(canvas.height/rect.height)};
 }
 function start(event:React.PointerEvent<HTMLCanvasElement>){
  const canvas=canvasRef.current;if(!canvas)return;
  event.preventDefault();canvas.setPointerCapture(event.pointerId);
  const context=canvas.getContext("2d");if(!context)return;
  const p=point(event);context.beginPath();context.moveTo(p.x,p.y);
  context.strokeStyle="#1e3555";context.lineWidth=3;context.lineCap="round";context.lineJoin="round";
  drawing.current=true;setHasInk(true);setError("");
 }
 function move(event:React.PointerEvent<HTMLCanvasElement>){
  if(!drawing.current)return;
  const canvas=canvasRef.current;if(!canvas)return;
  const context=canvas.getContext("2d");if(!context)return;
  const p=point(event);context.lineTo(p.x,p.y);context.stroke();
 }
 function stop(event:React.PointerEvent<HTMLCanvasElement>){
  drawing.current=false;
  if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId);
 }
 function clear(){
  const canvas=canvasRef.current;const context=canvas?.getContext("2d");
  if(canvas&&context)context.clearRect(0,0,canvas.width,canvas.height);
  setHasInk(false);setSaved(false);setError("");
 }
 async function submit(){
  if(!token||!canvasRef.current||!hasInk||!consent)return;
  setBusy(true);setError("");
  try{
   const signature_data_url=canvasRef.current.toDataURL("image/png");
   await submitHandoverSignature(token,assignmentId,{signed_name:signerName,signature_data_url});
   setSaved(true);onSigned();
  }catch(err){setError(err instanceof Error?err.message:"Unable to save your handover signature. Please try again.");}
  finally{setBusy(false);}
 }

 return <section className="handover-signature-panel" aria-label="Parcel handover signature">
  <div className="handover-signature-heading"><span><PenLine size={16}/></span><div><strong>Confirm physical parcel handover</strong><p>Review the parcel details and sign before accepting this assignment.</p></div></div>
  <div className="handover-signature-signer"><span>PARTNER ACCOUNT</span><strong>{signerName}</strong></div>
  <div className="handover-signature-canvas-wrap"><canvas ref={canvasRef} width={640} height={180} aria-label="Draw your signature in this box" onPointerDown={start} onPointerMove={move} onPointerUp={stop} onPointerCancel={stop}/><span>Sign here using your finger, stylus or mouse</span></div>
  <div className="handover-signature-actions"><button type="button" className="secondary-button" onClick={clear} disabled={busy}><Eraser size={14}/> Clear signature</button></div>
  <label className="handover-signature-consent"><input type="checkbox" checked={consent} onChange={event=>setConsent(event.target.checked)} disabled={busy}/><span>{ACKNOWLEDGEMENT}</span></label>
  {error&&<div className="alert-error" role="alert">{error}</div>}
  {saved&&<div className="handover-signature-saved" role="status"><CheckCircle2 size={15}/> Handover signature recorded. You can now accept this assignment.</div>}
  <button type="button" className="primary-button" onClick={()=>void submit()} disabled={busy||!hasInk||!consent||saved}><ShieldCheck size={15}/>{busy?"Recording signature…":"Sign and confirm receipt"}</button>
  <small className="handover-signature-legal">This signature records acknowledgement of physical receipt. It does not automatically determine fault or authorize a salary deduction; any later claim must follow the documented review and dispute process.</small>
 </section>;
}
