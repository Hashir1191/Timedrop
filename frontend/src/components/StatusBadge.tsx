const labels: Record<string, string> = {
  registered: "Registered",
  scheduled: "Scheduled",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  failed: "Failed",
  cancelled: "Cancelled",
};
export default function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}><span />{labels[status] || status}</span>;
}