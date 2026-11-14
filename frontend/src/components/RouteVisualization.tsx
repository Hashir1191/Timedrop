import { useEffect, useMemo, useRef, useState } from "react";
import { MapPin, Minus, Navigation2, Plus, RotateCcw } from "lucide-react";
import type { PointerEvent as ReactPointerEvent } from "react";
import type { DeliveryRouteStop } from "../types";

type RouteGroup = { key:string; partnerName:string; mapUrl:string|null; stops:DeliveryRouteStop[] };
type Point = { stop:DeliveryRouteStop; x:number; y:number; order:number; groupKey:string; partnerName:string };
type WorldPoint = { x:number; y:number };
const TILE=256, DEFAULT_WIDTH=760, DEFAULT_HEIGHT=380;
const colors=["#4569e8","#16a085","#a855f7","#e68b32","#cf4f75","#2788aa"];
const MIN_ZOOM=3,MAX_ZOOM=18;
const TILE_URL=(import.meta.env.VITE_ROUTE_TILE_URL as string|undefined)||"https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION=(import.meta.env.VITE_ROUTE_TILE_ATTRIBUTION as string|undefined)||"© OpenStreetMap contributors";
const TILE_ATTRIBUTION_URL=(import.meta.env.VITE_ROUTE_TILE_ATTRIBUTION_URL as string|undefined)||"https://www.openstreetmap.org/copyright";

function clamp(value:number,min:number,max:number){return Math.max(min,Math.min(max,value));}
function wrapTileX(x:number,count:number){return ((x%count)+count)%count;}
function project(latitude:number,longitude:number,zoom:number):WorldPoint{
  const lat=clamp(latitude,-85.05112878,85.05112878)*Math.PI/180;
  const scale=TILE*Math.pow(2,zoom);
  return {x:(longitude+180)/360*scale,y:(1-Math.asinh(Math.tan(lat))/Math.PI)/2*scale};
}
function unproject(point:WorldPoint,zoom:number):{latitude:number;longitude:number}{
  const scale=TILE*Math.pow(2,zoom);
  const longitude=point.x/scale*360-180;
  const n=Math.PI-2*Math.PI*point.y/scale;
  return {latitude:180/Math.PI*Math.atan(Math.sinh(n)),longitude};
}
function validMapUrl(url:string|null){
  if(!url)return null;
  try{const parsed=new URL(url);return parsed.protocol==="https:"&&["www.google.com","google.com","www.openstreetmap.org","openstreetmap.org"].includes(parsed.hostname)?parsed.toString():null;}
  catch{return null;}
}

