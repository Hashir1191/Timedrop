import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, CalendarDays, MapPin, Package, RefreshCw, Search } from "lucide-react";
import { getParcels, updateParcelStatus } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import type { Parcel } from "../types";

const statuses = ["registered", "scheduled", "out_for_delivery", "delivered", "failed", "cancelled"];

export default function Parcels() {
  const { token } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setParcels(await getParcels(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load parcels.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return parcels.filter((parcel) =>
      (filter === "all" || parcel.status === filter)
      && [parcel.tracking_number,parcel.recipient_name,parcel.city,parcel.pincode].some((value) => value.toLowerCase().includes(normalized)),
    );
  }, [parcels,filter,query]);

  async function changeStatus(parcel: Parcel, status: string) {
    if (!token || status === parcel.status) return;
    setBusyId(parcel.id);
    setError("");
    try {
      const updated = await updateParcelStatus(token, parcel.id, status);
      setParcels((current) => current.map((item) => item.id === parcel.id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update parcel status.");
    } finally {
      setBusyId(null);
    }
  }

  const statusCount = (status: string) => parcels.filter((parcel) => parcel.status === status).length;

  return <div className="parcel-operations-workspace">
    <div className="page-heading parcel-operations-heading">
      <div><div className="eyebrow">OPERATIONS / PARCEL REGISTER</div><h1>Parcel management</h1><p>Monitor parcel movement, find records quickly, and maintain accurate status updates.</p></div>
      <button className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={15}/> Refresh</button>
    </div>

    {error && <div className="alert-error">{error}</div>}

    <section className="parcel-register-summary">
      <div><span>ALL PARCELS</span><strong>{loading ? "—" : parcels.length}</strong></div>
      <div><span>REGISTERED</span><strong>{loading ? "—" : statusCount("registered")}</strong></div>
      <div><span>SCHEDULED</span><strong>{loading ? "—" : statusCount("scheduled")}</strong></div>
      <div><span>OUT FOR DELIVERY</span><strong>{loading ? "—" : statusCount("out_for_delivery")}</strong></div>
      <div><span>DELIVERED</span><strong>{loading ? "—" : statusCount("delivered")}</strong></div>
    </section>

    <section className="parcel-register-toolbar">
      <label className="parcel-register-search"><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tracking ID, recipient, city or PIN" aria-label="Search parcels"/></label>
      <select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter parcels by status">
        <option value="all">All statuses</option>
        {statuses.map((status) => <option key={status} value={status}>{status.replace(/_/g," ")}</option>)}
      </select>
      <span className="parcel-register-count">{filtered.length} results</span>
    </section>

    {loading ? <div className="parcel-register-skeletons">{[1,2,3,4].map((item) => <div className="parcel-register-skeleton" key={item}/>)}</div> :
      filtered.length ? <div className="parcel-register-grid">{filtered.map((parcel) => <article className="parcel-register-card" key={parcel.id}>
        <div className="parcel-register-card-top"><span className="parcel-register-icon"><Package size={18}/></span><div className="parcel-register-id"><small>TRACKING NUMBER</small><strong>{parcel.tracking_number}</strong></div><StatusBadge status={parcel.status}/></div>
        <div className="parcel-register-recipient"><span>RECIPIENT</span><strong>{parcel.recipient_name}</strong><small>{parcel.phone}</small></div>
        <div className="parcel-register-destination"><MapPin size={14}/><span>{parcel.city}, {parcel.state} · {parcel.pincode}</span></div>
        <div className="parcel-register-card-meta"><span><CalendarDays size={13}/> Registered {new Date(parcel.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</span><span>Parcel #{parcel.id}</span></div>
        <div className="parcel-register-status-editor"><label>Update status<select className="status-select" disabled={busyId===parcel.id} value={parcel.status} onChange={(event) => void changeStatus(parcel,event.target.value)}>{statuses.map((status) => <option key={status} value={status}>{status.replace(/_/g," ")}</option>)}</select></label>{busyId===parcel.id&&<span className="parcel-register-saving">Saving…</span>}</div>
      </article>)}</div> : <div className="parcel-register-empty"><EmptyState title="No matching parcels" description="Try another search term or status filter."/></div>
    }
    <p className="page-footnote">Status changes are subject to the server's parcel workflow rules. Use the warehouse and custody workspaces to record physical handovers and returns.</p>
  </div>;
}
