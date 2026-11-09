import { PackageOpen } from "lucide-react";
export default function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><div className="empty-icon"><PackageOpen size={22} /></div><strong>{title}</strong><span>{description}</span></div>;
}