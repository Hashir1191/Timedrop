import { CalendarClock, Package, Smartphone } from "lucide-react";
import WorkspaceShell, { type WorkspaceLink } from "./WorkspaceShell";
const links: WorkspaceLink[] = [{to:"/",label:"My deliveries",icon:Package,end:true},{to:"/phone-settings",label:"Phone & SMS",icon:Smartphone},{to:"/availability",label:"Availability",icon:CalendarClock}];
export default function PartnerLayout(){ return <WorkspaceShell role="delivery_partner" links={links} footer="TIMEDROP · DELIVERY PARTNER"/>; }
