import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, MapPin, Package, PackageCheck, RefreshCw, Search, Save, Truck, Warehouse, X } from "lucide-react";
import { getWarehouseParcels, getWarehouseSummary, updateWarehouseLocation } from "../api";
import { useAuth } from "../auth";
import type { Parcel } from "../types";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";

const statusOptions = [
  ["", "All statuses"],
  ["registered", "Registered"],
  ["scheduled", "Scheduled"],
  ["out_for_delivery", "Out for delivery"],
  ["delivered", "Delivered"],
  ["failed", "Failed"],
  ["returned_to_operations", "Returned to operations"],
  ["cancelled", "Cancelled"],
];

type WarehouseSummary = Awaited<ReturnType<typeof getWarehouseSummary>>;

export default function WarehousePage() {
  const { token } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [summary, setSummary] = useState<WarehouseSummary | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [location, setLocation] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [locationDraft, setLocationDraft] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function refresh() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [stats, rows] = await Promise.all([
        getWarehouseSummary(token),
        getWarehouseParcels(token, {q:query,status,location}),
      ]);
      setSummary(stats);
      setParcels(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load warehouse inventory.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void refresh(); }, [token, query, status, location]);

  function beginEdit(parcel: Parcel) {
    setEditingId(parcel.id);
    setLocationDraft(parcel.warehouse_location || "");
    setError("");
    setSuccess("");
  }

  function cancelEdit() {
    setEditingId(null);
    setLocationDraft("");
  }

  async function saveLocation(parcel: Parcel) {
    if (!token) return;
    const next = locationDraft.trim() || null;
    if (next && next.length > 40) {
      setError("Storage location must be 40 characters or fewer.");
      return;
    }
    setBusyId(parcel.id);
    setError("");
    setSuccess("");
    try {
      await updateWarehouseLocation(token, parcel.id, next);
      setParcels((current) => current.map((item) => item.id === parcel.id ? {...item, warehouse_location:next} : item));
      setSuccess(next ? `Storage location for ${parcel.tracking_number} updated to ${next}.` : `Storage location cleared for ${parcel.tracking_number}.`);
      cancelEdit();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update storage location.");
    } finally {
      setBusyId(null);
    }
  }

  return <div className="warehouse-workspace">
    <div className="page-heading warehouse-page-heading">
      <div><div className="eyebrow">WAREHOUSE OPERATIONS / INVENTORY</div><h1>Warehouse management</h1><p>Track physical custody, organize storage locations, and keep inventory moving.</p></div>
      <button className="secondary-button" onClick={() => void refresh()} disabled={loading}><RefreshCw size={15}/> Refresh</button>
    </div>

    {error && <div className="alert-error">{error}</div>}
    {success && <div className="alert-success">{success}</div>}

    <section className="warehouse-summary-grid">
      <WarehouseMetric icon={Package} label="Total parcels" value={summary?.total_parcels} tone="blue" note="All delivery stages"/>
      <WarehouseMetric icon={Warehouse} label="In custody" value={summary?.in_custody} tone="violet" note="Physically with operations"/>
      <WarehouseMetric icon={MapPin} label="Assigned to bins" value={summary?.assigned_to_bins} tone="green" note="Storage recorded"/>
      <WarehouseMetric icon={PackageCheck} label="Awaiting storage" value={summary?.awaiting_storage} tone="amber" note="No bin assigned"/>
      <WarehouseMetric icon={AlertTriangle} label="Damaged / opened" value={summary?.damaged_or_opened} tone="red" note="Latest inspection"/>
      <WarehouseMetric icon={Truck} label="Out for delivery" value={summary?.out_for_delivery} tone="blue" note="With delivery partners"/>
      <WarehouseMetric icon={CheckCircle2} label="Delivered" value={summary?.delivered} tone="green" note="Completed parcels"/>
      <WarehouseMetric icon={AlertTriangle} label="Failed deliveries" value={summary?.failed} tone="red" note="Needs follow-up"/>
    </section>

    <section className="warehouse-inventory">
      <div className="warehouse-inventory-heading"><div><span className="warehouse-section-kicker">STORAGE & CUSTODY</span><h2>Parcel inventory</h2><p>Find a parcel and manage its storage location.</p></div><span className="warehouse-inventory-count">{loading ? "Loading…" : `${parcels.length} results · max 200`}</span></div>
      <div className="warehouse-toolbar">
        <label className="warehouse-search"><Search size={16}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tracking ID, recipient, city or PIN" aria-label="Search warehouse parcels"/></label>
        <select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter parcel status">{statusOptions.map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select>
        <select value={location} onChange={(event) => setLocation(event.target.value)} aria-label="Filter storage location"><option value="">All locations</option><option value="unassigned">Awaiting storage</option></select>
      </div>

      {loading ? <div className="warehouse-loading-grid">{[1,2,3,4].map((item) => <div className="warehouse-loading-card" key={item}/>)}</div> :
       parcels.length ? <div className="warehouse-parcel-grid">{parcels.map((parcel) => <article className="warehouse-parcel-card" key={parcel.id}>
        <div className="warehouse-parcel-card-top"><span className="warehouse-parcel-icon"><Package size={18}/></span><div className="warehouse-parcel-id"><small>TRACKING NUMBER</small><strong>{parcel.tracking_number}</strong></div><StatusBadge status={parcel.status}/></div>
        <div className="warehouse-parcel-recipient"><span>RECIPIENT</span><strong>{parcel.recipient_name}</strong><small>{parcel.phone}</small></div>
        <div className="warehouse-parcel-destination"><MapPin size={14}/><span>{parcel.city}, {parcel.state} · {parcel.pincode}</span></div>
        <div className="warehouse-bin-area">
          <div className="warehouse-bin-label"><span>STORAGE LOCATION</span><strong className={parcel.warehouse_location?"assigned":"unassigned"}>{parcel.warehouse_location || "Awaiting storage"}</strong></div>
          {editingId===parcel.id ? <div className="warehouse-bin-editor">
            <label><span>Bin / shelf reference</span><input autoFocus maxLength={40} value={locationDraft} onChange={(event) => setLocationDraft(event.target.value)} placeholder="Example: A-01-02"/></label>
            <div><button className="warehouse-save-bin" disabled={busyId===parcel.id} onClick={() => void saveLocation(parcel)}><Save size={14}/>{busyId===parcel.id?"Saving…":"Save"}</button><button className="warehouse-cancel-bin" onClick={cancelEdit} disabled={busyId===parcel.id} aria-label="Cancel bin edit"><X size={14}/></button></div>
          </div> : <button className="warehouse-edit-bin" onClick={() => beginEdit(parcel)}>{parcel.warehouse_location?"Edit location":"Assign storage bin"} <MapPin size={13}/></button>}
        </div>
        <div className="warehouse-parcel-card-foot"><span>Received / created {new Date(parcel.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</span><span>#{parcel.id}</span></div>
       </article>)}</div> : <div className="warehouse-empty"><EmptyState title="No matching parcels" description="Try changing the search text or inventory filters."/></div>
      }
    </section>
    <p className="page-footnote">Storage-bin changes are accepted only while the latest custody event confirms the parcel is physically in TimeDrop operations custody. Use a consistent location format, for example A-01-02.</p>
  </div>;
}

function WarehouseMetric({icon:Icon,label,value,tone,note}:{icon:typeof Package;label:string;value?:number;tone:string;note:string}) {
  return <article className="warehouse-metric"><span className={`warehouse-metric-icon ${tone}`}><Icon size={18}/></span><div><span>{label}</span><strong>{value ?? "—"}</strong><small>{note}</small></div></article>;
}
