import { Link } from "react-router";
import type { Movie } from "@/api/types";
import { formatReleaseDate } from "@/lib/format";

export function Poster({ movie }: { movie: Movie }) {
  if (movie.poster_url) {
    return (
      <img
        src={movie.poster_url}
        alt={movie.title}
        loading="lazy"
        className="aspect-[2/3] w-full rounded-lg object-cover"
      />
    );
  }
  // Chưa có poster (dữ liệu seed): hiển thị khung thay thế
  return (
    <div className="flex aspect-[2/3] w-full items-center justify-center rounded-lg bg-gradient-to-br from-slate-700 to-slate-900 text-5xl font-bold text-slate-500">
      {movie.title.charAt(0)}
    </div>
  );
}

export function MovieCard({ movie }: { movie: Movie }) {
  return (
    <Link to={`/movies/${movie.id}`} className="group block space-y-2">
      <div className="relative overflow-hidden rounded-lg ring-red-500 transition group-hover:ring-2">
        <Poster movie={movie} />
        <span className="absolute left-2 top-2 rounded bg-black/70 px-1.5 py-0.5 text-xs font-bold">
          {movie.age_rating}
        </span>
      </div>
      <h3 className="line-clamp-2 font-semibold leading-tight">{movie.title}</h3>
      <p className="text-xs text-slate-400">
        {movie.status === "coming_soon"
          ? `Khởi chiếu ${formatReleaseDate(movie.release_date)}`
          : `${movie.duration_minutes} phút`}
        {movie.genres.length > 0 && ` · ${movie.genres.map((g) => g.name).join(", ")}`}
      </p>
    </Link>
  );
}