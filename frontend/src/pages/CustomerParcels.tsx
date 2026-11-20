import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, CalendarClock, Clock3, Package, Plus, RefreshCw, Search, ShieldCheck, Truck } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { getParcels, issueDeliveryCode, getMyTracking } from "../api";
import { useAuth } from "../auth";
import EmptyState from "../components/EmptyState";
import StatusBadge from "../components/StatusBadge";
import ParcelTimeline from "../components/ParcelTimeline";
import type { DeliveryAssignment, Parcel } from "../types";

type Filter = "all" | "active" | "delivered" | "failed" | "cancelled";

const TRACKING_REFRESH_MS = 60_000;

function formatEtaWindow(start: string, end: string): string | null {
  const startDate = new Date(start);
  const endDate = new Date(end);
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime()) || endDate < startDate) return null;
  const dateFormatter = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" });
  const timeFormatter = new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit" });
  const startLabel = `${dateFormatter.format(startDate)}, ${timeFormatter.format(startDate)}`;
  const endLabel = dateFormatter.format(startDate) === dateFormatter.format(endDate) ? timeFormatter.format(endDate) : `${dateFormatter.format(endDate)}, ${timeFormatter.format(endDate)}`;
  return `${startLabel} – ${endLabel}`;
}

function formatRefreshTime(value: Date): string {
  return new Intl.DateTimeFormat("en-IN", { hour: "2-digit", minute: "2-digit" }).format(value);
}

