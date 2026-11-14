import { useMemo, useState } from "react";
import { MapPin, Navigation2 } from "lucide-react";
import type { DeliveryRouteStop } from "../types";

type RouteGroup = { key:string; partnerName:string; mapUrl:string|null; stops:DeliveryRouteStop[] };
type Point = { stop:DeliveryRouteStop; x:number; y:number; order:number; groupKey:string; partnerName:string };
const WIDTH=760, HEIGHT=380, PAD=43;
const colors=["#4569e8","#16a085","#a855f7","#e68b32","#cf4f75","#2788aa"];

export default function RouteVisualization({groups}:{groups:RouteGroup[]}) {
  const [selectedGroup,setSelectedGroup]=useState("all");
  const [selectedParcel,setSelectedParcel]=useState<number|null>(null);
  const groupsWithCoordinates=useMemo(()=>groups.map(group=>({
    ...group, stops:group.stops.filter(stop=>stop.latitude!==null&&stop.longitude!==null&&Number.isFinite(stop.latitude)&&Number.isFinite(stop.longitude)&&Math.abs(stop.latitude!)<=90&&Math.abs(stop.longitude!)<=180)
  })).filter(group=>group.stops.length>0),[groups]);
  const visibleGroups=selectedGroup==="all"?groupsWithCoordinates:groupsWithCoordinates.filter(group=>group.key===selectedGroup);
  const points=useMemo(()=>{
    const raw=visibleGroups.flatMap(group=>group.stops.map((stop,index)=>({stop,order:stop.route_sequence??index+1,groupKey:group.key,partnerName:group.partnerName})));
    if(!raw.length)return [] as Point[];
    const latitudes=raw.map(item=>item.stop.latitude!), longitudes=raw.map(item=>item.stop.longitude!);
    const minLat=Math.min(...latitudes),maxLat=Math.max(...latitudes),minLon=Math.min(...longitudes),maxLon=Math.max(...longitudes);
    const latRange=Math.max(maxLat-minLat,.005),lonRange=Math.max(maxLon-minLon,.005);
    const centerLat=(maxLat+minLat)/2,centerLon=(maxLon+minLon)/2;
    const longitudeCorrection=Math.max(.15,Math.cos(centerLat*Math.PI/180));
    const spanX=lonRange*longitudeCorrection,spanY=latRange;
    const scale=Math.min((WIDTH-2*PAD)/spanX,(HEIGHT-2*PAD)/spanY);
    return raw.map(item=>({
      ...item,
      x:WIDTH/2+(item.stop.longitude!-centerLon)*longitudeCorrection*scale,
      y:HEIGHT/2-(item.stop.latitude!-centerLat)*scale,
    }));
  },[visibleGroups]);
  const selected=points.find(point=>point.stop.parcel_id===selectedParcel);
  const selectedStop=selected??points[0];
  const validMapUrl=(url:string|null)=>{if(!url)return null;try{const parsed=new URL(url);return parsed.protocol==="https:"&&["www.google.com","google.com","www.openstreetmap.org","openstreetmap.org"].includes(parsed.hostname)?parsed.toString():null;}catch{return null;}};
  if(!groupsWithCoordinates.length)return <div className="route-viz-empty"><MapPin size={21}/><strong>Map preview unavailable</strong><span>No valid geocoded coordinates were returned. You can still review and assign stops in the route list below.</span></div>;
  return <section className="route-viz" aria-label="Geographic delivery stop preview">
    <div className="route-viz-heading"><div><span className="route-planning-kicker">GEOGRAPHIC STOP PREVIEW</span><h3>Explore proposed delivery routes</h3><p>Stop positions use geocoded coordinates. Connecting lines show visit order, not road geometry.</p></div><label>View partner<select value={selectedGroup} onChange={event=>{setSelectedGroup(event.target.value);setSelectedParcel(null);}}><option value="all">All mapped routes</option>{groupsWithCoordinates.map(group=><option key={group.key} value={group.key}>{group.partnerName}</option>)}</select></label></div>
    <div className="route-viz-content">
      <div className="route-viz-map">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`Geographic preview of ${points.length} mapped delivery stops`}>
          <defs><pattern id="route-viz-grid" width="38" height="38" patternUnits="userSpaceOnUse"><path d="M 38 0 L 0 0 0 38" fill="none" stroke="#dce6f3" strokeWidth="1"/></pattern></defs>
          <rect width={WIDTH} height={HEIGHT} fill="#f6f9fe"/><rect width={WIDTH} height={HEIGHT} fill="url(#route-viz-grid)"/>
          {visibleGroups.map(group=>{const line=points.filter(point=>point.groupKey===group.key).sort((a,b)=>a.order-b.order);const color=colors[groupsWithCoordinates.findIndex(g=>g.key===group.key)%colors.length];return line.length>1?<polyline key={group.key} points={line.map(point=>`${point.x},${point.y}`).join(" ")} fill="none" stroke={color} strokeWidth="3" strokeDasharray="8 6" strokeLinecap="round" opacity=".75"/>:null;})}
          {points.map(point=>{const color=colors[groupsWithCoordinates.findIndex(g=>g.key===point.groupKey)%colors.length];const active=point.stop.parcel_id===selectedStop?.stop.parcel_id;return <g key={point.stop.parcel_id} transform={`translate(${point.x} ${point.y})`}><circle r={active?18:15} fill={active?"#ffffff":color} stroke={color} strokeWidth={active?4:2}/><text y="4" textAnchor="middle" fontSize="11" fontWeight="700" fill={active?color:"#ffffff"}>{point.order}</text></g>;})}
        </svg>
        <div className="route-viz-controls" aria-label="Select a mapped stop">{points.map(point=><button type="button" key={point.stop.parcel_id} aria-label={`Select stop ${point.order}: ${point.stop.tracking_number}`} aria-pressed={point.stop.parcel_id===selectedStop?.stop.parcel_id} className={point.stop.parcel_id===selectedStop?.stop.parcel_id?"active":""} onClick={()=>setSelectedParcel(point.stop.parcel_id)}>{point.order}</button>)}</div>
        <span className="route-viz-map-note">Schematic geographic projection · Not a live navigation map</span>
      </div>
      <aside className="route-viz-detail" aria-live="polite">
        {selectedStop&&<><span className="route-planning-kicker">SELECTED STOP {selectedStop.order}</span><h4>{selectedStop.stop.tracking_number}</h4><p>{selectedStop.stop.city}, {selectedStop.stop.state} · {selectedStop.stop.pincode}</p><dl><dt>Suggested partner</dt><dd>{selectedStop.partnerName}</dd><dt>Delivery window</dt><dd>{selectedStop.stop.slot_start.slice(0,5)}–{selectedStop.stop.slot_end.slice(0,5)}</dd><dt>Coordinates</dt><dd>{selectedStop.stop.latitude!.toFixed(5)}, {selectedStop.stop.longitude!.toFixed(5)}</dd>{selectedStop.stop.leg_distance_m!==null&&<><dt>Estimated preceding leg</dt><dd>{(selectedStop.stop.leg_distance_m/1000).toFixed(1)} km{selectedStop.stop.leg_duration_seconds!==null?` · ${Math.round(selectedStop.stop.leg_duration_seconds/60)} min`:""}</dd></>}</dl>
        {validMapUrl(groupsWithCoordinates.find(group=>group.key===selectedStop.groupKey)?.mapUrl??null)&&<a href={validMapUrl(groupsWithCoordinates.find(group=>group.key===selectedStop.groupKey)?.mapUrl??null)!} target="_blank" rel="noopener noreferrer"><Navigation2 size={15}/> Open external route map</a>}</>}
        <span className="route-viz-disclaimer">Route suggestions require manual approval. Distances and durations are estimates when supplied by the routing service.</span>
      </aside>
    </div>
    <div className="route-viz-legend">{groupsWithCoordinates.map((group,index)=><button key={group.key} type="button" onClick={()=>{setSelectedGroup(selectedGroup===group.key?"all":group.key);setSelectedParcel(null);}} aria-pressed={selectedGroup===group.key}><span style={{background:colors[index%colors.length]}}/>{group.partnerName} ({group.stops.length})</button>)}</div>
  </section>;
}
