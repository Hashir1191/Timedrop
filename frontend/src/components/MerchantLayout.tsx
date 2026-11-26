import { LayoutDashboard, Package, PlusCircle, Settings } from "lucide-react";
import WorkspaceShell, { type WorkspaceLink } from "./WorkspaceShell";
const links: WorkspaceLink[] = [{to:"/",label:"Overview",icon:LayoutDashboard,end:true},{to:"/shipments",label:"Shipments",icon:Package},{to:"/new-shipment",label:"Create shipment",icon:PlusCircle},{to:"/phone-settings",label:"Account settings",icon:Settings}];
export default function MerchantLayout(){ return <WorkspaceShell role="merchant" links={links} footer="TIMEDROP · MERCHANT"/>; }
