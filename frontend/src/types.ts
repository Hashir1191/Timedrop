export type User = {
  id: number; email: string; full_name: string;
  role: "admin" | "customer" | "delivery_partner"; is_active: boolean; created_at: string;
};
export type Parcel = {
  id: number; tracking_number: string; recipient_name: string; phone: string;
  address_line: string; city: string; state: string; pincode: string;
  delivery_instructions: string | null; preferred_delivery_date: string | null;
  status: string; created_at: string;
};
export type DeliverySlot = { id:number; delivery_date:string; start_time:string; end_time:string; capacity:number; booked_count:number; remaining_capacity:number; is_active?:boolean };
export type Booking = { id:number; parcel_id:number; slot_id:number; delivery_date:string; start_time:string; end_time:string; status:string; booked_at:string; updated_at:string };
export type AdminBooking = { id:number; parcel_id:number; slot_id:number; status:"booked"|"cancelled"; booked_at:string; updated_at:string; parcel:Parcel; slot:{id:number;delivery_date:string;start_time:string;end_time:string;capacity:number;booked_count:number;is_active:boolean} };
export type ParcelCreate = { tracking_number:string; recipient_name:string; phone:string; address_line:string; city:string; state:string; pincode:string; delivery_instructions?:string; preferred_delivery_date?:string };
export type DeliveryPartner = { id:number; user_id:number; full_name:string; email:string; phone:string; vehicle_type:string; is_available:boolean; is_active:boolean; active_assignments:number };
export type DeliveryAssignment = { id:number; parcel_id:number; partner_id:number; status:string; assigned_at:string; updated_at:string; tracking_number:string; recipient_name:string; phone:string; address_line:string; city:string; state:string; pincode:string; delivery_date:string; start_time:string; end_time:string; partner_name:string };
