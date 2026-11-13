import { useEffect, useMemo, useState } from "react";
import { AlertCircle, CalendarClock, Check, Clock3, Plus, Save, ShieldCheck, Trash2 } from "lucide-react";
import { getMyAvailability, updateMyAvailability, type PartnerAvailabilityWindow } from "../api";
import { useAuth } from "../auth";

const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function PartnerAvailability() {
  const { token } = useAuth();
  const [enabled, setEnabled] = useState(false);
  const [windows, setWindows] = useState<PartnerAvailabilityWindow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const result = await getMyAvailability(token);
      setEnabled(result.enabled);
      setWindows(result.windows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load your availability.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [token]);

  const activeDays = useMemo(
    () => new Set(windows.filter((item) => item.is_active).map((item) => item.weekday)).size,
    [windows],
  );

  function updateWindow(index: number, patch: Partial<PartnerAvailabilityWindow>) {
    setWindows((current) => current.map((item, i) => i === index ? { ...item, ...patch } : item));
    setNotice("");
  }

  function addWindow(weekday: number) {
    setWindows((current) => [...current, {
      weekday, start_time: "13:00:00", end_time: "17:00:00", is_active: true,
    }].sort((a, b) => a.weekday - b.weekday || a.start_time.localeCompare(b.start_time)));
    setNotice("");
  }

  function removeWindow(index: number) {
    setWindows((current) => current.filter((_, i) => i !== index));
    setNotice("");
  }

  async function save() {
    if (!token) return;
    for (let weekday = 0; weekday < 7; weekday += 1) {
      const dayWindows = windows.filter((item) => item.weekday === weekday).sort((a, b) => a.start_time.localeCompare(b.start_time));
      for (let index = 0; index < dayWindows.length; index += 1) {
        if (dayWindows[index].end_time <= dayWindows[index].start_time) {
          setError(`${days[weekday]}: the end time must be later than the start time.`);
          return;
        }
        if (index > 0 && dayWindows[index].start_time < dayWindows[index - 1].end_time) {
          setError(`${days[weekday]}: availability windows cannot overlap.`);
          return;
        }
      }
    }
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const result = await updateMyAvailability(token, { enabled, windows });
      setEnabled(result.enabled);
      setWindows(result.windows);
      setNotice("Your weekly availability has been saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save your availability.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="panel availability-loading"><div className="loader" /><span>Loading your weekly schedule…</span></div>;

  return <section className="availability-page">
    <div className="page-heading availability-heading">
      <div>
        <div className="eyebrow">DELIVERY WORKSPACE / PREFERENCES</div>
        <h1>Working availability</h1>
        <p>Set the days and time windows when you can receive delivery assignments.</p>
      </div>
      <div className={`availability-state ${enabled ? "is-enabled" : ""}`}>
        <span className="availability-state-dot" />
        {enabled ? "Schedule active" : "Schedule not enforced"}
      </div>
    </div>

    {error && <div className="alert-error availability-alert"><AlertCircle size={16} />{error}</div>}
    {notice && <div className="alert-success availability-alert"><Check size={16} />{notice}</div>}

    <div className="panel availability-intro">
      <div className="availability-intro-icon"><CalendarClock size={22} /></div>
      <div className="availability-intro-copy">
        <strong>Use a schedule that works for you</strong>
        <span>Operations will only assign new deliveries that fit fully inside one of your active time windows.</span>
      </div>
      <label className="availability-switch">
        <input type="checkbox" checked={enabled} onChange={(event) => { setEnabled(event.target.checked); setNotice(""); }} />
        <span className="availability-switch-track" />
        <span>{enabled ? "Enabled" : "Disabled"}</span>
      </label>
    </div>

    <div className="availability-summary">
      <div className="availability-summary-item">
        <span className="availability-summary-icon"><CalendarClock size={17}/></span>
        <div><strong>{activeDays} of 7</strong><span>Days with availability</span></div>
      </div>
      <div className="availability-summary-item">
        <span className="availability-summary-icon"><Clock3 size={17}/></span>
        <div><strong>{windows.filter((item) => item.is_active).length}</strong><span>Active time windows</span></div>
      </div>
      <div className="availability-summary-item">
        <span className="availability-summary-icon"><ShieldCheck size={17}/></span>
        <div><strong>{enabled ? "Protected" : "Flexible"}</strong><span>Assignment matching</span></div>
      </div>
    </div>

    <div className="availability-section-head">
      <div><h2>Your weekly schedule</h2><p>Times use the local delivery-slot timezone.</p></div>
      <span className="availability-timezone">24-hour time</span>
    </div>

    <div className="availability-days">
      {days.map((day, weekday) => {
        const dayWindows = windows.map((item, index) => ({ ...item, index })).filter((item) => item.weekday === weekday);
        return <article className="panel availability-day" key={day}>
          <div className="availability-day-head">
            <div className="availability-day-name">
              <span className="availability-day-indicator" />
              <strong>{day}</strong>
              <span>{dayWindows.filter((item) => item.is_active).length ? `${dayWindows.filter((item) => item.is_active).length} window(s)` : "No hours set"}</span>
            </div>
            <button type="button" className="availability-add" onClick={() => addWindow(weekday)}><Plus size={15}/> Add hours</button>
          </div>
          {dayWindows.length === 0 ? (
            <div className="availability-empty">No availability windows for this day.</div>
          ) : (
            <div className="availability-window-list">
              {dayWindows.map((item) => <div className={`availability-window ${item.is_active ? "" : "is-paused"}`} key={item.index}>
                <label className="availability-window-toggle" title="Include this time window">
                  <input type="checkbox" checked={item.is_active} onChange={(event) => updateWindow(item.index, { is_active: event.target.checked })}/>
                  <span />
                </label>
                <label className="availability-time-field">
                  <span>From</span>
                  <input type="time" value={item.start_time.slice(0, 5)} onChange={(event) => updateWindow(item.index, { start_time: event.target.value + ":00" })}/>
                </label>
                <span className="availability-time-separator">to</span>
                <label className="availability-time-field">
                  <span>Until</span>
                  <input type="time" value={item.end_time.slice(0, 5)} onChange={(event) => updateWindow(item.index, { end_time: event.target.value + ":00" })}/>
                </label>
                <button type="button" className="availability-remove" title={`Remove ${day} window`} onClick={() => removeWindow(item.index)}><Trash2 size={16}/></button>
              </div>)}
            </div>
          )}
        </article>;
      })}
    </div>

    {enabled && windows.filter((item) => item.is_active).length === 0 && (
      <div className="availability-warning"><AlertCircle size={17}/><span><strong>No active hours configured.</strong> With the schedule enabled, you will not receive new assignments until you add at least one active time window.</span></div>
    )}

    <div className="availability-footer">
      <p>Changing your schedule affects future assignments only. Existing deliveries remain assigned.</p>
      <button type="button" className="primary-button" onClick={save} disabled={saving}>
        <Save size={16}/>{saving ? "Saving schedule…" : "Save availability"}
      </button>
    </div>
  </section>;
}
