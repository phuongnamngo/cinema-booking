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