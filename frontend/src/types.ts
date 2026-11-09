export type User = {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "customer";
  is_active: boolean;
  created_at: string;
};

export type Parcel = {
  id: number;
  tracking_number: string;
  recipient_name: string;
  phone: string;
  address_line: string;
  city: string;
  state: string;
  pincode: string;
  delivery_instructions: string | null;
  preferred_delivery_date: string | null;
  status: string;
  created_at: string;
};

export type DeliverySlot = {
  id: number;
  delivery_date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  booked_count: number;
  remaining_capacity: number;
  is_active?: boolean;
};

export type Booking = {
  id: number;
  parcel_id: number;
  slot_id: number;
  delivery_date: string;
  start_time: string;
  end_time: string;
  status: string;
  booked_at: string;
  updated_at: string;
};

export type AdminBooking = {
  id: number;
  parcel_id: number;
  slot_id: number;
  status: "booked" | "cancelled";
  booked_at: string;
  updated_at: string;
  parcel: Parcel;
  slot: { id: number; delivery_date: string; start_time: string; end_time: string; capacity: number; booked_count: number; is_active: boolean };
};
