import type { AdminBooking, Booking, DeliverySlot, Parcel, ParcelCreate, User, DeliveryPartner, DeliveryAssignment, DeliveryEvent, NotificationItem, DeliveryRoutePlan, ParcelTimelineEvent } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1").replace(/\/+$/, "");
export const SESSION_EXPIRED_EVENT = "timedrop:session-expired";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function responseErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item && typeof item === "object" && "msg" in item
        ? String((item as { msg: unknown }).msg)
        : "")
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}

async function fetchJson<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch (error) {
    const message = error instanceof Error && error.name === "AbortError"
      ? "The request timed out. Please try again."
      : "Unable to reach TimeDrop. Check your internet connection and try again.";
    throw new ApiError(message, 0);
  }

  if (!response.ok) {
    let body: unknown = null;
    try { body = await response.json(); } catch { /* The server may return an empty or non-JSON error. */ }
    const fallback = `Request failed (${response.status})`;
    const message = responseErrorMessage(body, fallback);
    if (response.status === 401 && token && typeof window !== "undefined") {
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  try {
    return await response.json() as T;
  } catch {
    throw new ApiError("TimeDrop returned an unreadable response. Please try again.", response.status);
  }
}

function request<T>(path: string, token: string, init: RequestInit = {}): Promise<T> {
  return fetchJson<T>(path, init, token);
}

export function login(email: string, password: string) {
  return fetchJson<{ access_token: string; token_type: string }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) },
  );
}
export const getMe=(token:string)=>request<User>("/auth/me",token);
export const getParcels=(token:string)=>request<Parcel[]>("/parcels/?skip=0&limit=100",token);
export const updateParcelStatus=(token:string,id:number,status:string)=>request<Parcel>(`/parcels/${id}/status`,token,{method:"PATCH",body:JSON.stringify({status})});
export const getSlots=(token:string,date:string,includeInactive=false)=>request<DeliverySlot[]>(`/scheduling/slots?delivery_date=${encodeURIComponent(date)}&include_inactive=${includeInactive}`,token);
export const createSlot=(token:string,data:{delivery_date:string;start_time:string;end_time:string;capacity:number})=>request<DeliverySlot>("/scheduling/slots",token,{method:"POST",body:JSON.stringify(data)});
export const updateSlot=(token:string,slotId:number,data:{capacity?:number;is_active?:boolean})=>
 request<DeliverySlot>(`/scheduling/slots/${slotId}`,token,{method:"PATCH",body:JSON.stringify(data)});
export const cancelBooking=(token:string,parcelId:number)=>request<void>(`/scheduling/parcels/${parcelId}/bookings`,token,{method:"DELETE"});
export const rescheduleBooking=(token:string,parcelId:number,slotId:number)=>request<Booking>(`/scheduling/parcels/${parcelId}/bookings`,token,{method:"PATCH",body:JSON.stringify({slot_id:slotId})});
export const getAdminBookings=(token:string,status:"booked"|"cancelled"|"all"="booked",deliveryDate="")=>{const params=new URLSearchParams();if(status!=="all")params.set("status",status);if(deliveryDate)params.set("delivery_date",deliveryDate);const query=params.toString();return request<AdminBooking[]>(`/scheduling/bookings${query?`?${query}`:""}`,token);};
export const register=(data:{email:string;full_name:string;password:string})=>fetchJson<User>("/auth/register",{method:"POST",body:JSON.stringify(data)});
export const createParcel=(token:string,data:ParcelCreate)=>request<Parcel>("/parcels/",token,{method:"POST",body:JSON.stringify(data)});
export const getParcelBooking=(token:string,parcelId:number)=>request<Booking>(`/scheduling/parcels/${parcelId}/bookings`,token);
export const bookParcel=(token:string,parcelId:number,slotId:number)=>request<Booking>(`/scheduling/parcels/${parcelId}/bookings`,token,{method:"POST",body:JSON.stringify({slot_id:slotId})});
export const getDeliveryPartners=(token:string)=>request<DeliveryPartner[]>("/delivery/partners",token);
export const createDeliveryPartner=(token:string,data:{email:string;full_name:string;password:string;phone:string;vehicle_type:string;max_active_assignments:number})=>request<DeliveryPartner>("/delivery/partners",token,{method:"POST",body:JSON.stringify(data)});
export type DeliveryPartnerUpdate = Partial<Pick<DeliveryPartner, "full_name" | "phone" | "vehicle_type" | "max_active_assignments" | "is_available" | "is_active">>;
export const updateDeliveryPartner=(token:string,partnerId:number,data:DeliveryPartnerUpdate)=>
 request<DeliveryPartner>(`/delivery/partners/${partnerId}`,token,{method:"PATCH",body:JSON.stringify(data)});
