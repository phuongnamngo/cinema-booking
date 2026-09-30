import { apiFetch } from "./client";
import type {
    Genre, Movie, MovieStatus, Page, RegisterInput, Showtime, TokenPair, User,
} from "./types";

export type MovieFilters = {
    status?: MovieStatus;
    genre?: number;
    search?: string;
    page?: number;
    ordering?: string;
};
export type ShowtimeFilters = { movie?: number; cinema?: number; city?: string; date?: string };
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
};