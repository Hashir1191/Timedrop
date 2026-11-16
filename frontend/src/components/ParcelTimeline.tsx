import { useEffect, useState } from "react";
import { AlertCircle, Clock3, RefreshCw } from "lucide-react";
import { getParcelTimeline } from "../api";
import type { ParcelTimelineEvent } from "../types";

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Time unavailable";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function ParcelTimeline({ token, parcelId }: { token: string; parcelId: number }) {
  const [events, setEvents] = useState<ParcelTimelineEvent[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    getParcelTimeline(token, parcelId)
      .then((rows) => {
        if (active) setEvents(rows);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Could not load parcel history.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [token, parcelId, refreshKey]);

  if (loading) {
    return <div className="parcel-timeline-state" role="status" aria-label="Loading parcel activity">
      <span className="parcel-timeline-spinner" aria-hidden="true" />
      <span>Loading parcel activity…</span>
    </div>;
  }

  if (error) {
    return <div className="parcel-timeline-state parcel-timeline-error" role="alert">
      <AlertCircle size={17} />
      <span>{error}</span>
      <button type="button" className="customer-card-action" onClick={() => setRefreshKey((key) => key + 1)}>
        <RefreshCw size={13} /> Try again
      </button>
    </div>;
  }

  if (!events.length) {
    return <div className="parcel-timeline-state">
      <Clock3 size={17} />
      <span>No parcel activity has been recorded yet. New updates will appear here.</span>
    </div>;
  }

  return <div className="parcel-timeline-content">
    <div className="parcel-timeline-toolbar">
      <span>{events.length} {events.length === 1 ? "update" : "updates"}</span>
      <button type="button" className="customer-card-action secondary" onClick={() => setRefreshKey((key) => key + 1)}>
        <RefreshCw size={13} /> Refresh activity
      </button>
    </div>
    <ol className="delivery-timeline parcel-timeline" aria-label="Parcel activity history">
      {events.map((event) => (
        <li key={event.id}>
          <strong>{event.title}</strong>
          <time dateTime={event.created_at}>{formatTimestamp(event.created_at)}</time>
          <p>{event.description}</p>
        </li>
      ))}
    </ol>
  </div>;
}