export const getDeliveryAssignments=(token:string)=>request<DeliveryAssignment[]>("/delivery/assignments",token);
export const getDeliveryRoutePlan=(token:string,date:string)=>request<DeliveryRoutePlan>(`/delivery/route-plan?delivery_date=${encodeURIComponent(date)}`,token);
export const assignParcel=(token:string,parcelId:number,partnerId:number)=>request<DeliveryAssignment>(`/delivery/parcels/${parcelId}/assignments`,token,{method:"POST",body:JSON.stringify({partner_id:partnerId})});
export const getMyAssignments=(token:string)=>request<DeliveryAssignment[]>("/delivery/my-assignments",token);
export const getMyTracking=(token:string)=>request<DeliveryAssignment[]>("/delivery/my-tracking",token);
export const publishDeliveryLocation=(token:string,assignmentId:number,data:{latitude:number;longitude:number;accuracy_meters?:number})=>request<{accepted:boolean;recorded_at:string}>(`/delivery/assignments/${assignmentId}/location`,token,{method:"POST",body:JSON.stringify(data)});
export const getLiveDeliveryLocation=(token:string,parcelId:number)=>request<import("./types").DeliveryLiveLocation>(`/delivery/parcels/${parcelId}/live-location`,token);

export const updateDeliveryEta=(token:string,id:number,data:{estimated_delivery_start:string;estimated_delivery_end:string})=>request<DeliveryAssignment>(`/delivery/assignments/${id}/eta`,token,{method:"PATCH",body:JSON.stringify(data)});
export const updateAssignmentStatus=(token:string,id:number,data:{status:"accepted"|"out_for_delivery"|"delivered"|"failed";failure_reason?:string})=>request<DeliveryAssignment>(`/delivery/assignments/${id}/status`,token,{method:"PATCH",body:JSON.stringify(data)});

export const getAssignmentEvents=(token:string,assignmentId:number)=>request<DeliveryEvent[]>(`/delivery/assignments/${assignmentId}/events`,token);

export const issueDeliveryCode=(token:string,parcelId:number)=>request<{code:string;expires_at:string}>(`/delivery/parcels/${parcelId}/delivery-code`,token,{method:"POST"});
export const submitDeliveryProof=(token:string,assignmentId:number,data:{code:string;recipient_name:string})=>request<DeliveryAssignment>(`/delivery/assignments/${assignmentId}/proof`,token,{method:"POST",body:JSON.stringify(data)});


export const getSupportCases=(token:string)=>request<import("./types").SupportCase[]>("/support/cases",token);
export const createSupportCase=(token:string,data:{category:string;subject:string;description:string;parcel_id?:number|null})=>request<import("./types").SupportCase>("/support/cases",token,{method:"POST",body:JSON.stringify(data)});
export const replySupportCase=(token:string,caseId:number,body:string)=>request<import("./types").SupportCase>("/support/cases/"+caseId+"/messages",token,{method:"POST",body:JSON.stringify({body})});
export const getSupportQueue=(token:string,status?:string)=>request<import("./types").SupportCase[]>("/support/admin/cases"+(status?"?status="+encodeURIComponent(status):""),token);
export const updateSupportCase=(token:string,caseId:number,data:{status?:string;priority?:string;assigned_to_id?:number|null})=>request<import("./types").SupportCase>("/support/admin/cases/"+caseId,token,{method:"PATCH",body:JSON.stringify(data)});
export const replyAdminSupportCase=(token:string,caseId:number,body:string,is_internal=false)=>request<import("./types").SupportCase>("/support/admin/cases/"+caseId+"/messages",token,{method:"POST",body:JSON.stringify({body,is_internal})});
export const getNotifications=(token:string)=>request<NotificationItem[]>("/notifications/?limit=30",token);
export const getUnreadNotificationCount=(token:string)=>request<{unread_count:number}>("/notifications/unread-count",token);
export const markNotificationRead=(token:string,id:number)=>request<NotificationItem>(`/notifications/${id}/read`,token,{method:"PATCH"});
export const markAllNotificationsRead=(token:string)=>request<{updated_count:number}>("/notifications/read-all",token,{method:"POST"});

