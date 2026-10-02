export type Role = "customer" | "staff" | "admin";
export type MovieStatus = "coming_soon" | "now_showing" | "ended";
export type AgeRating = "P" | "K" | "T13" | "T16" | "T18";

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface TokenPair { access: string; refresh: string }

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: Role;
  cinema: number | null;
  date_joined: string;
}

export interface RegisterInput {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
}

export interface Genre { id: number; name: string }

export interface Movie {
  id: number;
  title: string;
  synopsis: string;
  duration_minutes: number;
  release_date: string; // "YYYY-MM-DD"
  poster_url: string;
  trailer_url: string;
  age_rating: AgeRating;
  status: MovieStatus;
  genres: Genre[];
  created_at: string;
  updated_at: string;
}

export interface Showtime {
  id: number;
  movie: number;
  movie_title: string;
  room: number;
  room_name: string;
  cinema_id: number;
  cinema_name: string;
  start_time: string; // ISO 8601 kèm +07:00
  end_time: string;
  price_standard: number;
  price_vip: number;
  price_couple: number;
  is_active: boolean;
}

export type SeatType = "standard" | "vip" | "couple";
export type SeatState = "available" | "held" | "mine" | "sold";
export type BookingStatus = "pending" | "confirmed" | "expired" | "cancelled";

export interface ShowtimeSeat {
  id: number;
  row: string;
  number: number;
  label: string; // "A1"
  seat_type: SeatType;
  price: number;
  status: SeatState;
}

export interface BookingSeat {
  seat: number;
  label: string;
  seat_type: SeatType;
  price: number;
}

export interface BookingCombo {
  combo: number;
  name: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface Booking {
  id: number;
  code: string;
  status: BookingStatus;
  total_amount: number; // số tiền phải trả, do server tính
  seats_amount: number;
  combos_amount: number;
  discount_amount: number;
  voucher_code: string | null;
  expires_at: string;
  checked_in_at: string | null;
  seconds_left: number;
  showtime: number;
  movie_title: string;
  cinema_name: string;
  room_name: string;
  start_time: string;
  seats: BookingSeat[];
  combos: BookingCombo[];
  has_pending_payment: boolean;
  created_at: string;
}

export interface Combo {
  id: number;
  name: string;
  description: string;
  price: number;
  is_active: boolean;
  sort_order: number;
}

export interface ComboItem {
  combo: number;
  quantity: number;
}

export interface Payment {
  txn_ref: string;
  booking_code: string;
  amount: number;
  status: "pending" | "succeeded" | "failed" | "needs_review" | "cancelled";
  payment_url: string | null;
  expires_at: string;
}

export type RejectReason =
  | "not_confirmed"
  | "already_checked_in"
  | "showtime_cancelled"
  | "too_early"
  | "too_late";

export interface Ticket {
  code: string;
  status: BookingStatus;
  movie_title: string;
  cinema_name: string;
  room_name: string;
  start_time: string;
  end_time: string;
  seats: BookingSeat[];
  customer: string;
  checked_in_at: string | null;
  checked_in_by: string | null;
}

export interface TicketLookup {
  ticket: Ticket;
  can_check_in: boolean;
  reason: RejectReason | null;
  message: string | null;
}

export interface DateRange { date_from: string; date_to: string }

export interface RevenuePoint { date: string; revenue: number; orders: number }
export interface RevenueReport extends DateRange {
  total_revenue: number;
  total_orders: number;
  days: RevenuePoint[];
}

export interface TopMovie { movie_id: number; title: string; tickets: number; revenue: number }
export interface TopMoviesReport extends DateRange { movies: TopMovie[] }

export interface OccupancyRow {
  showtime_id: number;
  movie_title: string;
  cinema_name: string;
  room_name: string;
  start_time: string;
  seats_total: number;
  seats_sold: number;
  occupancy: number; // 0..1
}
export interface OccupancyReport extends DateRange {
  overall_occupancy: number;
  showtimes: OccupancyRow[];
}