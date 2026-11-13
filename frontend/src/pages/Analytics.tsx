import { useEffect, useMemo, useState } from "react";
import { Activity, CalendarDays, CheckCircle2, Clock3, Package, RefreshCw, TrendingUp, Truck, XCircle } from "lucide-react";
import { getOperationsAnalytics } from "../api";
import { useAuth } from "../auth";
import type { OperationsAnalytics } from "../types";
import EmptyState from "../components/EmptyState";

function localDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function Analytics() {
  const { token } = useAuth();
  const [endDate, setEndDate] = useState(localDate(new Date()));
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 29);
    return localDate(date);
  });
  const [data, setData] = useState<OperationsAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setData(await getOperationsAnalytics(token, startDate, endDate));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load operations analytics.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  const maxDaily = useMemo(
    () => Math.max(1, ...(data?.daily.map(day => day.assigned) ?? [])),
    [data],
  );

  return <>
    <div className="page-heading">
      <div>
        <div className="eyebrow">PERFORMANCE & INSIGHTS</div>
        <h1>Operations analytics</h1>
        <p>Delivery outcomes, workload, and partner performance from recorded activity.</p>
      </div>
      <button className="secondary-button" onClick={() => void load()} disabled={loading}>
        <RefreshCw size={15}/> Refresh
      </button>
    </div>

    <section className="panel analytics-filters">
      <div className="analytics-date-field"><label htmlFor="analytics-start">From</label><input id="analytics-start" type="date" value={startDate} max={endDate} onChange={event => setStartDate(event.target.value)}/></div>
      <div className="analytics-date-field"><label htmlFor="analytics-end">To</label><input id="analytics-end" type="date" value={endDate} min={startDate} onChange={event => setEndDate(event.target.value)}/></div>
      <button className="primary-button" onClick={() => void load()} disabled={loading || !startDate || !endDate || startDate > endDate}>
        <CalendarDays size={15}/> Apply range
      </button>
      <span className="analytics-range-note">Up to 366 days · Inclusive dates</span>
    </section>

    {error && <div className="alert-error">{error}</div>}
    {loading && !data ? <div className="table-loading">Loading analytics...</div> : data && <>
      <div className="analytics-section-heading"><div><h2>Delivery overview</h2><p>{new Date(data.start_date + "T00:00:00").toLocaleDateString("en-IN")} – {new Date(data.end_date + "T00:00:00").toLocaleDateString("en-IN")}</p></div></div>
      <div className="stats-grid analytics-stats">
        <Metric icon={Package} label="Parcels created" value={data.parcels_created} note="Registered in selected period"/>
        <Metric icon={Truck} label="Assignments" value={data.assignments_created} note="Partner assignments created"/>
        <Metric icon={CheckCircle2} label="Delivered" value={data.delivered} note="Completed successfully"/>
        <Metric icon={XCircle} label="Failed" value={data.failed} note="Recorded failed outcomes"/>
        <Metric icon={Activity} label="Active deliveries" value={data.active} note="Assigned, accepted or out for delivery"/>
        <Metric icon={TrendingUp} label="Success rate" value={`${data.success_rate}%`} note="Delivered ÷ delivered + failed"/>
        <Metric icon={Clock3} label="Average delivery time" value={data.average_delivery_hours === null ? "—" : `${data.average_delivery_hours}h`} note="Delivered assignments only"/>
        <Metric icon={Truck} label="Partners active" value={data.partner_count} note="Partners with assignments in range"/>
      </div>

      <section className="panel analytics-panel">
        <div className="panel-heading"><div><h2>Daily delivery activity</h2><p>Assignments created and recorded delivery outcomes by day</p></div></div>
        {data.daily.length ? <div className="daily-analytics-list">
          {data.daily.map(day => <div className="daily-analytics-row" key={day.day}>
            <span className="daily-date">{new Date(day.day + "T00:00:00").toLocaleDateString("en-IN", {day:"2-digit",month:"short"})}</span>
            <div className="daily-bars">
              <div className="daily-bar-track"><div className="daily-bar assigned" style={{width:`${day.assigned / maxDaily * 100}%`}}/></div>
              <div className="daily-bar-track"><div className="daily-bar delivered" style={{width:`${day.delivered / maxDaily * 100}%`}}/></div>
              <div className="daily-bar-track"><div className="daily-bar failed" style={{width:`${day.failed / maxDaily * 100}%`}}/></div>
            </div>
            <span className="daily-counts">{day.assigned} / {day.delivered} / {day.failed}</span>
          </div>)}
          <div className="daily-legend"><span><i className="legend-dot assigned"/>Assigned</span><span><i className="legend-dot delivered"/>Delivered</span><span><i className="legend-dot failed"/>Failed</span><small>Assigned / delivered / failed</small></div>
        </div> : <EmptyState title="No activity in this range" description="Try a wider date range to view delivery activity."/>}
      </section>

      <section className="panel analytics-panel">
        <div className="panel-heading"><div><h2>Delivery partner performance</h2><p>Ranked by delivered volume, then assignment count</p></div></div>
        {data.partners.length ? <div className="table-wrap">
          <table><thead><tr><th>PARTNER</th><th>ASSIGNMENTS</th><th>DELIVERED</th><th>FAILED</th><th>ACTIVE</th><th>SUCCESS RATE</th><th>AVG. HOURS</th></tr></thead>
            <tbody>{data.partners.map(partner => <tr key={partner.partner_id}>
              <td><span className="cell-strong">{partner.partner_name}</span></td>
              <td>{partner.total_assignments}</td><td>{partner.delivered}</td><td>{partner.failed}</td><td>{partner.active}</td>
              <td><span className={partner.success_rate >= 80 ? "performance-good" : partner.success_rate > 0 ? "performance-watch" : "cell-sub"}>{partner.success_rate}%</span></td>
              <td>{partner.average_delivery_hours === null ? "—" : `${partner.average_delivery_hours}h`}</td>
            </tr>)}</tbody>
          </table>
        </div> : <EmptyState title="No partner assignments" description="Partner performance will appear once assignments are created in this date range."/>}
      </section>
      <p className="page-footnote">Metrics reflect records currently stored in TimeDrop. Success rate excludes active assignments. Failed outcomes are dated using the assignment's last update because a dedicated failure timestamp is not yet stored. Average delivery time is calculated only when a delivered timestamp exists; this is an operational report, not a live tracking feed.</p>
    </>}
  </>;
}

function Metric({icon:Icon,label,value,note}:{icon:typeof Package;label:string;value:string|number;note:string}) {
  return <div className="stat-card"><div className="stat-icon blue"><Icon size={19}/></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>;
}
