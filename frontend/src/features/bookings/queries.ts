import { keepPreviousData, skipToken, useQuery } from "@tanstack/react-query";
import { bookingsApi, type BookingFilters } from "@/api/endpoints";
import { useAuth } from "@/auth/store";

export function useBookings(filters: BookingFilters, enabled = true) {
  return useQuery({
    queryKey: ["bookings", "list", filters] as const,
    queryFn: ({ signal }) => bookingsApi.list(filters, signal),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** Đơn đang giữ ghế của mình ở suất chiếu này (nếu có) */
export function usePendingBooking(showtimeId: number) {
  const authenticated = useAuth((s) => s.status === "authenticated");
  const query = useBookings({ status: "pending" }, authenticated);
  return query.data?.results.find((b) => b.showtime === showtimeId);
}

export function useBooking(code: string | undefined) {
  return useQuery({
    queryKey: ["bookings", "detail", code ?? ""] as const,
    queryFn: code === undefined ? skipToken : ({ signal }) => bookingsApi.get(code, signal),
    // Còn pending thì poll: học được việc hết hạn (lazy expiration ở server) hoặc đã thanh toán (webhook)
    refetchInterval: (query) => (query.state.data?.status === "pending" ? 5_000 : false),
  });
}