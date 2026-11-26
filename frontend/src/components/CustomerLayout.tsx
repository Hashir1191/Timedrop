import { LayoutDashboard, Package, PlusCircle, Smartphone, LifeBuoy } from "lucide-react";
import WorkspaceShell, { type WorkspaceLink } from "./WorkspaceShell";
const links: WorkspaceLink[] = [{to:"/",label:"Overview",icon:LayoutDashboard,end:true},{to:"/my-parcels",label:"My parcels",icon:Package},{to:"/new-parcel",label:"Create parcel",icon:PlusCircle},{to:"/phone-settings",label:"Phone & SMS",icon:Smartphone},{to:"/support",label:"Support centre",icon:LifeBuoy}];
export default function CustomerLayout(){ return <WorkspaceShell role="customer" links={links} footer="TIMEDROP · CUSTOMER"/>; }
