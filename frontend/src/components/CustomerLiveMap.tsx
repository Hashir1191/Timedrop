import { useCallback, useEffect, useRef, useState } from "react";
import { Clock3, MapPin, Navigation, RefreshCw, Signal, SignalLow } from "lucide-react";
import { ApiError, getLiveDeliveryLocation } from "../api";
import type { DeliveryLiveLocation } from "../types";

function formatTime(value:string|null){
  if(!value)return "";
  const date=new Date(value);
  return Number.isNaN(date.getTime())?"":new Intl.DateTimeFormat("en-IN",{hour:"2-digit",minute:"2-digit"}).format(date);
}

function mapEmbedUrl(latitude:number,longitude:number){
  const latitudeDelta=0.012;
  const longitudeDelta=0.012;
  const bbox=[
    (longitude-longitudeDelta).toFixed(6),
    (latitude-latitudeDelta).toFixed(6),
    (longitude+longitudeDelta).toFixed(6),
    (latitude+latitudeDelta).toFixed(6),
  ].join(",");
  return "https://www.openstreetmap.org/export/embed.html?bbox="+bbox+"&layer=mapnik&marker="+latitude.toFixed(6)+","+longitude.toFixed(6);
}

export default function CustomerLiveMap({token,parcelId}:{token:string;parcelId:number}){
  const [location,setLocation]=useState<DeliveryLiveLocation|null>(null);
  const [loading,setLoading]=useState(true);
  const [refreshing,setRefreshing]=useState(false);
  const [error,setError]=useState("");
  const [unavailable,setUnavailable]=useState(false);
  const sequence=useRef(0);

  const refresh=useCallback(async()=>{
    const requestId=++sequence.current;
    setRefreshing(true);
    setError("");
    try{
      const result=await getLiveDeliveryLocation(token,parcelId);
      if(requestId!==sequence.current)return;
      setLocation(result);
      setUnavailable(false);
    }catch(err){
      if(requestId!==sequence.current)return;
      if(err instanceof ApiError&&err.status===409){
        setUnavailable(true);
        setLocation(null);
        setError("Live tracking has ended because this parcel is no longer out for delivery.");
      }else{
        setError(err instanceof Error?err.message:"Unable to load the latest delivery location.");
      }
    }finally{
      if(requestId===sequence.current){setLoading(false);setRefreshing(false);}
    }
  },[token,parcelId]);

  useEffect(()=>{
    void refresh();
    const interval=window.setInterval(()=>{if(!unavailable)void refresh();},20000);
    return()=>{
      sequence.current+=1;
      window.clearInterval(interval);
    };
  },[refresh,unavailable]);

  const hasCoordinates=location!==null&&location.latitude!==null&&location.longitude!==null;
  const mapUrl=hasCoordinates?mapEmbedUrl(location!.latitude!,location!.longitude!):"";
  const externalMapUrl=hasCoordinates?"https://www.openstreetmap.org/?mlat="+location!.latitude+"&mlon="+location!.longitude+"#map=16/"+location!.latitude+"/"+location!.longitude:"";

  return <section className="customer-live-map" aria-label="Live parcel location">
    <div className="customer-live-map-heading">
      <div><span className="customer-live-map-kicker">LIVE DELIVERY VIEW</span><h3>Follow your parcel</h3><p>Location updates are shared only during the active delivery.</p></div>
      <button type="button" className="secondary-button" onClick={()=>void refresh()} disabled={refreshing||unavailable}><RefreshCw size={14}/>{refreshing?"Updating…":"Refresh"}</button>
    </div>
    {error&&<div className="customer-live-map-alert" role="status">{error}</div>}
    {loading&&!location?<div className="customer-live-map-placeholder" role="status">Loading the latest delivery position…</div>:
      hasCoordinates?<>
        <div className="customer-live-map-status">
          <span className={location?.is_live?"live":"stale"}><Signal size={14}/>{location?.is_live?"Live position":"Last known position"}</span>
          <small>{location?.recorded_at?"Updated "+formatTime(location.recorded_at):""}</small>
        </div>
        <div className="customer-live-map-frame"><iframe title="Map showing the delivery partner's latest reported location" src={mapUrl} loading="lazy" referrerPolicy="strict-origin-when-cross-origin"/></div>
        <div className="customer-live-map-foot">
          <div><MapPin size={16}/><span><strong>{location?.is_live?"Delivery partner location":"Last reported location"}</strong><small>{location?.accuracy_meters!==null&&location?.accuracy_meters!==undefined?"GPS accuracy approximately "+Math.round(location.accuracy_meters)+" m":"Location accuracy not provided"}</small></span></div>
          <a href={externalMapUrl} target="_blank" rel="noopener noreferrer"><Navigation size={14}/> Open map</a>
        </div>
        {!location?.is_live&&<p className="customer-live-map-stale-note"><SignalLow size={14}/> This position may have changed. Waiting for the next partner update.</p>}
      </>:<div className="customer-live-map-placeholder"><MapPin size={20}/><strong>{location?.location_status==="awaiting_location"?"Waiting for the delivery partner's GPS":"Location not available"}</strong><span>The map will appear after the partner enables location sharing and their device sends its first GPS update.</span></div>
    }
    {location?.estimated_delivery_start&&location?.estimated_delivery_end&&<div className="customer-live-map-eta"><Clock3 size={16}/><span>Estimated arrival <strong>{formatTime(location.estimated_delivery_start)} – {formatTime(location.estimated_delivery_end)}</strong></span></div>}
    <p className="customer-live-map-disclaimer">The map shows the latest position received by TimeDrop, not continuous second-by-second movement. Location can be delayed by device permissions or network coverage.</p>
  </section>;
}
