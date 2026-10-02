import { apiBlob, apiFetch } from "./client";
import type {
  Booking, BookingStatus, DateRange, Genre, Movie, MovieStatus, OccupancyReport, Page,
  Payment, RegisterInput, RevenueReport, Showtime, ShowtimeSeat, Ticket, TicketLookup,
  TokenPair, TopMoviesReport, User, Combo, ComboItem
} from "./types";

export type MovieFilters = {
  status?: MovieStatus;
  genre?: number;
  search?: string;
  page?: number;
  ordering?: string;
};
export type ShowtimeFilters = { movie?: number; cinema?: number; city?: string; date?: string };
export type BookingFilters = { status?: BookingStatus; page?: number };
export type ProfileInput = Partial<Pick<User, "first_name" | "last_name" | "phone">>;

export const authApi = {
  login: (username: string, password: string) =>
    apiFetch<TokenPair>("/auth/login/", { method: "POST", body: { username, password }, auth: false }),
  register: (input: RegisterInput) =>
    apiFetch<User>("/auth/register/", { method: "POST", body: input, auth: false }),
  logout: (refresh: string) =>
    apiFetch<unknown>("/auth/logout/", { method: "POST", body: { refresh }, auth: false }),
  me: () => apiFetch<User>("/auth/me/"),
  updateMe: (input: ProfileInput) => apiFetch<User>("/auth/me/", { method: "PATCH", body: input }),
};

export const moviesApi = {
  list: (filters: MovieFilters, signal?: AbortSignal) =>
    apiFetch<Page<Movie>>("/movies/", { params: { ...filters }, signal }),
  get: (id: number, signal?: AbortSignal) => apiFetch<Movie>(`/movies/${id}/`, { signal }),
  genres: (signal?: AbortSignal) => apiFetch<Genre[]>("/genres/", { signal }),
};

export const showtimesApi = {
  // page_size=200 là mức tối đa ShowtimePagination cho phép (Bước 5)
  list: (filters: ShowtimeFilters, signal?: AbortSignal) =>
    apiFetch<Page<Showtime>>("/showtimes/", { params: { ...filters, page_size: 200 }, signal }),
  get: (id: number, signal?: AbortSignal) => apiFetch<Showtime>(`/showtimes/${id}/`, { signal }),
  // Endpoint này không phân trang: trả thẳng một mảng ghế
  seats: (id: number, signal?: AbortSignal) =>
    apiFetch<ShowtimeSeat[]>(`/showtimes/${id}/seats/`, { signal }),
};

export const bookingsApi = {
  hold: (showtimeId: number, seatIds: number[]) =>
    apiFetch<Booking>(`/showtimes/${showtimeId}/hold/`, {
      method: "POST",
      body: { seat_ids: seatIds },
    }),
  list: (filters: BookingFilters, signal?: AbortSignal) =>
    apiFetch<Page<Booking>>("/bookings/", { params: { ...filters }, signal }),
  get: (code: string, signal?: AbortSignal) => apiFetch<Booking>(`/bookings/${code}/`, { signal }),
  cancel: (code: string) => apiFetch<Booking>(`/bookings/${code}/cancel/`, { method: "POST" }),
  pay: (code: string) => apiFetch<Payment>(`/bookings/${code}/pay/`, { method: "POST" }),
  cancelPayment: (code: string) =>
    apiFetch<Booking>(`/bookings/${code}/payments/cancel/`, { method: "POST" }),
  /** QR cần token nên không dùng thẳng <img src>: tải bằng fetch rồi nhúng dạng data URL */
  qr: async (code: string, signal?: AbortSignal) =>
    (await apiBlob(`/bookings/${code}/qr/`, { signal })).text(),
  // PUT = "đặt lại toàn bộ": gửi lại hay đến trễ đều vô hại, request cuối thắng
  setCombos: (code: string, items: ComboItem[]) =>
    apiFetch<Booking>(`/bookings/${code}/combos/`, { method: "PUT", body: { items } }),
  applyVoucher: (code: string, voucherCode: string) =>
    apiFetch<Booking>(`/bookings/${code}/voucher/`, { method: "PUT", body: { code: voucherCode } }),
  removeVoucher: (code: string) =>
    apiFetch<Booking>(`/bookings/${code}/voucher/`, { method: "DELETE" }),
};

export const combosApi = {
  // Endpoint này không phân trang: trả thẳng một mảng
  list: (signal?: AbortSignal) => apiFetch<Combo[]>("/combos/", { signal }),
};

export const staffApi = {
  // Chỉ đọc: cho biết vé có check-in được không và vì sao không
  lookup: (code: string, signal?: AbortSignal) =>
    apiFetch<TicketLookup>(`/staff/tickets/${encodeURIComponent(code)}/`, { signal }),
  // Ghi: đánh dấu khách đã vào rạp. Quét lần hai trả 409 (ApiError có reason)
  checkIn: (code: string) =>
    apiFetch<Ticket>("/staff/checkin/", { method: "POST", body: { code } }),
};

export const reportsApi = {
  revenue: (range: DateRange, signal?: AbortSignal) =>
    apiFetch<RevenueReport>("/reports/revenue/", { params: { ...range }, signal }),
  topMovies: (range: DateRange, limit = 5, signal?: AbortSignal) =>
    apiFetch<TopMoviesReport>("/reports/top-movies/", { params: { ...range, limit }, signal }),
  occupancy: (range: DateRange, signal?: AbortSignal) =>
    apiFetch<OccupancyReport>("/reports/occupancy/", { params: { ...range }, signal }),
};