export default function RouteVisualization({groups}:{groups:RouteGroup[]}){
  const [selectedGroup,setSelectedGroup]=useState("all");
  const [selectedParcel,setSelectedParcel]=useState<number|null>(null);
  const [zoom,setZoom]=useState(12);
  const [center,setCenter]=useState<WorldPoint>(()=>project(20.5937,78.9629,12));
  const [size,setSize]=useState({width:DEFAULT_WIDTH,height:DEFAULT_HEIGHT});
  const [tileError,setTileError]=useState(false);
  const mapRef=useRef<HTMLDivElement|null>(null);
  const dragRef=useRef<{pointerId:number;x:number;y:number;center:WorldPoint}|null>(null);

  const groupsWithCoordinates=useMemo(()=>groups.map(group=>({
    ...group,
    stops:group.stops.filter(stop=>stop.latitude!==null&&stop.longitude!==null&&Number.isFinite(stop.latitude)&&Number.isFinite(stop.longitude)&&Math.abs(stop.latitude!)<=90&&Math.abs(stop.longitude!)<=180)
  })).filter(group=>group.stops.length>0),[groups]);
  const visibleGroups=selectedGroup==="all"?groupsWithCoordinates:groupsWithCoordinates.filter(group=>group.key===selectedGroup);
  const points=useMemo(()=>visibleGroups.flatMap(group=>group.stops.map((stop,index)=>({
    stop,order:stop.route_sequence??index+1,groupKey:group.key,partnerName:group.partnerName
  }))),[visibleGroups]);
  const selectedStop=points.find(point=>point.stop.parcel_id===selectedParcel)??points[0];

  function fitGroups(nextGroups=visibleGroups){
    const coordinates=nextGroups.flatMap(group=>group.stops.map(stop=>({latitude:stop.latitude!,longitude:stop.longitude!})));
    if(!coordinates.length)return;
    const latitudes=coordinates.map(point=>point.latitude),longitudes=coordinates.map(point=>point.longitude);
    const minLat=Math.min(...latitudes),maxLat=Math.max(...latitudes),minLon=Math.min(...longitudes),maxLon=Math.max(...longitudes);
    const centerLat=(minLat+maxLat)/2,centerLon=(minLon+maxLon)/2;
    const width=Math.max(320,size.width),height=Math.max(220,size.height);
    let nextZoom=MAX_ZOOM;
    for(let candidate=MAX_ZOOM;candidate>=MIN_ZOOM;candidate--){
      const a=project(minLat,minLon,candidate),b=project(maxLat,maxLon,candidate);
      if(Math.abs(b.x-a.x)<=width-110&&Math.abs(b.y-a.y)<=height-110){nextZoom=candidate;break;}
    }
    setZoom(nextZoom);setCenter(project(centerLat,centerLon,nextZoom));setSelectedParcel(null);
  }

  useEffect(()=>{
    const element=mapRef.current;if(!element)return;
    const observer=new ResizeObserver(entries=>{
      const rect=entries[0]?.contentRect;if(rect) setSize({width:Math.max(1,rect.width),height:Math.max(1,rect.height)});
    });
    observer.observe(element);return()=>observer.disconnect();
  },[]);

  useEffect(()=>{fitGroups(visibleGroups);},[visibleGroups]);

  const topLeft={x:center.x-size.width/2,y:center.y-size.height/2};
  const firstTileX=Math.floor(topLeft.x/TILE),firstTileY=Math.floor(topLeft.y/TILE);
  const lastTileX=Math.floor((topLeft.x+size.width)/TILE),lastTileY=Math.floor((topLeft.y+size.height)/TILE);
  const tileCount=Math.pow(2,zoom);
  const tiles=[];
  for(let y=firstTileY;y<=lastTileY;y++)for(let x=firstTileX;x<=lastTileX;x++){
    if(y<0||y>=tileCount)continue;
    const tileX=wrapTileX(x,tileCount);
    tiles.push({key:`${zoom}/${tileX}/${y}`,url:TILE_URL.replace("{z}",String(zoom)).replace("{x}",String(tileX)).replace("{y}",String(y)),left:x*TILE-topLeft.x,top:y*TILE-topLeft.y});
  }
  const mappedPoints:Point[]=points.map(point=>{
    const world=project(point.stop.latitude!,point.stop.longitude!,zoom);
    return {...point,x:world.x-topLeft.x,y:world.y-topLeft.y};
  });
  const routeLines=visibleGroups.map(group=>({
    ...group,
    points:mappedPoints.filter(point=>point.groupKey===group.key).sort((a,b)=>a.order-b.order)
  }));

  function onPointerDown(event:ReactPointerEvent<HTMLDivElement>){
    if((event.target as HTMLElement).closest("button,a"))return;
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current={pointerId:event.pointerId,x:event.clientX,y:event.clientY,center};
  }
  function onPointerMove(event:ReactPointerEvent<HTMLDivElement>){
    const drag=dragRef.current;if(!drag||drag.pointerId!==event.pointerId)return;
    setCenter({x:drag.center.x-(event.clientX-drag.x),y:drag.center.y-(event.clientY-drag.y)});
  }
  function onPointerUp(event:ReactPointerEvent<HTMLDivElement>){
    if(dragRef.current?.pointerId===event.pointerId)dragRef.current=null;
  }
  function changeZoom(delta:number){
    const next=clamp(zoom+delta,MIN_ZOOM,MAX_ZOOM);
    const geographic=unproject(center,zoom);setZoom(next);setCenter(project(geographic.latitude,geographic.longitude,next));
  }
  function selectGroup(key:string){
    const next=key==="all"?groupsWithCoordinates:groupsWithCoordinates.filter(group=>group.key===key);
    setSelectedGroup(key);setSelectedParcel(null);fitGroups(next);
  }

  if(!groupsWithCoordinates.length)return <div className="route-viz-empty"><MapPin size={21}/><strong>Map preview unavailable</strong><span>No valid geocoded coordinates were returned. You can still review and assign stops in the route list below.</span></div>;

  return <section className="route-viz" aria-label="Interactive street map of proposed delivery stops">
    <div className="route-viz-heading">
      <div><span className="route-planning-kicker">INTERACTIVE STREET MAP</span><h3>Explore proposed delivery routes</h3><p>Pan and zoom the street map, filter by partner, and select a stop to inspect its delivery window.</p></div>
      <label>View partner<select value={selectedGroup} onChange={event=>selectGroup(event.target.value)}><option value="all">All mapped routes</option>{groupsWithCoordinates.map(group=><option key={group.key} value={group.key}>{group.partnerName}</option>)}</select></label>
    </div>
    <div className="route-viz-map-shell">
      <div ref={mapRef} className="route-viz-map" onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp} role="region" aria-label="Draggable street map with numbered delivery stops">
        <div className="route-viz-tiles" aria-hidden="true">{tiles.map(tile=><img key={tile.key} src={tile.url} alt="" draggable={false} onError={()=>setTileError(true)} style={{left:tile.left,top:tile.top}}/>)}</div>
        <svg className="route-viz-overlay" viewBox={`0 0 ${size.width} ${size.height}`} aria-hidden="true">
          {routeLines.map(group=>{const color=colors[groupsWithCoordinates.findIndex(item=>item.key===group.key)%colors.length];return group.points.length>1?<polyline key={group.key} points={group.points.map(point=>`${point.x},${point.y}`).join(" ")} fill="none" stroke={color} strokeWidth="3" strokeDasharray="8 6" strokeLinecap="round" opacity=".9"/>:null;})}
          {mappedPoints.map(point=>{const color=colors[groupsWithCoordinates.findIndex(item=>item.key===point.groupKey)%colors.length];const active=point.stop.parcel_id===selectedStop?.stop.parcel_id;return <g key={point.stop.parcel_id} transform={`translate(${point.x} ${point.y})`}><circle r={active?18:15} fill={active?"#fff":color} stroke={color} strokeWidth={active?4:2}/><text y="4" textAnchor="middle" fontSize="11" fontWeight="700" fill={active?color:"#fff"}>{point.order}</text></g>;})}
        </svg>
        <div className="route-viz-map-controls" onPointerDown={event=>event.stopPropagation()}>
          <button type="button" aria-label="Zoom in" onClick={()=>changeZoom(1)} disabled={zoom>=MAX_ZOOM}><Plus size={16}/></button>
          <button type="button" aria-label="Zoom out" onClick={()=>changeZoom(-1)} disabled={zoom<=MIN_ZOOM}><Minus size={16}/></button>
          <button type="button" aria-label="Fit all visible stops" onClick={()=>fitGroups()}><RotateCcw size={15}/></button>
        </div>
        <span className="route-viz-map-note">Dashed connectors show stop order, not road geometry</span>
        <a className="route-viz-attribution" href={TILE_ATTRIBUTION_URL} target="_blank" rel="noopener noreferrer">{TILE_ATTRIBUTION}</a>
      </div>
      {tileError&&<p className="route-viz-tile-warning" role="status">Some map tiles could not be loaded. Stop details and assignment controls remain available.</p>}
    </div>
    <div className="route-viz-detail" aria-live="polite">
      {selectedStop&&<><span className="route-planning-kicker">SELECTED STOP {selectedStop.order}</span><h4>{selectedStop.stop.tracking_number}</h4><p>{selectedStop.stop.city}, {selectedStop.stop.state} · {selectedStop.stop.pincode}</p><dl><dt>Suggested partner</dt><dd>{selectedStop.partnerName}</dd><dt>Delivery window</dt><dd>{selectedStop.stop.slot_start.slice(0,5)}–{selectedStop.stop.slot_end.slice(0,5)}</dd><dt>Coordinates</dt><dd>{selectedStop.stop.latitude!.toFixed(5)}, {selectedStop.stop.longitude!.toFixed(5)}</dd>{selectedStop.stop.leg_distance_m!==null&&<><dt>Estimated preceding leg</dt><dd>{(selectedStop.stop.leg_distance_m/1000).toFixed(1)} km{selectedStop.stop.leg_duration_seconds!==null?` · ${Math.round(selectedStop.stop.leg_duration_seconds/60)} min`:""}</dd></>}</dl>
      {validMapUrl(groupsWithCoordinates.find(group=>group.key===selectedStop.groupKey)?.mapUrl??null)&&<a href={validMapUrl(groupsWithCoordinates.find(group=>group.key===selectedStop.groupKey)?.mapUrl??null)!} target="_blank" rel="noopener noreferrer"><Navigation2 size={15}/> Open external route map</a>}</>}
      <span className="route-viz-disclaimer">Route suggestions require manual approval. Dashed connectors represent stop sequence only. Distances and durations are estimates from the routing service, not live traffic.</span>
    </div>
    <div className="route-viz-stop-picker" aria-label="Select a delivery stop">{mappedPoints.map(point=><button type="button" key={point.stop.parcel_id} aria-pressed={point.stop.parcel_id===selectedStop?.stop.parcel_id} className={point.stop.parcel_id===selectedStop?.stop.parcel_id?"active":""} onClick={()=>setSelectedParcel(point.stop.parcel_id)}><span>{point.order}</span>{point.stop.tracking_number}</button>)}</div>
    <div className="route-viz-legend">{groupsWithCoordinates.map((group,index)=><button key={group.key} type="button" onClick={()=>selectGroup(selectedGroup===group.key?"all":group.key)} aria-pressed={selectedGroup===group.key}><span style={{background:colors[index%colors.length]}}/>{group.partnerName} ({group.stops.length})</button>)}</div>
    <p className="route-viz-coverage">Showing {mappedPoints.length} of {visibleGroups.reduce((sum,group)=>sum+group.stops.length,0)} stops in this view with valid coordinates. Stops without geocoding remain visible in the assignment list.</p>
  </section>;
}
