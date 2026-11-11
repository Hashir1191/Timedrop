import { useEffect, useState } from "react";
import { getAssignmentEvents } from "../api";
import type { DeliveryEvent } from "../types";

export default function DeliveryTimeline({ token, assignmentId }: { token: string; assignmentId: number }) {
  const [events, setEvents] = useState<DeliveryEvent[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    getAssignmentEvents(token, assignmentId)
      .then(data => { if (active) setEvents(data); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : "Could not load history."); });
    return () => { active = false; };
  }, [token, assignmentId]);
  if (error) return <p className="alert-error">{error}</p>;
  if (!events.length) return <p className="muted-copy">No recorded events yet.</p>;
  return <ol className="delivery-timeline">{events.map(event =>
    <li key={event.id}>
      <strong>{event.to_status.replace(/_/g, " ")}</strong>
      <span>{event.actor_name} · {new Date(event.created_at).toLocaleString("en-IN")}</span>
      {event.note && <p>{event.note}</p>}
    </li>
  )}</ol>;
}
