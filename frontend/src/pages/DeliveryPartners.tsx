import { useEffect, useState, type FormEvent } from "react";
import { Plus, RefreshCw, Truck } from "lucide-react";
import { createDeliveryPartner, getDeliveryPartners, getDeliveryAssignments, getParcels, assignParcel } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import DeliveryTimeline from "../components/DeliveryTimeline";
import StatusBadge from "../components/StatusBadge";
import type { DeliveryAssignment, DeliveryPartner, Parcel } from "../types";

export default function DeliveryPartners() {
  const { token } = useAuth();
  const [partners, setPartners] = useState<DeliveryPartner[]>([]);
  const [assignments, setAssignments] = useState<DeliveryAssignment[]>([]);
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", phone: "", vehicle_type: "two_wheeler" });
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!token) return;
    setLoading(true); setError("");
    try {
      const [p, a, allParcels] = await Promise.all([getDeliveryPartners(token), getDeliveryAssignments(token), getParcels(token)]);
      setPartners(p); setAssignments(a); setParcels(allParcels);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to load delivery operations."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [token]);

  async function submitPartner(event: FormEvent) {
    event.preventDefault(); if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await createDeliveryPartner(token, form);
      setForm({ full_name: "", email: "", password: "", phone: "", vehicle_type: "two_wheeler" });
      setNotice("Delivery partner account created. Share the temporary password securely.");
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to create partner."); }
    finally { setBusy(false); }
  }

  async function assign(parcelId: number) {
    if (!token || !selected[parcelId]) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await assignParcel(token, parcelId, Number(selected[parcelId]));
      setNotice("Parcel assigned successfully.");
      await load();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to assign parcel."); }
    finally { setBusy(false); }
  }

  const assignedParcelIds = new Set(assignments.filter(a => ["assigned","accepted","out_for_delivery"].includes(a.status)).map(a => a.parcel_id));
  const eligibleParcels = parcels.filter(p => p.status === "scheduled" && !assignedParcelIds.has(p.id));
  return <>
    <div className="page-heading"><div><div className="eyebrow">OPERATIONS / DELIVERY FLEET</div><h1>Delivery partners</h1><p>Create partner accounts and assign booked parcels to your delivery team.</p></div><button className="secondary-button" onClick={() => void load()}><RefreshCw size={14}/> Refresh</button></div>
    {error && <div className="alert-error">{error}</div>}{notice && <div className="alert-success">{notice}</div>}
    <div className="stats-grid">
      <div className="stat-card"><div className="stat-icon blue"><Truck size={18}/></div><div className="stat-label">Total partners</div><div className="stat-value">{partners.length}</div><div className="stat-note">Provisioned accounts</div></div>
      <div className="stat-card"><div className="stat-icon violet"><Truck size={18}/></div><div className="stat-label">Active assignments</div><div className="stat-value">{assignedParcelIds.size}</div><div className="stat-note">In the delivery workflow</div></div>
      <div className="stat-card"><div className="stat-icon amber"><Truck size={18}/></div><div className="stat-label">Ready to assign</div><div className="stat-value">{eligibleParcels.length}</div><div className="stat-note">Scheduled parcels without a partner</div></div>
      <div className="stat-card"><div className="stat-icon green"><Truck size={18}/></div><div className="stat-label">Completed</div><div className="stat-value">{assignments.filter(a => a.status === "delivered").length}</div><div className="stat-note">Delivered assignments</div></div>
    </div>
    <section className="panel customer-form-panel">
      <div className="panel-heading"><div><h2><Plus size={17}/> Create delivery partner</h2><p>Accounts can only be created by an operations administrator.</p></div></div>
      <form className="customer-form" onSubmit={submitPartner}>
        <label>Full name<input required minLength={2} value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/></label>
        <label>Email address<input required type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label>
        <label>Temporary password<input required type="password" minLength={12} value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="At least 12 characters"/></label>
        <label>Phone number<input required minLength={10} value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/></label>
        <label>Vehicle type<select value={form.vehicle_type} onChange={e=>setForm({...form,vehicle_type:e.target.value})}><option value="two_wheeler">Two wheeler</option><option value="three_wheeler">Three wheeler</option><option value="four_wheeler">Four wheeler</option><option value="bicycle">Bicycle</option></select></label>
        <div className="customer-form-actions"><span>Share credentials with the partner through a secure channel.</span><button className="primary-button" disabled={busy}><Plus size={15}/> Create account</button></div>
      </form>
    </section>
    <div className="section-title-row"><h2>Delivery team</h2><span className="result-count">{partners.length} partners</span></div>
    {loading ? <div className="panel table-loading">Loading delivery partners…</div> : partners.length ? <div className="panel list-panel"><div className="table-wrap"><table><thead><tr><th>PARTNER</th><th>CONTACT</th><th>VEHICLE</th><th>ACTIVE JOBS</th><th>ACCOUNT</th></tr></thead><tbody>{partners.map(p=><tr key={p.id}><td><strong className="cell-strong">{p.full_name}</strong><span className="cell-sub">Partner #{p.id}</span></td><td>{p.email}<span className="cell-sub">{p.phone}</span></td><td>{p.vehicle_type.replaceAll("_"," ")}</td><td>{p.active_assignments}</td><td><StatusBadge status={p.is_active ? (p.is_available ? "available" : "busy") : "inactive"}/></td></tr>)}</tbody></table></div></div> : <div className="panel"><EmptyState title="No delivery partners yet" description="Create the first partner account using the form above."/></div>}
    <div className="section-title-row"><h2>Unassigned scheduled parcels</h2><span className="result-count">{eligibleParcels.length} parcels</span></div>
    {eligibleParcels.length ? <div className="booking-list">{eligibleParcels.map(parcel=><div className="panel booking-card" key={parcel.id}><div className="booking-main"><div className="booking-icon"><Truck size={19}/></div><div><strong>{parcel.tracking_number}</strong><span>{parcel.recipient_name} · {parcel.city}, {parcel.state}</span><span>{parcel.address_line} · {parcel.pincode}</span></div></div><div className="booking-actions"><select value={selected[parcel.id] || ""} onChange={e=>setSelected({...selected,[parcel.id]:e.target.value})}><option value="">Choose partner…</option>{partners.filter(p=>p.is_active && p.is_available).map(p=><option key={p.id} value={p.id}>{p.full_name} · {p.active_assignments} active</option>)}</select><button className="primary-button" disabled={busy || !selected[parcel.id]} onClick={()=>void assign(parcel.id)}>Assign parcel</button></div></div>)}</div> : <div className="panel"><EmptyState title="No parcels awaiting assignment" description="Only parcels with an active delivery booking can be assigned."/></div>}
    <div className="section-title-row"><h2>Assignment register</h2><span className="result-count">{assignments.length} records</span></div>
    {assignments.length ? <div className="panel list-panel"><div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DELIVERY PARTNER</th><th>DELIVERY WINDOW</th><th>STATUS</th></tr></thead><tbody>{assignments.map(a=><tr key={a.id}><td className="tracking">{a.tracking_number}</td><td>{a.recipient_name}<span className="cell-sub">{a.city}, {a.state}</span></td><td>{a.partner_name}</td><td>{new Date(a.delivery_date+"T00:00:00").toLocaleDateString("en-IN")}<span className="cell-sub">{a.start_time.slice(0,5)}–{a.end_time.slice(0,5)}</span></td><td><StatusBadge status={a.status}/><details className="delivery-history"><summary>History</summary>{token && <DeliveryTimeline token={token} assignmentId={a.id}/>}</details></td></tr>)}</tbody></table></div></div> : <div className="panel"><EmptyState title="No assignments yet" description="New assignments will appear here."/></div>}
  </>;
}
