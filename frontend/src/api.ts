import type { AdminBooking, Booking, DeliverySlot, Parcel, ParcelCreate, User, DeliveryPartner, DeliveryAssignment, DeliveryEvent, NotificationItem, DeliveryRoutePlan } from "./types";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
export class ApiError extends Error { status:number; constructor(message:string,status:number){super(message);this.status=status;} }
async function request<T>(path:string,token:string,init:RequestInit={}):Promise<T>{
 const response=await fetch(`${API_BASE}${path}`,{...init,headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`,...init.headers}});
 if(!response.ok){let message=`Request failed (${response.status})`;try{const body=await response.json();message=body.detail||message;}catch{/* no json */}throw new ApiError(message,response.status);}
 if(response.status===204)return undefined as T;return response.json() as Promise<T>;
}
export async function login(email:string,password:string){const response=await fetch(`${API_BASE}/auth/login`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,password})});if(!response.ok){const body=await response.json().catch(()=>({}));throw new ApiError(body.detail||"Unable to sign in.",response.status);}return response.json() as Promise<{access_token:string;token_type:string}>;}
export const getMe=(token:string)=>request<User>("/auth/me",token);
export const getParcels=(token:string)=>request<Parcel[]>("/parcels/?skip=0&limit=100",token);
export const updateParcelStatus=(token:string,id:number,status:string)=>request<Parcel>(`/parcels/${id}/status`,token,{method:"PATCH",body:JSON.stringify({status})});
export const getSlots=(token:string,date:string)=>request<DeliverySlot[]>(`/scheduling/slots?delivery_date=${date}`,token);
export const createSlot=(token:string,data:{delivery_date:string;start_time:string;end_time:string;capacity:number})=>request<DeliverySlot>("/scheduling/slots",token,{method:"POST",body:JSON.stringify(data)});
export const cancelBooking=(token:string,parcelId:number)=>request<void>(`/scheduling/parcels/${parcelId}/bookings`,token,{method:"DELETE"});
export const rescheduleBooking=(token:string,parcelId:number,slotId:number)=>request<Booking>(`/scheduling/parcels/${parcelId}/bookings`,token,{method:"PATCH",body:JSON.stringify({slot_id:slotId})});
export const getAdminBookings=(token:string,status:"booked"|"cancelled"|"all"="booked",deliveryDate="")=>{const params=new URLSearchParams();if(status!=="all")params.set("status",status);if(deliveryDate)params.set("delivery_date",deliveryDate);const query=params.toString();return request<AdminBooking[]>(`/scheduling/bookings${query?`?${query}`:""}`,token);};
export const register=(data:{email:string;full_name:string;password:string})=>fetch(`${API_BASE}/auth/register`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)}).then(async response=>{if(!response.ok){const body=await response.json().catch(()=>({}));throw new ApiError(body.detail||"Unable to create account.",response.status);}return response.json() as Promise<User>;});
export const createParcel=(token:string,data:ParcelCreate)=>request<Parcel>("/parcels/",token,{method:"POST",body:JSON.stringify(data)});
export const getParcelBooking=(token:string,parcelId:number)=>request<Booking>(`/scheduling/parcels/${parcelId}/bookings`,token);
export const bookParcel=(token:string,parcelId:number,slotId:number)=>request<Booking>(`/scheduling/parcels/${parcelId}/bookings`,token,{method:"POST",body:JSON.stringify({slot_id:slotId})});
export const getDeliveryPartners=(token:string)=>request<DeliveryPartner[]>("/delivery/partners",token);
export const createDeliveryPartner=(token:string,data:{email:string;full_name:string;password:string;phone:string;vehicle_type:string})=>request<DeliveryPartner>("/delivery/partners",token,{method:"POST",body:JSON.stringify(data)});
export const getDeliveryAssignments=(token:string)=>request<DeliveryAssignment[]>("/delivery/assignments",token);
export const getDeliveryRoutePlan=(token:string,date:string)=>request<DeliveryRoutePlan>(`/delivery/route-plan?delivery_date=${encodeURIComponent(date)}`,token);
export const assignParcel=(token:string,parcelId:number,partnerId:number)=>request<DeliveryAssignment>(`/delivery/parcels/${parcelId}/assignments`,token,{method:"POST",body:JSON.stringify({partner_id:partnerId})});
export const getMyAssignments=(token:string)=>request<DeliveryAssignment[]>("/delivery/my-assignments",token);
export const getMyTracking=(token:string)=>request<DeliveryAssignment[]>("/delivery/my-tracking",token);
export const updateDeliveryEta=(token:string,id:number,data:{estimated_delivery_start:string;estimated_delivery_end:string})=>request<DeliveryAssignment>(`/delivery/assignments/${id}/eta`,token,{method:"PATCH",body:JSON.stringify(data)});
export const updateAssignmentStatus=(token:string,id:number,data:{status:"accepted"|"out_for_delivery"|"delivered"|"failed";failure_reason?:string})=>request<DeliveryAssignment>(`/delivery/assignments/${id}/status`,token,{method:"PATCH",body:JSON.stringify(data)});

export const getAssignmentEvents=(token:string,assignmentId:number)=>request<DeliveryEvent[]>(`/delivery/assignments/${assignmentId}/events`,token);

export const issueDeliveryCode=(token:string,parcelId:number)=>request<{code:string;expires_at:string}>(`/delivery/parcels/${parcelId}/delivery-code`,token,{method:"POST"});
export const submitDeliveryProof=(token:string,assignmentId:number,data:{code:string;recipient_name:string})=>request<DeliveryAssignment>(`/delivery/assignments/${assignmentId}/proof`,token,{method:"POST",body:JSON.stringify(data)});

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
