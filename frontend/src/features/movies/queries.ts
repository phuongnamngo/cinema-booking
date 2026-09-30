import { keepPreviousData, skipToken, useQuery } from "@tanstack/react-query";
import { moviesApi, type MovieFilters } from "@/api/endpoints";

export const movieKeys = {
  list: (filters: MovieFilters) => ["movies", "list", filters] as const,
  detail: (id: number) => ["movies", "detail", id] as const,
  genres: ["movies", "genres"] as const,
};

export function useMovies(filters: MovieFilters) {
  return useQuery({
    queryKey: movieKeys.list(filters),
    queryFn: ({ signal }) => moviesApi.list(filters, signal),
    placeholderData: keepPreviousData, // đổi trang/lọc: giữ danh sách cũ trong lúc tải
  });
}

export function useMovie(id: number | undefined) {
  return useQuery({
    queryKey: movieKeys.detail(id ?? 0),
    // skipToken: id không hợp lệ thì query không chạy, và TS vẫn biết id là number bên trong
    queryFn: id === undefined ? skipToken : ({ signal }) => moviesApi.get(id, signal),
  });
}

export function useGenres() {
  return useQuery({
    queryKey: movieKeys.genres,
    queryFn: ({ signal }) => moviesApi.genres(signal),
    staleTime: 10 * 60_000, // thể loại hiếm khi đổi
  });
}