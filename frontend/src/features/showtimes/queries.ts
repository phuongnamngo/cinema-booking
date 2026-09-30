import { useQuery } from "@tanstack/react-query";
import { showtimesApi, type ShowtimeFilters } from "@/api/endpoints";

export function useShowtimes(filters: ShowtimeFilters) {
  return useQuery({
    queryKey: ["showtimes", "list", filters] as const,
    queryFn: ({ signal }) => showtimesApi.list(filters, signal),
  });
}