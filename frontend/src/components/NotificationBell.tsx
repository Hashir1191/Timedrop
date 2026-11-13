import { useEffect, useState } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { getNotifications, getUnreadNotificationCount, markAllNotificationsRead, markNotificationRead } from "../api";
import { useAuth } from "../auth";
import type { NotificationItem } from "../types";

export default function NotificationBell() {
  const { token } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [result, unread] = await Promise.all([getNotifications(token), getUnreadNotificationCount(token)]);
      setItems(result);
      setUnreadCount(unread.unread_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load notifications.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [token]);

  async function markRead(id: number) {
    if (!token) return;
    try {
      const updated = await markNotificationRead(token, id);
      setItems((current) => current.map((item) => item.id === id ? updated : item));
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update notification.");
    }
  }

  async function markAllRead() {
    if (!token) return;
    try {
      await markAllNotificationsRead(token);
      setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at || new Date().toISOString() })));
      setUnreadCount(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update notifications.");
    }
  }

  return <div className="notification-control">
    <button className="icon-button notification-trigger" type="button" aria-label="Notifications" aria-expanded={open} onClick={() => { const next = !open; setOpen(next); if (next) void load(); }}>
      <Bell size={18}/>
      {unreadCount > 0 && <span className="notification-count">{unreadCount > 99 ? "99+" : unreadCount}</span>}
    </button>
    {open && <section className="notification-popover" aria-label="Notifications">
      <div className="notification-popover-head"><div><strong>Notifications</strong><span>{unreadCount} unread</span></div><button type="button" className="notification-mark-all" onClick={() => void markAllRead()} disabled={unreadCount === 0}><CheckCheck size={14}/> Mark all read</button></div>
      {error && <p className="notification-error">{error}</p>}
      {loading ? <div className="notification-empty">Loading notifications…</div> : items.length === 0 ? <div className="notification-empty">You're all caught up.</div> : <div className="notification-list">{items.map((item) => <button type="button" key={item.id} className={`notification-item ${item.read_at ? "read" : "unread"}`} onClick={() => !item.read_at && void markRead(item.id)}>
        <span className="notification-dot"/><span className="notification-copy"><strong>{item.title}</strong><span>{item.message}</span><small>{new Date(item.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</small></span>
      </button>)}</div>}
      <button type="button" className="notification-close" onClick={() => setOpen(false)}>Close</button>
    </section>}
  </div>;
}