export type PhoneStatus = { phone_number:string|null; phone_verified:boolean; sms_notifications_consent:boolean };
export const getPhoneStatus=(token:string)=>request<PhoneStatus>("/phone-verification/me",token);
export const requestPhoneCode=(token:string,phone_number:string)=>request<{message:string;phone_number:string;expires_in_seconds:number;development_code?:string;delivery_mode?:string}>("/phone-verification/request",token,{method:"POST",body:JSON.stringify({phone_number})});
export const resendPhoneCode=(token:string)=>request<{message:string;phone_number:string;expires_in_seconds:number;delivery_mode:string}>("/phone-verification/resend",token,{method:"POST"});
export const verifyPhoneCode=(token:string,code:string)=>request<PhoneStatus>("/phone-verification/verify",token,{method:"POST",body:JSON.stringify({code})});
export const updateSmsConsent=(token:string,enabled:boolean)=>request<PhoneStatus>("/phone-verification/sms-consent",token,{method:"PUT",body:JSON.stringify({enabled})});

export type ParcelIntakeCreate = {
 tracking_number:string; recipient_name:string; phone:string; address_line:string;
 city:string; state:string; pincode:string; customer_email?:string;
 received_from:string; package_condition:"intact"|"damaged"|"opened"; note?:string;
};
export type ParcelIntake = {
 id:number; tracking_number:string; recipient_name:string; city:string; state:string;
 pincode:string; status:string; received_from:string; package_condition:string;
 received_at:string; customer_email:string|null;
};
export type CustodyEvent = {
 id:number; parcel_id:number; actor_id:number; event_type:string;
 package_condition:string|null; received_from:string|null; handed_to:string|null;
 note:string|null; created_at:string;
};
export const createParcelIntake=(token:string,data:ParcelIntakeCreate)=>request<ParcelIntake>("/operations/intake",token,{method:"POST",body:JSON.stringify(data)});
export const getParcelIntakes=(token:string)=>request<ParcelIntake[]>("/operations/intake",token);
export const getCustodyHistory=(token:string,parcelId:number)=>request<CustodyEvent[]>(`/operations/parcels/${parcelId}/custody`,token);
export const releaseParcelCustody=(token:string,parcelId:number,note?:string)=>request<CustodyEvent>(`/operations/parcels/${parcelId}/release`,token,{method:"POST",body:JSON.stringify({note:note||undefined})});

export const returnParcelToOperations=(
 token:string,parcelId:number,data:{package_condition:"intact"|"damaged"|"opened";note:string}
)=>request<CustodyEvent>(`/operations/parcels/${parcelId}/return`,token,{method:"POST",body:JSON.stringify(data)});

export type WarehouseSummary = {
 total_parcels:number; in_custody:number; assigned_to_bins:number; awaiting_storage:number;
 damaged_or_opened:number; out_for_delivery:number; delivered:number; failed:number;
};
export const getWarehouseSummary=(token:string)=>request<WarehouseSummary>("/operations/warehouse/summary",token);
export const getWarehouseParcels=(token:string,filters:{q?:string;status?:string;location?:string})=>{
 const params=new URLSearchParams();
 if(filters.q)params.set("q",filters.q);
 if(filters.status)params.set("parcel_status",filters.status);
 if(filters.location)params.set("location",filters.location);
 const query=params.toString();
 return request<import("./types").WarehouseParcel[]>(`/operations/warehouse/parcels${query?`?${query}`:""}`,token);
};
export const updateWarehouseLocation=(token:string,parcelId:number,warehouse_location:string|null)=>
 request<Parcel>(`/operations/warehouse/parcels/${parcelId}/location`,token,{method:"PATCH",body:JSON.stringify({warehouse_location})});

export const getParcelTimeline=(token:string,parcelId:number)=>request<ParcelTimelineEvent[]>(`/parcels/${parcelId}/timeline`,token);

