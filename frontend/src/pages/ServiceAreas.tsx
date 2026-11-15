import { useEffect, useMemo, useState, type FormEvent } from "react";
import { CheckCircle2, MapPin, Plus, RefreshCw, Search, ShieldCheck, ToggleLeft, ToggleRight } from "lucide-react";
import { createServiceArea, getServiceAreas, updateServiceArea } from "../api";
import { useAuth } from "../auth";
import type { ServiceArea } from "../types";

export default function ServiceAreas() {
  const { token } = useAuth();
  const [areas, setAreas] = useState<ServiceArea[]>([]);
  const [form, setForm] = useState({ pincode: "", city: "", state: "" });
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setAreas(await getServiceAreas(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load service areas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  const filteredAreas = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return areas;
    return areas.filter((area) =>
      area.pincode.includes(query) ||
      area.city.toLowerCase().includes(query) ||
      area.state.toLowerCase().includes(query),
    );
  }, [areas, search]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const created = await createServiceArea(token, {
        pincode: form.pincode.trim(),
        city: form.city.trim(),
        state: form.state.trim(),
      });
      setAreas((current) => [...current, created].sort((a, b) => a.pincode.localeCompare(b.pincode)));
      setForm({ pincode: "", city: "", state: "" });
      setNotice(`PIN code ${created.pincode} is now serviceable.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to add this service area.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleArea(area: ServiceArea) {
    if (!token) return;
    setUpdatingId(area.id);
    setError("");
    setNotice("");
    try {
      const updated = await updateServiceArea(token, area.id, { is_active: !area.is_active });
      setAreas((current) => current.map((item) => item.id === area.id ? updated : item));
      setNotice(updated.is_active
        ? `PIN code ${updated.pincode} is active for new parcel registrations.`
        : `PIN code ${updated.pincode} has been paused for new parcel registrations.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update this service area.");
    } finally {
      setUpdatingId(null);
    }
  }

  const activeCount = areas.filter((area) => area.is_active).length;

  return <div className="service-areas-workspace">
    <div className="page-heading">
      <div><div className="eyebrow">OPERATIONS / COVERAGE</div><h1>Service areas</h1><p>Control which Indian PIN codes customers can use when registering new parcels.</p></div>
      <button type="button" className="secondary-button" onClick={() => void load()} disabled={loading}><RefreshCw size={14}/> Refresh</button>
    </div>
    {error && <div className="alert-error">{error}</div>}
    {notice && <div className="alert-success">{notice}</div>}

    <div className="stats-grid service-area-stats">
      <div className="stat-card"><div className="stat-icon blue"><MapPin size={18}/></div><div className="stat-label">PIN codes configured</div><div className="stat-value">{areas.length}</div><div className="stat-note">Operations-managed coverage records</div></div>
      <div className="stat-card"><div className="stat-icon green"><CheckCircle2 size={18}/></div><div className="stat-label">Active service areas</div><div className="stat-value">{activeCount}</div><div className="stat-note">Accepting new parcel registrations</div></div>
      <div className="stat-card"><div className="stat-icon amber"><ShieldCheck size={18}/></div><div className="stat-label">Paused PIN codes</div><div className="stat-value">{areas.length - activeCount}</div><div className="stat-note">Existing parcels are not affected</div></div>
    </div>

    <section className="panel customer-form-panel service-area-create">
      <div className="panel-heading"><div><h2><Plus size={17}/> Add a service area</h2><p>Register the six-digit PIN code and its city/state reference.</p></div></div>
      <form className="customer-form" onSubmit={submit}>
        <label>PIN code<input required inputMode="numeric" pattern="[1-9][0-9]{5}" minLength={6} maxLength={6} value={form.pincode} onChange={(event) => setForm({ ...form, pincode: event.target.value.replace(/\D/g, "") })} placeholder="6-digit PIN code"/></label>
        <label>City<input required minLength={2} maxLength={100} value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} placeholder="City or delivery area"/></label>
        <label>State<input required minLength={2} maxLength={100} value={form.state} onChange={(event) => setForm({ ...form, state: event.target.value })} placeholder="State"/></label>
        <div className="customer-form-actions"><span>Only add areas TimeDrop is ready and authorized to serve.</span><button className="primary-button" disabled={busy}><Plus size={15}/>{busy ? "Adding area…" : "Add service area"}</button></div>
      </form>
    </section>

    <div className="section-title-row service-area-list-heading"><h2>Configured coverage</h2><span className="result-count">{filteredAreas.length} of {areas.length} PIN codes</span></div>
    <div className="service-area-search"><Search size={16}/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search PIN code, city or state" aria-label="Search service areas"/></div>
    {loading ? <div className="panel table-loading">Loading service areas…</div> : filteredAreas.length ? (
      <div className="panel list-panel"><div className="table-wrap"><table><thead><tr><th>PIN CODE</th><th>CITY</th><th>STATE</th><th>STATUS</th><th>NEW REGISTRATIONS</th></tr></thead><tbody>
        {filteredAreas.map((area) => <tr key={area.id}>
          <td><strong className="cell-strong">{area.pincode}</strong><span className="cell-sub">Area #{area.id}</span></td>
          <td>{area.city}</td><td>{area.state}</td>
          <td><span className={`service-area-status ${area.is_active ? "active" : "paused"}`}><span/>{area.is_active ? "Active" : "Paused"}</span></td>
          <td><button type="button" className="secondary-button service-area-toggle" disabled={updatingId === area.id} onClick={() => void toggleArea(area)}>{area.is_active ? <><ToggleRight size={15}/> Pause area</> : <><ToggleLeft size={15}/> Activate area</>}</button></td>
        </tr>)}
      </tbody></table></div></div>
    ) : <div className="panel service-area-empty"><MapPin size={22}/><strong>{areas.length ? "No matching PIN codes" : "No service areas configured"}</strong><span>{areas.length ? "Try a different PIN code, city or state." : "Add your first supported PIN code above. Customer parcel registration remains unavailable until coverage is configured."}</span></div>}
    <p className="page-footnote">Pausing a PIN code blocks new customer parcel registrations. Existing parcels, bookings and deliveries remain unchanged.</p>
  </div>;
}