export default function CustomerParcels() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const focusParcelId = Number(searchParams.get("parcelId"));
  const [codes, setCodes] = useState<Record<number, {code:string;expires_at:string}>>({});
  const [codeBusy, setCodeBusy] = useState<number|null>(null);
  const [codeError, setCodeError] = useState("");
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [tracking, setTracking] = useState<DeliveryAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState("");
  const requestInFlight = useRef(false);
  const requestSequence = useRef(0);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");

  const load = useCallback(async (silent = false) => {
    if (!token || requestInFlight.current) return;
    requestInFlight.current = true;
    const requestId = ++requestSequence.current;
    if (silent) setRefreshing(true); else setLoading(true);
    setError("");
    try {
      const [parcelRows, trackingRows] = await Promise.all([getParcels(token), getMyTracking(token)]);
      if (requestId !== requestSequence.current) return;
      setParcels(parcelRows);
      setTracking(trackingRows);
      setLastUpdated(new Date());
    } catch (err) {
      if (requestId === requestSequence.current) setError(err instanceof Error ? err.message : "Unable to load parcels.");
    } finally {
      requestInFlight.current = false;
      if (requestId === requestSequence.current) { setLoading(false); setRefreshing(false); }
    }
  }, [token]);

  useEffect(() => {
    void load();
    const refreshWhenVisible = () => { if (document.visibilityState === "visible") void load(true); };
    const intervalId = window.setInterval(() => { if (document.visibilityState === "visible") void load(true); }, TRACKING_REFRESH_MS);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      requestSequence.current += 1;
      requestInFlight.current = false;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [load]);

  async function generateCode(parcelId: number) {
    if (!token) return;
    setCodeBusy(parcelId);
    setCodeError("");
    try {
      const result = await issueDeliveryCode(token, parcelId);
      setCodes((current) => ({...current, [parcelId]: result}));
    } catch (err) {
      setCodeError(err instanceof Error ? err.message : "Unable to generate delivery code.");
    } finally {
      setCodeBusy(null);
    }
  }

  const trackingByParcel = useMemo(
    () => new Map(tracking.map((item) => [item.parcel_id, item])),
    [tracking],
  );
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return parcels.filter((parcel) => {
      const matchesQuery = !normalized || [parcel.tracking_number, parcel.recipient_name, parcel.city, parcel.pincode]
        .some((value) => value.toLowerCase().includes(normalized));
      const matchesFilter = filter === "all"
        || (filter === "active" && !["delivered","failed","cancelled"].includes(parcel.status))
        || parcel.status === filter;
      return matchesQuery && matchesFilter;
    });
  }, [parcels, query, filter]);

  return <div className="customer-parcels-page">
    <div className="page-heading customer-list-heading">
      <div><div className="eyebrow">YOUR DELIVERY HISTORY</div><h1>My parcels</h1><p>Follow every parcel from registration through delivery.</p></div>
      <div className="customer-heading-actions"><button className="secondary-button" onClick={() => void load()} disabled={loading || refreshing}><RefreshCw size={15} className={refreshing ? "tracking-refresh-icon" : undefined}/> {refreshing ? "Updating…" : "Refresh"}</button><Link className="primary-button" to="/new-parcel"><Plus size={16}/> New parcel</Link></div>
    </div>

    {error && <div className="alert-error customer-tracking-error" role="alert"><span>{error}</span><button type="button" className="secondary-button" onClick={() => void load()} disabled={loading || refreshing}>Try again</button></div>}
    {codeError && <div className="alert-error">{codeError}</div>}
    {lastUpdated && <p className="customer-tracking-updated" role="status">Tracking last updated at {formatRefreshTime(lastUpdated)} · Refreshes automatically while this page is open</p>}

    <section className="customer-parcel-toolbar">
      <label className="customer-search"><Search size={17}/><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tracking number, recipient or city" aria-label="Search parcels"/></label>
      <div className="customer-filter-tabs" aria-label="Filter parcels">
        {(["all","active","delivered","failed","cancelled"] as Filter[]).map((value) => <button key={value} type="button" className={filter===value?"active":""} onClick={() => setFilter(value)}>{value==="all"?"All parcels":value==="active"?"In progress":value==="delivered"?"Delivered":value==="failed"?"Failed":"Cancelled"}</button>)}
      </div>
      <span className="customer-results-count">{filtered.length} {filtered.length===1?"parcel":"parcels"}</span>
    </section>

    {loading ? <div className="customer-parcel-skeletons">{[1,2,3].map((item) => <div className="customer-parcel-skeleton" key={item}/>)}</div> :
      filtered.length ? <div className="customer-parcel-list">{filtered.map((parcel) => {
        const assignment = trackingByParcel.get(parcel.id);
        const canManage = !["delivered","failed","cancelled"].includes(parcel.status);
        return <article className={`customer-parcel-card ${focusParcelId===parcel.id?"notification-target-row":""}`} key={parcel.id} id={`parcel-${parcel.id}`}>
          <div className="customer-parcel-card-main">
            <div className="customer-parcel-card-top">
              <span className="customer-parcel-card-icon"><Package size={20}/></span>
              <div className="customer-parcel-card-id"><span>TRACKING NUMBER</span><strong>{parcel.tracking_number}</strong></div>
              <StatusBadge status={parcel.status}/>
            </div>
            <div className="customer-parcel-card-details">
              <div><span>Recipient</span><strong>{parcel.recipient_name}</strong></div>
              <div><span>Destination</span><strong>{parcel.city}, {parcel.state}</strong><small>{parcel.pincode}</small></div>
              <div><span>Registered</span><strong>{new Date(parcel.created_at).toLocaleDateString("en-IN",{day:"numeric",month:"short",year:"numeric"})}</strong></div>
            </div>
            <div className="customer-parcel-card-footer">
              <div className="customer-parcel-eta">
                {assignment?.estimated_delivery_start && assignment.estimated_delivery_end && formatEtaWindow(assignment.estimated_delivery_start, assignment.estimated_delivery_end) ? <><Clock3 size={14}/><span>Estimated arrival <strong>{formatEtaWindow(assignment.estimated_delivery_start, assignment.estimated_delivery_end)}</strong></span></> :
                  assignment ? <><Clock3 size={14}/><span>Delivery estimate <strong>Awaiting a confirmed time window</strong></span></> :
                  <><ShieldCheck size={14}/><span>Delivery updates <strong>Shown here as they become available</strong></span></>}
              </div>
              <div className="customer-parcel-actions">
                {canManage && <Link className="customer-card-action" to={`/schedule/${parcel.id}`}><CalendarClock size={15}/>{parcel.status==="scheduled"?"Manage slot":"Book a slot"}</Link>}
                {parcel.status==="out_for_delivery" && <button className="customer-card-action secondary" disabled={codeBusy===parcel.id} onClick={() => void generateCode(parcel.id)}>{codeBusy===parcel.id?"Generating…":"Get delivery code"}</button>}
                {codes[parcel.id] && <span className="customer-delivery-code"><strong>{codes[parcel.id].code}</strong><small>Expires {new Date(codes[parcel.id].expires_at).toLocaleTimeString("en-IN")}</small></span>}
              </div>
            </div>
          </div>
          <details className="customer-parcel-history"><summary><span><Truck size={15}/> View parcel activity</span><span className="customer-history-hint">Registration, booking and delivery updates <ArrowRight size={13}/></span></summary>
            {token && <ParcelTimeline token={token} parcelId={parcel.id}/>}
          </details>
        </article>;
      })}</div> : parcels.length ? <div className="customer-empty-panel"><EmptyState title="No matching parcels" description="Try a different search or filter to find your parcel."/></div> : <div className="customer-empty-panel"><EmptyState title="No parcels registered" description="Create your first parcel to see its delivery progress here."/><Link className="primary-button" to="/new-parcel"><Plus size={16}/> Create a parcel</Link></div>
    }
  </div>;
}