export const getOperationsAnalytics=(token:string,startDate:string,endDate:string)=>
 request<import("./types").OperationsAnalytics>(`/operations/analytics?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,token);


export type PartnerAvailabilityWindow = {
 weekday:number;
 start_time:string;
 end_time:string;
 is_active:boolean;
};
export type PartnerAvailabilitySettings = {
 enabled:boolean;
 windows:PartnerAvailabilityWindow[];
};
export const getMyAvailability=(token:string)=>
 request<PartnerAvailabilitySettings>("/delivery/my-availability",token);
export const updateMyAvailability=(token:string,data:PartnerAvailabilitySettings)=>
 request<PartnerAvailabilitySettings>("/delivery/my-availability",token,{
  method:"PUT",body:JSON.stringify(data)
});


export const checkPincodeServiceability=(token:string,pincode:string)=>
 request<import("./types").ServiceabilityCheck>(`/serviceability/${encodeURIComponent(pincode)}`,token);
export const getServiceAreas=(token:string,q="")=>{
 const params=new URLSearchParams();
 if(q.trim())params.set("q",q.trim());
 const query=params.toString();
 return request<import("./types").ServiceArea[]>(`/operations/service-areas/${query?`?${query}`:""}`,token);
};
export const createServiceArea=(token:string,data:{pincode:string;city:string;state:string})=>
 request<import("./types").ServiceArea>("/operations/service-areas/",token,{method:"POST",body:JSON.stringify(data)});
export const updateServiceArea=(token:string,id:number,data:{pincode?:string;city?:string;state?:string;is_active?:boolean})=>
 request<import("./types").ServiceArea>(`/operations/service-areas/${id}`,token,{method:"PATCH",body:JSON.stringify(data)});


export const getBlackoutDates=(token:string,fromDate="",toDate="",includeInactive=true)=>{
 const params=new URLSearchParams();
 if(fromDate)params.set("from_date",fromDate);
 if(toDate)params.set("to_date",toDate);
 params.set("include_inactive",String(includeInactive));
 return request<import("./types").DeliveryBlackoutDate[]>(`/operations/blackout-dates?${params.toString()}`,token);
};
export const createBlackoutDate=(token:string,data:{delivery_date:string;reason:string})=>
 request<import("./types").DeliveryBlackoutDate>("/operations/blackout-dates",token,{method:"POST",body:JSON.stringify(data)});
export const updateBlackoutDate=(token:string,id:number,data:{reason?:string;is_active?:boolean})=>
 request<import("./types").DeliveryBlackoutDate>(`/operations/blackout-dates/${id}`,token,{method:"PATCH",body:JSON.stringify(data)});


export const getBlackoutStatus=(token:string,deliveryDate:string)=>
 request<import("./types").DeliveryBlackoutStatus>(`/scheduling/blackout-status?delivery_date=${encodeURIComponent(deliveryDate)}`,token);


export const getOperationsAuditLog=(token:string,filters:{entity_type?:string;action?:string;from_date?:string;to_date?:string;skip?:number;limit?:number}={})=>{
 const params=new URLSearchParams();
 Object.entries(filters).forEach(([key,value])=>{if(value!==undefined&&value!=="")params.set(key,String(value));});
 return request<import("./types").OperationsAuditEvent[]>(`/operations/audit-log?${params.toString()}`,token);
};


export type NotificationDeliveryOperationsItem = {
 id:number;
 channel:"email"|"sms";
 masked_recipient:string;
 subject:string;
 status:"pending"|"processing"|"sent"|"failed"|"cancelled";
 attempts:number;
 next_attempt_at:string;
 locked_at:string|null;
 sent_at:string|null;
 provider_message_id:string|null;
 last_error:string|null;
 created_at:string;
};
export const getNotificationDeliveries=(token:string,filters:{status?:NotificationDeliveryOperationsItem["status"];channel?:NotificationDeliveryOperationsItem["channel"];skip?:number;limit?:number}={})=>{
 const params=new URLSearchParams();
 Object.entries(filters).forEach(([key,value])=>{if(value!==undefined)params.set(key,String(value));});
 return request<NotificationDeliveryOperationsItem[]>(`/operations/notification-deliveries?${params.toString()}`,token);
};
export const retryNotificationDelivery=(token:string,id:number)=>
 request<NotificationDeliveryOperationsItem>(`/operations/notification-deliveries/${id}/retry`,token,{method:"POST"});


export type OperationsSystemHealth = {
 database_status:"ok";
 notification_worker_status:"healthy"|"stale"|"not_seen";
 worker_last_seen_at:string|null;
 worker_age_seconds:number|null;
 worker_stale_after_seconds:number;
 notification_queue:Record<string,number>;
 checked_at:string;
};
export const getOperationsSystemHealth=(token:string)=>
 request<OperationsSystemHealth>("/operations/system-health",token);
