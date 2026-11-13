import { useEffect, useState } from "react";
import { getParcelTimeline } from "../api";
import type { ParcelTimelineEvent } from "../types";

export default function ParcelTimeline({ token, parcelId }: { token: string; parcelId: number }) {
  const [events, setEvents] = useState<ParcelTimelineEvent[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    getParcelTimeline(token, parcelId)
      .then(rows => { if (active) setEvents(rows); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : "Could not load parcel history."); });
    return () => { active = false; };
  }, [token, parcelId]);
  if (error) return <p className="alert-error">{error}</p>;
  if (!events.length) return <p className="muted-copy">No parcel activity has been recorded yet.</p>;
  return <ol className="delivery-timeline parcel-timeline">{events.map(event =>
    <li key={event.id}>
      <strong>{event.title}</strong>
      <span>{new Date(event.created_at).toLocaleString("en-IN")}</span>
      <p>{event.description}</p>
    </li>
  )}</ol>;
}
