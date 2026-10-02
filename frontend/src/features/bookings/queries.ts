import { keepPreviousData, skipToken, useQuery } from "@tanstack/react-query";
import { bookingsApi, combosApi, type BookingFilters } from "@/api/endpoints";
import { useAuth } from "@/auth/store";

export const bookingKeys = {
  lists: ["bookings", "list"] as const,
  detail: (code: string) => ["bookings", "detail", code] as const,
  qr: (code: string) => ["bookings", "qr", code] as const,
  // Khóa của MUTATION (không phải query): dùng với useIsMutating để biết đơn đang được ghi
  editing: (code: string) => ["booking-edit", code] as const,
  edit: (code: string, part: "combos" | "voucher") => ["booking-edit", code, part] as const,
};

export function useBookings(filters: BookingFilters, enabled = true) {
  return useQuery({
    queryKey: [...bookingKeys.lists, filters] as const,
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

export function useBooking(code: string | undefined, options: { poll?: boolean } = {}) {
  const { poll = true } = options;
  return useQuery({
    queryKey: bookingKeys.detail(code ?? ""),
    queryFn: code === undefined ? skipToken : ({ signal }) => bookingsApi.get(code, signal),
    // Còn pending thì poll để học việc hết hạn (lazy expiration) hoặc đã thanh toán (webhook).
    // poll=false khi đang ghi: một poll xuất phát trước lúc ghi có thể về sau và đè dữ liệu mới
    refetchInterval: (query) => (poll && query.state.data?.status === "pending" ? 5_000 : false),
  });
}

export function useCombos() {
  return useQuery({
    queryKey: ["combos"] as const,
    queryFn: ({ signal }) => combosApi.list(signal),
    staleTime: 5 * 60_000, // menu bắp nước hiếm khi đổi
  });
}