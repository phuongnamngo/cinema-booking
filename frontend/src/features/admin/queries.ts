import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { reportsApi } from "@/api/endpoints";
import type { DateRange } from "@/api/types";

// Đổi khoảng ngày: giữ dữ liệu cũ trong lúc tải. Báo cáo không cần tươi từng giây
const options = { placeholderData: keepPreviousData, staleTime: 60_000 } as const;

export const useRevenue = (range: DateRange) =>
  useQuery({
    queryKey: ["reports", "revenue", range] as const,
    queryFn: ({ signal }) => reportsApi.revenue(range, signal),
    ...options,
  });

export const useTopMovies = (range: DateRange) =>
  useQuery({
    queryKey: ["reports", "top-movies", range] as const,
    queryFn: ({ signal }) => reportsApi.topMovies(range, 5, signal),
    ...options,
  });

export const useOccupancy = (range: DateRange) =>
  useQuery({
    queryKey: ["reports", "occupancy", range] as const,
    queryFn: ({ signal }) => reportsApi.occupancy(range, signal),
    ...options,
  });