import { useEffect, useMemo, useState } from "react";
import { Search, RefreshCw } from "lucide-react";
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
  const [busyId, setBusyId] = useState<number | null>(null);
  async function load() { if (!token) return; try { setError(""); setParcels(await getParcels(token)); } catch (err) { setError(err instanceof Error ? err.message : "Unable to load parcels."); } }
  useEffect(() => { void load(); }, [token]);
  const filtered = useMemo(() => parcels.filter((p) => (filter === "all" || p.status === filter) && [p.tracking_number, p.recipient_name, p.city, p.pincode].some((v) => v.toLowerCase().includes(query.toLowerCase()))), [parcels, filter, query]);
  async function changeStatus(parcel: Parcel, status: string) {
    if (!token) return; setBusyId(parcel.id); setError("");
    try { const updated = await updateParcelStatus(token, parcel.id, status); setParcels((old) => old.map((p) => p.id === parcel.id ? updated : p)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not update status."); }
    finally { setBusyId(null); }
  }
  return <><div className="page-heading"><div><div className="eyebrow">PARCEL OPERATIONS</div><h1>Parcels</h1><p>Search, monitor, and update parcel progress.</p></div><button className="secondary-button" onClick={() => void load()}><RefreshCw size={15} /> Refresh</button></div>
    {error && <div className="alert-error">{error}</div>}
    <div className="panel list-panel"><div className="list-toolbar"><div className="search-box"><Search size={17} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search tracking ID, recipient or city..." /></div><select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All statuses</option>{statuses.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select><span className="result-count">{filtered.length} parcels</span></div>
    {filtered.length ? <div className="table-wrap"><table><thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>CREATED</th><th>STATUS</th><th>UPDATE STATUS</th></tr></thead><tbody>{filtered.map((p) => <tr key={p.id}><td className="tracking">{p.tracking_number}</td><td><strong className="cell-strong">{p.recipient_name}</strong><span className="cell-sub">{p.phone}</span></td><td>{p.city}, {p.state}<span className="cell-sub">{p.pincode}</span></td><td>{new Date(p.created_at).toLocaleDateString("en-IN")}</td><td><StatusBadge status={p.status} /></td><td><select className="status-select" disabled={busyId === p.id} value={p.status} onChange={(e) => void changeStatus(p, e.target.value)}>{statuses.map((s) => <option key={s} value={s}>{s.replaceAll("_", " ")}</option>)}</select></td></tr>)}</tbody></table></div> : <EmptyState title="No matching parcels" description="Try a different search or status filter." />}</div></>;
}