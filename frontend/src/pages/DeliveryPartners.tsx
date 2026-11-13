import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ArrowRight, CalendarClock, Clock3, MapPin, Plus, RefreshCw, Route, Truck } from "lucide-react";
import { createDeliveryPartner, getDeliveryPartners, getDeliveryAssignments, getParcels, assignParcel, getDeliveryRoutePlan } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import DeliveryTimeline from "../components/DeliveryTimeline";
import StatusBadge from "../components/StatusBadge";
import type { DeliveryAssignment, DeliveryPartner, Parcel, DeliveryRoutePlan, DeliveryRouteStop } from "../types";

export default function DeliveryPartners() {
  const { token } = useAuth();
  const [partners, setPartners] = useState<DeliveryPartner[]>([]);
  const [assignments, setAssignments] = useState<DeliveryAssignment[]>([]);
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", phone: "", vehicle_type: "two_wheeler", max_active_assignments: 5 });
  const [selected, setSelected] = useState<Record<number, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [routeDate, setRouteDate] = useState(() => { const d = new Date(); return [d.getFullYear(), String(d.getMonth()+1).padStart(2,"0"), String(d.getDate()).padStart(2,"0")].join("-"); });
  const [routePlan, setRoutePlan] = useState<DeliveryRoutePlan | null>(null);
  const [routeLoading, setRouteLoading] = useState(false);

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
      setForm({ full_name: "", email: "", password: "", phone: "", vehicle_type: "two_wheeler", max_active_assignments: 5 });
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


  async function generateRoutePlan() {
    if (!token || !routeDate) return;
    setRouteLoading(true); setError(""); setNotice("");
    try { setRoutePlan(await getDeliveryRoutePlan(token, routeDate)); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to generate route plan."); setRoutePlan(null); }
    finally { setRouteLoading(false); }
  }

  async function assignRecommended(parcelId: number, partnerId: number) {
    if (!token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await assignParcel(token, parcelId, partnerId);
      setNotice("Recommended parcel assignment created.");
      const [plan] = await Promise.all([getDeliveryRoutePlan(token, routeDate), load()]);
      setRoutePlan(plan);
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to apply recommended assignment."); }
    finally { setBusy(false); }
  }


  const routeGroups = useMemo(() => {
    const grouped = new Map<string, { key:string; partnerId:number|null; partnerName:string; mapUrl:string|null; stops:DeliveryRouteStop[] }>();
    for (const stop of routePlan?.stops ?? []) {
      const key = stop.suggested_partner_id === null ? "unassigned" : String(stop.suggested_partner_id);
      const group = grouped.get(key) ?? {
        key,
        partnerId: stop.suggested_partner_id,
        partnerName: stop.suggested_partner_name || "Needs manual assignment",
        mapUrl: stop.map_url,
        stops: [],
      };
      if (!group.mapUrl && stop.map_url) group.mapUrl = stop.map_url;
      group.stops.push(stop);
      grouped.set(key, group);
    }
    return Array.from(grouped.values()).map(group => ({
      ...group,
      stops: group.stops.sort((a,b) => (a.route_sequence ?? 999) - (b.route_sequence ?? 999)),
    }));
  }, [routePlan]);

  const assignedParcelIds = new Set(assignments.filter(a => ["assigned","accepted","out_for_delivery"].includes(a.status)).map(a => a.parcel_id));
  const eligibleParcels = parcels.filter(p => p.status === "scheduled" && !assignedParcelIds.has(p.id));
  return <div className="delivery-fleet-workspace">
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
        <label>Maximum active assignments<input required type="number" min={1} max={50} value={form.max_active_assignments} onChange={e=>setForm({...form,max_active_assignments:Number(e.target.value)})}/></label>
        <div className="customer-form-actions"><span>Share credentials with the partner through a secure channel.</span><button className="primary-button" disabled={busy}><Plus size={15}/> Create account</button></div>
      </form>
    </section>
    <div className="section-title-row"><h2>Delivery team</h2><span className="result-count">{partners.length} partners</span></div>
    {loading ? <div className="panel table-loading">Loading delivery partners…</div> : partners.length ? <div className="panel list-panel"><div className="table-wrap"><table><thead><tr><th>PARTNER</th><th>CONTACT</th><th>VEHICLE</th><th>ACTIVE JOBS / CAPACITY</th><th>ACCOUNT</th></tr></thead><tbody>{partners.map(p=><tr key={p.id}><td><strong className="cell-strong">{p.full_name}</strong><span className="cell-sub">Partner #{p.id}</span></td><td>{p.email}<span className="cell-sub">{p.phone}</span></td><td>{p.vehicle_type.replace(/_/g," ")}</td><td>{p.active_assignments} / {p.max_active_assignments}</td><td><StatusBadge status={p.is_active ? (p.is_available ? "available" : "busy") : "inactive"}/></td></tr>)}</tbody></table></div></div> : <div className="panel"><EmptyState title="No delivery partners yet" description="Create the first partner account using the form above."/></div>}
    <div className="section-title-row"><h2>Unassigned scheduled parcels</h2><span className="result-count">{eligibleParcels.length} parcels</span></div>
    {eligibleParcels.length ? <div className="booking-list">{eligibleParcels.map(parcel=><div className="panel booking-card" key={parcel.id}><div className="booking-main"><div className="booking-icon"><Truck size={19}/></div><div><strong>{parcel.tracking_number}</strong><span>{parcel.recipient_name} · {parcel.city}, {parcel.state}</span><span>{parcel.address_line} · {parcel.pincode}</span></div></div><div className="booking-actions"><select value={selected[parcel.id] || ""} onChange={e=>setSelected({...selected,[parcel.id]:e.target.value})}><option value="">Choose partner…</option>{partners.filter(p=>p.is_active && p.is_available).map(p=><option key={p.id} value={p.id}>{p.full_name} · {p.active_assignments} active</option>)}</select><button className="primary-button" disabled={busy || !selected[parcel.id]} onClick={()=>void assign(parcel.id)}>Assign parcel</button></div></div>)}</div> : <div className="panel"><EmptyState title="No parcels awaiting assignment" description="Only parcels with an active delivery booking can be assigned."/></div>}
    <section className="panel customer-form-panel">
      <div className="panel-heading"><div><h2>Route planning & assignment suggestions</h2><p>Generate a proposed partner allocation. When map routing is enabled, TimeDrop geocodes destinations and uses road-network estimates to reorder each partner’s stops.</p></div></div>
      <div className="booking-actions"><label>Delivery date<input type="date" value={routeDate} onChange={e=>{setRouteDate(e.target.value);setRoutePlan(null);}}/></label><button className="primary-button" disabled={routeLoading || !routeDate} onClick={()=>void generateRoutePlan()}>{routeLoading?"Planning…":"Generate route plan"}</button></div>
      {routePlan&&<div className="route-planning-results">
        <div className="route-planning-summary">
          <div><span className="route-planning-kicker">PLANNING SUMMARY</span><strong>{routePlan.mapping_enabled?"Road-network route plan":"Zone-based assignment plan"}</strong><small>{routePlan.stops.length} stops grouped into {routeGroups.filter(group=>group.partnerId!==null).length} partner route(s)</small></div>
          <div className="route-planning-kpis"><span><strong>{routePlan.total_unassigned}</strong>Parcels</span><span><strong>{routePlan.recommended}</strong>Recommendations</span><span><strong>{routePlan.unassigned_without_partner}</strong>Need attention</span></div>
        </div>
        <div className={routePlan.mapping_enabled?"route-planning-mode road":"route-planning-mode zone"}>
          {routePlan.mapping_enabled?"Road routing enabled · OpenStreetMap geocoding and OSRM driving estimates are available.":"Zone-based planning is active. Enable route mapping to add geocoded stops and road-network estimates."}
        </div>
        {routeGroups.length ? <div className="route-groups">{routeGroups.map(group=><section className="route-group" key={group.key}>
          <div className="route-group-heading">
            <span className="route-partner-icon"><Truck size={17}/></span>
            <div><small>PROPOSED ROUTE</small><strong>{group.partnerName}</strong><span>{group.stops.length} stop(s) · {routePlan.mapping_enabled?"Road-optimized order":"Zone-based order"}</span></div>
            {group.mapUrl&&<a href={group.mapUrl} target="_blank" rel="noreferrer" className="route-map-link"><MapPin size={14}/> Open route map <ArrowRight size={13}/></a>}
          </div>
          <div className="route-stop-list">{group.stops.map((stop,index)=><article className="route-stop-card" key={stop.parcel_id}>
            <span className="route-stop-number">{stop.route_sequence??index+1}</span>
            <div className="route-stop-main">
              <div className="route-stop-title"><strong>{stop.tracking_number}</strong><span>{stop.recipient_name}</span></div>
              <div className="route-stop-address"><MapPin size={13}/>{stop.city}, {stop.state} · PIN {stop.pincode}</div>
              <div className="route-stop-meta"><span><CalendarClock size={12}/> {stop.slot_start.slice(0,5)}–{stop.slot_end.slice(0,5)}</span>{stop.leg_distance_m!=null&&<span><Route size={12}/> {(stop.leg_distance_m/1000).toFixed(1)} km leg</span>}{stop.leg_duration_seconds!=null&&<span><Clock3 size={12}/> {Math.max(1,Math.round(stop.leg_duration_seconds/60))} min</span>}</div>
              <p>{stop.recommendation}</p>
            </div>
            <div className="route-stop-action">{stop.suggested_partner_id?<button className="secondary-button" disabled={busy} onClick={()=>void assignRecommended(stop.parcel_id,stop.suggested_partner_id!)}>Assign parcel</button>:<span className="route-needs-attention">No compatible partner</span>}</div>
          </article>)}</div>
        </section>)}</div> : <EmptyState title="No parcels need assignment" description="There are no booked, unassigned parcels for this date."/>}
      </div>}
    </section>
    <div className="section-title-row"><h2>Assignment register</h2><span className="result-count">{assignments.length} records</span></div>
    {assignments.length ? <div className="panel list-panel"><div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DELIVERY PARTNER</th><th>DELIVERY WINDOW</th><th>STATUS</th></tr></thead><tbody>{assignments.map(a=><tr key={a.id}><td className="tracking">{a.tracking_number}</td><td>{a.recipient_name}<span className="cell-sub">{a.city}, {a.state}</span></td><td>{a.partner_name}</td><td>{new Date(a.delivery_date+"T00:00:00").toLocaleDateString("en-IN")}<span className="cell-sub">{a.start_time.slice(0,5)}–{a.end_time.slice(0,5)}</span></td><td><StatusBadge status={a.status}/><details className="delivery-history"><summary>History</summary>{token && <DeliveryTimeline token={token} assignmentId={a.id}/>}</details></td></tr>)}</tbody></table></div></div> : <div className="panel"><EmptyState title="No assignments yet" description="New assignments will appear here."/></div>}
  </div>;
}
