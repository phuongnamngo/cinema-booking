import { skipToken, useQuery } from "@tanstack/react-query";
import { showtimesApi, type ShowtimeFilters } from "@/api/endpoints";

export function useShowtimes(filters: ShowtimeFilters) {
  return useQuery({
    queryKey: ["showtimes", "list", filters] as const,
    queryFn: ({ signal }) => showtimesApi.list(filters, signal),
  });
}

export function useShowtime(id: number | undefined) {
  return useQuery({
    queryKey: ["showtimes", "detail", id ?? 0] as const,
    queryFn: id === undefined ? skipToken : ({ signal }) => showtimesApi.get(id, signal),
  });
}

/** userId nằm trong key: trạng thái "mine" của REST phụ thuộc người đang đăng nhập */
export function useShowtimeSeats(id: number, userId: number | null) {
  return useQuery({
    queryKey: ["showtimes", "seats", id, userId] as const,
    queryFn: ({ signal }) => showtimesApi.seats(id, signal),
  });
}