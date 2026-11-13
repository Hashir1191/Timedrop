export type User = {
  id: number; email: string; full_name: string;
  role: "admin" | "customer" | "delivery_partner"; is_active: boolean; created_at: string;
};
export type Parcel = {
  id: number; tracking_number: string; recipient_name: string; phone: string;
  address_line: string; city: string; state: string; pincode: string;
  delivery_instructions: string | null; preferred_delivery_date: string | null;
  status: string; created_at: string; warehouse_location?: string | null;
};
export type DeliverySlot = { id:number; delivery_date:string; start_time:string; end_time:string; capacity:number; booked_count:number; remaining_capacity:number; is_active?:boolean };
export type Booking = { id:number; parcel_id:number; slot_id:number; delivery_date:string; start_time:string; end_time:string; status:string; booked_at:string; updated_at:string };
export type AdminBooking = { id:number; parcel_id:number; slot_id:number; status:"booked"|"cancelled"; booked_at:string; updated_at:string; parcel:Parcel; slot:{id:number;delivery_date:string;start_time:string;end_time:string;capacity:number;booked_count:number;is_active:boolean} };
export type ParcelCreate = { tracking_number:string; recipient_name:string; phone:string; address_line:string; city:string; state:string; pincode:string; delivery_instructions?:string; preferred_delivery_date?:string };
export type DeliveryPartner = { id:number; user_id:number; full_name:string; email:string; phone:string; vehicle_type:string; is_available:boolean; is_active:boolean; active_assignments:number };
export type DeliveryRouteStop = { parcel_id:number; tracking_number:string; recipient_name:string; city:string; state:string; pincode:string; delivery_date:string; slot_start:string; slot_end:string; suggested_partner_id:number|null; suggested_partner_name:string|null; route_sequence:number|null; partner_active_jobs:number; zone_key:string; recommendation:string; latitude:number|null; longitude:number|null; leg_distance_m:number|null; leg_duration_seconds:number|null; map_url:string|null };
export type DeliveryRoutePlan = { delivery_date:string; generated_at:string; total_unassigned:number; recommended:number; unassigned_without_partner:number; mapping_enabled:boolean; routing_provider:string; stops:DeliveryRouteStop[] };
export type DeliveryAssignment = { id:number; parcel_id:number; partner_id:number; status:string; assigned_at:string; updated_at:string; tracking_number:string; recipient_name:string; phone:string; address_line:string; city:string; state:string; pincode:string; delivery_date:string; start_time:string; end_time:string; partner_name:string; estimated_delivery_start:string|null; estimated_delivery_end:string|null };

export type DeliveryEvent = {
  id:number; assignment_id:number; parcel_id:number; actor_id:number; actor_name:string;
  event_type:string; from_status:string|null; to_status:string; note:string|null; created_at:string;
};

export type NotificationItem = {
  id:number; user_id:number; parcel_id:number|null; event_type:string;
  title:string; message:string; created_at:string; read_at:string|null;
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

export type ParcelTimelineEvent = {
  id: string; event_type: string; title: string; description: string;
  status: string; created_at: string;
};
