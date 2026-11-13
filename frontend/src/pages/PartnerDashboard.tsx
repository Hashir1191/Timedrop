import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarClock, CheckCircle2, Clock3, MapPin, Package, RefreshCw, Search, ShieldCheck, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { getMyAssignments, getMyAvailability, updateAssignmentStatus, submitDeliveryProof, updateDeliveryEta, type PartnerAvailabilitySettings } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import DeliveryTimeline from "../components/DeliveryTimeline";
import StatusBadge from "../components/StatusBadge";
import type { DeliveryAssignment } from "../types";

type DeliveryFilter = "active" | "completed" | "all";

export default function PartnerDashboard() {
  const { token, user } = useAuth();
  const [items, setItems] = useState<DeliveryAssignment[]>([]);
  const [availability, setAvailability] = useState<PartnerAvailabilitySettings | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [proof, setProof] = useState<Record<number, {code:string;recipient_name:string}>>({});
  const [eta, setEta] = useState<Record<number, {start:string;end:string}>>({});
  const [filter, setFilter] = useState<DeliveryFilter>("active");
  const [search, setSearch] = useState("");

  async function load() {
    if (!token) return;
    setError("");
    try {
      const [assignments, schedule] = await Promise.all([getMyAssignments(token), getMyAvailability(token)]);
      setItems(assignments);
      setAvailability(schedule);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load your delivery workspace.");
    }
  }

  useEffect(() => { void load(); }, [token]);

  async function update(id:number, status:"accepted"|"out_for_delivery"|"delivered"|"failed") {
    if (!token) return;
    let failure_reason: string | undefined;
    if (status === "failed") {
      failure_reason = window.prompt("Enter the reason delivery failed:")?.trim();
      if (!failure_reason || failure_reason.length < 3) return;
    }
    setBusy(id);
    setError("");
    try {
      await updateAssignmentStatus(token, id, {status, ...(failure_reason ? {failure_reason} : {})});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update delivery status.");
    } finally {
      setBusy(null);
    }
  }

  async function saveEta(id:number) {
    if (!token) return;
    const value = eta[id];
    if (!value?.start || !value?.end) { setError("Choose both ETA start and end times."); return; }
    const start = new Date(value.start), end = new Date(value.end);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start || end <= new Date()) {
      setError("Choose a future ETA window with the end after the start.");
      return;
    }
    setBusy(id);
    setError("");
    try {
      await updateDeliveryEta(token, id, {estimated_delivery_start:start.toISOString(), estimated_delivery_end:end.toISOString()});
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update ETA.");
    } finally {
      setBusy(null);
    }
  }

  async function confirmProof(id:number) {
    if (!token) return;
    const data = proof[id];
    if (!data || !/^\d{6}$/.test(data.code) || data.recipient_name.trim().length < 2) {
      setError("Enter the six-digit code and recipient name.");
      return;
    }
    setBusy(id);
    setError("");
    try {
      await submitDeliveryProof(token, id, {code:data.code, recipient_name:data.recipient_name.trim()});
      setProof((current) => ({...current, [id]:{code:"",recipient_name:""}}));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to verify delivery.");
    } finally {
      setBusy(null);
    }
  }

  const active = items.filter((item) => ["assigned","accepted","out_for_delivery"].includes(item.status));
  const delivered = items.filter((item) => item.status === "delivered").length;
  const visibleItems = useMemo(() => items.filter((item) => {
    const isActive = ["assigned","accepted","out_for_delivery"].includes(item.status);
    const matchesFilter = filter === "all" || (filter === "active" && isActive) || (filter === "completed" && !isActive);
    const query = search.trim().toLowerCase();
    const matchesSearch = !query || [item.tracking_number,item.recipient_name,item.city,item.pincode].some((value) => value.toLowerCase().includes(query));
    return matchesFilter && matchesSearch;
  }).sort((a,b) => a.delivery_date.localeCompare(b.delivery_date) || a.start_time.localeCompare(b.start_time) || a.tracking_number.localeCompare(b.tracking_number)), [items,filter,search]);

  const activeWindows = availability?.windows.filter((window) => window.is_active) ?? [];
  const activeDays = new Set(activeWindows.map((window) => window.weekday)).size;

  return <div className="partner-dashboard">
    <section className="partner-welcome">
      <div className="partner-welcome-copy">
        <span className="partner-welcome-kicker">YOUR DELIVERY WORKSPACE</span>
        <h1>Make every delivery<br/><span>count.</span></h1>
        <p>Welcome, {user?.full_name?.split(" ")[0] || "partner"}. Your assignments, delivery windows and progress are all in one place.</p>
        <Link to="/availability" className="partner-welcome-action"><CalendarClock size={16}/> Manage availability <ArrowRight size={15}/></Link>
      </div>
      <div className="partner-shift-card">
        <span className="partner-shift-icon"><ShieldCheck size={18}/></span>
        <div className="partner-shift-copy"><small>WEEKLY AVAILABILITY</small><strong>{availability?.enabled ? "Schedule active" : "Flexible availability"}</strong><span>{availability?.enabled ? `${activeDays} active day(s) · ${activeWindows.length} time window(s)` : "No weekly restrictions enabled"}</span></div>
        <Link to="/availability" aria-label="Edit weekly availability"><ArrowRight size={16}/></Link>
      </div>
      <div className="partner-welcome-decoration" aria-hidden="true"><div/><div/><div/></div>
    </section>

    {error && <div className="alert-error">{error}</div>}

    <section className="partner-metrics">
      <PartnerMetric icon={Package} label="Total assigned" value={items.length} tone="blue" note="All assigned parcels"/>
      <PartnerMetric icon={Truck} label="In progress" value={active.length} tone="amber" note="Needs your attention"/>
      <PartnerMetric icon={CheckCircle2} label="Delivered" value={delivered} tone="green" note="Completed handovers"/>
    </section>

    <section className="partner-queue">
      <div className="partner-queue-heading">
        <div><span className="partner-section-kicker">YOUR TASK LIST</span><h2>Delivery assignments</h2><p>Work through your booked delivery windows and keep customers informed.</p></div>
        <button className="secondary-button" onClick={() => void load()}><RefreshCw size={14}/> Refresh</button>
      </div>

      <div className="partner-queue-toolbar">
        <label className="partner-search"><Search size={16}/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search tracking ID, recipient, city or PIN" aria-label="Search deliveries"/></label>
        <div className="partner-filter-tabs" aria-label="Filter assignments">
          {(["active","completed","all"] as DeliveryFilter[]).map((value) => <button type="button" key={value} className={filter===value?"active":""} onClick={() => setFilter(value)}>{value==="active"?"Active":value==="completed"?"Completed / failed":"All"}</button>)}
        </div>
        <span className="partner-result-count">{visibleItems.length} shown</span>
      </div>

      {items.length===0 ? <div className="partner-empty"><EmptyState title="Your queue is clear" description="New delivery assignments from operations will appear here."/><Link to="/availability" className="partner-empty-link">Review your working hours <ArrowRight size={14}/></Link></div> :
       visibleItems.length===0 ? <div className="partner-empty"><EmptyState title="No matching deliveries" description="Try another search or switch the assignment filter."/></div> :
       <div className="partner-assignment-list">{visibleItems.map((item) => <article className="partner-assignment-card" key={item.id}>
        <div className="partner-assignment-main">
          <div className="partner-assignment-top">
            <div className="partner-assignment-id"><span>TRACKING NUMBER</span><strong>{item.tracking_number}</strong></div>
            <StatusBadge status={item.status}/>
          </div>
          <div className="partner-recipient"><span>DELIVER TO</span><strong>{item.recipient_name}</strong></div>
          <div className="partner-destination"><MapPin size={16}/><div><strong>{item.address_line}</strong><span>{item.city}, {item.state} · {item.pincode}</span><span>{item.phone}</span></div></div>
          <div className="partner-assignment-meta">
            <span><CalendarClock size={14}/><span>Booked window <strong>{new Date(item.delivery_date+"T00:00:00").toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})} · {item.start_time.slice(0,5)}–{item.end_time.slice(0,5)}</strong></span></span>
            {item.estimated_delivery_start&&item.estimated_delivery_end&&<span><Clock3 size={14}/><span>Customer ETA <strong>{new Date(item.estimated_delivery_start).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short"})} – {new Date(item.estimated_delivery_end).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"})}</strong></span></span>}
          </div>
        </div>

        {![ "delivered", "failed" ].includes(item.status) && <div className="partner-eta-editor">
          <div className="partner-form-heading"><Clock3 size={15}/><strong>Keep the customer updated</strong></div>
          <div className="partner-eta-fields">
            <label>ETA start<input type="datetime-local" value={eta[item.id]?.start||""} onChange={(event) => setEta((current) => ({...current,[item.id]:{start:event.target.value,end:current[item.id]?.end||""}}))}/></label>
            <label>ETA end<input type="datetime-local" value={eta[item.id]?.end||""} onChange={(event) => setEta((current) => ({...current,[item.id]:{start:current[item.id]?.start||"",end:event.target.value}}))}/></label>
            <button className="secondary-button" disabled={busy===item.id} onClick={() => void saveEta(item.id)}>Publish ETA</button>
          </div>
        </div>}

        {item.status==="out_for_delivery" && <div className="partner-proof-editor">
          <div className="partner-form-heading"><ShieldCheck size={15}/><strong>Confirm recipient handover</strong></div>
          <div className="partner-proof-fields">
            <label>Recipient name<input value={proof[item.id]?.recipient_name||""} onChange={(event) => setProof((current) => ({...current,[item.id]:{code:current[item.id]?.code||"",recipient_name:event.target.value}}))} placeholder="Person receiving the parcel"/></label>
            <label>6-digit customer code<input inputMode="numeric" maxLength={6} value={proof[item.id]?.code||""} onChange={(event) => setProof((current) => ({...current,[item.id]:{code:event.target.value.replace(/\D/g,"").slice(0,6),recipient_name:current[item.id]?.recipient_name||""}}))} placeholder="Enter delivery code"/></label>
          </div>
          <div className="partner-assignment-actions"><button className="primary-button" disabled={busy===item.id} onClick={() => void confirmProof(item.id)}>Verify & mark delivered</button><button className="danger-button" disabled={busy===item.id} onClick={() => void update(item.id,"failed")}>Delivery failed</button></div>
        </div>}

        <div className="partner-assignment-bottom">
          <details className="delivery-history"><summary>View delivery history</summary>{token && <DeliveryTimeline token={token} assignmentId={item.id}/>}</details>
          {item.status==="assigned" && <div className="partner-assignment-actions"><button className="primary-button" disabled={busy===item.id} onClick={() => void update(item.id,"accepted")}>Accept assignment</button><button className="danger-button" disabled={busy===item.id} onClick={() => void update(item.id,"failed")}>Cannot deliver</button></div>}
          {item.status==="accepted" && <div className="partner-assignment-actions"><button className="primary-button" disabled={busy===item.id} onClick={() => void update(item.id,"out_for_delivery")}>Start delivery</button></div>}
        </div>
       </article>)}</div>
      }
    </section>
  </div>;
}

function PartnerMetric({icon:Icon,label,value,tone,note}:{icon:typeof Package;label:string;value:number;tone:string;note:string}) {
  return <article className="partner-metric-card"><span className={`partner-metric-icon ${tone}`}><Icon size={19}/></span><div><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>;
}
