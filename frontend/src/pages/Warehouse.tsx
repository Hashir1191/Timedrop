import { useEffect, useState } from "react";
import { MapPin, Package, PackageCheck, RefreshCw, Search, Warehouse, AlertTriangle, Truck, CheckCircle2 } from "lucide-react";
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

export default function WarehousePage() {
  const { token } = useAuth();
  const [parcels, setParcels] = useState<Parcel[]>([]);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof getWarehouseSummary>> | null>(null);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [location, setLocation] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function refresh() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [stats, rows] = await Promise.all([
        getWarehouseSummary(token),
        getWarehouseParcels(token, { q: query, status, location }),
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

  async function changeLocation(parcel: Parcel) {
    if (!token) return;
    const current = parcel.warehouse_location || "";
    const entered = window.prompt(
      `Set storage bin for ${parcel.tracking_number}. Leave blank to clear the bin assignment.`,
      current,
    );
    if (entered === null) return;
    const next = entered.trim() || null;
    if (next && next.length > 40) {
      setError("Storage location must be 40 characters or fewer.");
      return;
    }
    setBusyId(parcel.id);
    setError("");
    setSuccess("");
    try {
      await updateWarehouseLocation(token, parcel.id, next);
      setSuccess(next ? `Storage location updated to ${next}.` : "Storage location cleared.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update storage location.");
    } finally {
      setBusyId(null);
    }
  }

  return <>
    <div className="page-heading">
      <div>
        <div className="eyebrow">WAREHOUSE OPERATIONS</div>
        <h1>Warehouse management</h1>
        <p>Monitor parcels in custody, assign storage bins, and find inventory quickly.</p>
      </div>
      <button className="secondary-button" onClick={() => void refresh()} disabled={loading}>
        <RefreshCw size={15} /> Refresh
      </button>
    </div>
    {error && <div className="alert-error">{error}</div>}
    {success && <div className="alert-success">{success}</div>}
    <div className="stats-grid">
      <Stat icon={Package} label="Total parcels" value={summary?.total_parcels} note="Across all delivery stages" />
      <Stat icon={Warehouse} label="In operations custody" value={summary?.in_custody} note="Physically received by operations" />
      <Stat icon={MapPin} label="Assigned to bins" value={summary?.assigned_to_bins} note="Storage location recorded" />
      <Stat icon={PackageCheck} label="Awaiting storage" value={summary?.awaiting_storage} note="In custody without a bin" />
      <Stat icon={AlertTriangle} label="Damaged / opened" value={summary?.damaged_or_opened} note="Latest custody inspection" />
      <Stat icon={Truck} label="Out for delivery" value={summary?.out_for_delivery} note="Currently with delivery partners" />
      <Stat icon={CheckCircle2} label="Delivered" value={summary?.delivered} note="Successfully completed" />
      <Stat icon={AlertTriangle} label="Failed deliveries" value={summary?.failed} note="Requires operations follow-up" />
    </div>
    <section className="panel list-panel">
      <div className="panel-heading" style={{ padding: "20px 20px 0" }}>
        <div><h2>Parcel inventory</h2><p>Search by tracking number, recipient, city, or PIN code. Maximum 200 results.</p></div>
      </div>
      <div className="list-toolbar">
        <div className="search-box"><Search size={15}/><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search parcels..." aria-label="Search parcels"/></div>
        <select value={status} onChange={event => setStatus(event.target.value)} aria-label="Filter by status">
          {statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select value={location} onChange={event => setLocation(event.target.value)} aria-label="Filter by storage location">
          <option value="">All locations</option>
          <option value="unassigned">Awaiting storage</option>
        </select>
        <span className="result-count">{loading ? "Loading..." : `${parcels.length} parcels`}</span>
      </div>
      {parcels.length ? <div className="table-wrap">
        <table>
          <thead><tr><th>TRACKING ID</th><th>RECIPIENT</th><th>DESTINATION</th><th>STATUS</th><th>STORAGE BIN</th><th>CREATED</th><th>ACTION</th></tr></thead>
          <tbody>{parcels.map(parcel => <tr key={parcel.id}>
            <td className="tracking">{parcel.tracking_number}</td>
            <td><span className="cell-strong">{parcel.recipient_name}</span><span className="cell-sub">{parcel.phone}</span></td>
            <td>{parcel.city}, {parcel.state}<span className="cell-sub">{parcel.pincode}</span></td>
            <td><StatusBadge status={parcel.status}/></td>
            <td>{parcel.warehouse_location || <span className="cell-sub">Not assigned</span>}</td>
            <td>{new Date(parcel.created_at).toLocaleDateString("en-IN")}</td>
            <td><button className="text-link" disabled={busyId === parcel.id} onClick={() => void changeLocation(parcel)}>{busyId === parcel.id ? "Saving..." : "Set bin"}</button></td>
          </tr>)}</tbody>
        </table>
      </div> : !loading ? <EmptyState title="No matching parcels" description="Try changing the search text or filters."/> : <div className="table-loading">Loading warehouse inventory...</div>}
    </section>
    <p className="page-footnote">Storage-bin updates are available only while the latest custody event shows the parcel is physically in TimeDrop operations custody. Use a consistent location format, for example A-01-02.</p>
  </>;
}

function Stat({ icon: Icon, label, value, note }: { icon: typeof Package; label: string; value?: number; note: string }) {
  return <div className="stat-card">
    <div className="stat-icon blue"><Icon size={19}/></div>
    <div className="stat-label">{label}</div>
    <div className="stat-value">{value ?? "—"}</div>
    <div className="stat-note">{note}</div>
  </div>;
}
