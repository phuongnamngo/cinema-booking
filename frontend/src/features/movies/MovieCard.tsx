import { Link } from "react-router";
import type { AgeRating, Movie } from "@/api/types";
import { formatReleaseDate } from "@/lib/format";

const AGE_CLASS: Record<AgeRating, string> = {
  P: "bg-green-500/90 text-black",
  K: "bg-sky-400/90 text-black",
  T13: "bg-yellow-400/90 text-black",
  T16: "bg-orange-500/90 text-black",
  T18: "bg-red-600/90 text-white",
};

export function AgeBadge({ rating, className = "" }: { rating: AgeRating; className?: string }) {
  return (
    <span className={`rounded-md px-1.5 py-0.5 text-[11px] font-bold tracking-wide ${AGE_CLASS[rating]} ${className}`}>
      {rating}
    </span>
  );
}

export function Poster({ movie, className = "" }: { movie: Movie; className?: string }) {
  if (movie.poster_url) {
    return (
      <img
        src={movie.poster_url}
        alt={movie.title}
        loading="lazy"
        className={`aspect-[2/3] w-full object-cover ${className}`}
      />
    );
  }
  // Phim chưa có poster: hiển thị khung thay thế
  return (
    <div
      className={`flex aspect-[2/3] w-full items-center justify-center bg-[radial-gradient(circle_at_30%_20%,rgba(225,29,72,0.35),transparent_60%),linear-gradient(160deg,#1f1f2e,#0a0a0f)] font-display text-7xl font-bold text-white/15 ${className}`}
      aria-hidden
    >
      {movie.title.charAt(0)}
    </div>
  );
}

export function MovieCard({ movie }: { movie: Movie }) {
  return (
    <Link
      to={`/movies/${movie.id}`}
      className="group block space-y-3 rounded-2xl transition duration-300 ease-[var(--ease-cinema)] hover:-translate-y-1.5"
    >
      <div className="relative overflow-hidden rounded-2xl border border-smoke bg-surface transition duration-300 group-hover:border-brand/60 group-hover:shadow-lift">
        <Poster movie={movie} className="transition duration-700 ease-[var(--ease-cinema)] group-hover:scale-[1.08]" />
        <AgeBadge rating={movie.age_rating} className="absolute left-3 top-3 shadow" />
        <div className="absolute inset-x-0 bottom-0 flex translate-y-full items-end justify-center bg-gradient-to-t from-black via-black/70 to-transparent p-4 pt-16 transition duration-300 ease-[var(--ease-cinema)] group-hover:translate-y-0">
          <span className="shimmer rounded-[10px] bg-brand px-4 py-2 text-sm font-semibold text-white shadow-glow">
            {movie.status === "coming_soon" ? "Xem chi tiết" : "Đặt vé"}
          </span>
        </div>
      </div>
      <div className="px-1">
        <h3 className="line-clamp-2 font-semibold leading-tight transition group-hover:text-brand-hover">{movie.title}</h3>
        <p className="mt-1 text-xs text-muted">
          {movie.status === "coming_soon"
            ? `Khởi chiếu ${formatReleaseDate(movie.release_date)}`
            : `${movie.duration_minutes} phút`}
          {movie.genres.length > 0 && ` · ${movie.genres.map((g) => g.name).join(", ")}`}
        </p>
      </div>
    </Link>
  );
}
