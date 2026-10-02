import { useEffect, useState, type CSSProperties } from "react";
import { Link, useSearchParams } from "react-router";
import type { Movie, MovieStatus } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox } from "@/components/ui";
import { AgeBadge, MovieCard, Poster } from "./MovieCard";
import { useGenres, useMovies } from "./queries";

const TABS: { value: MovieStatus; label: string }[] = [
  { value: "now_showing", label: "Đang chiếu" },
  { value: "coming_soon", label: "Sắp chiếu" },
];
const HERO_COUNT = 3;
const HERO_INTERVAL_MS = 7000;

export function HomePage() {
  // URL là nguồn sự thật của bộ lọc: link chia sẻ được, nút Back hoạt động
  const [params, setParams] = useSearchParams();
  const status: MovieStatus = params.get("status") === "coming_soon" ? "coming_soon" : "now_showing";
  const genre = Number(params.get("genre")) || undefined;
  const search = params.get("search") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);

  const movies = useMovies({ status, genre, search: search || undefined, page });
  const genres = useGenres();
  // Cùng khóa với danh sách mặc định nên dùng chung cache, không gọi API thêm
  const featured = useMovies({ status: "now_showing", genre: undefined, search: undefined, page: 1 });

  function update(changes: Record<string, string | undefined>, resetPage = true) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetPage) next.delete("page");
    setParams(next);
  }

  const heroMovies = featured.data?.results.slice(0, HERO_COUNT) ?? [];

  return (
    <div className="space-y-10">
      {heroMovies.length > 0 && <HeroSpotlight movies={heroMovies} />}

      <div className="sticky top-16 z-20 -mx-4 flex flex-wrap items-center gap-3 border-b border-white/5 bg-ink/80 px-4 py-3 backdrop-blur-xl sm:-mx-6 sm:px-6">
        <div role="tablist" className={styles.tabList}>
          {TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={status === tab.value}
              onClick={() => update({ status: tab.value === "now_showing" ? undefined : tab.value })}
              className={`${styles.tab} ${status === tab.value ? styles.tabActive : styles.tabIdle}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="no-scrollbar flex min-w-0 flex-1 gap-2 overflow-x-auto" role="group" aria-label="Thể loại">
          {[{ id: 0, name: "Tất cả" }, ...(genres.data ?? [])].map((g) => {
            const active = (genre ?? 0) === g.id;
            return (
              <button
                key={g.id}
                type="button"
                aria-pressed={active}
                onClick={() => update({ genre: g.id ? String(g.id) : undefined })}
                className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs font-medium transition ${
                  active
                    ? "border-brand bg-brand/15 text-fg shadow-glow-sm"
                    : "border-smoke text-muted hover:border-zinc-500 hover:text-fg"
                }`}
              >
                {g.name}
              </button>
            );
          })}
        </div>

        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const q = new FormData(e.currentTarget).get("search");
            update({ search: String(q ?? "").trim() || undefined });
          }}
        >
          <div className="relative">
            <svg
              aria-hidden
              viewBox="0 0 24 24"
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dim"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" />
            </svg>
            <input
              key={search} // URL đổi (vd bấm Back) thì ô nhập được reset theo
              name="search"
              defaultValue={search}
              placeholder="Tìm phim…"
              aria-label="Tìm phim"
              className={`${styles.input} w-44 pl-9 transition-[width] duration-300 focus:w-60`}
            />
          </div>
          <button type="submit" className={styles.buttonGhost}>
            Tìm
          </button>
        </form>
      </div>

      <div className="flex items-end justify-between gap-4">
        <h2 className="flex items-center gap-3 font-display text-3xl font-semibold uppercase tracking-wide">
          <span className="h-7 w-1 rounded-full bg-brand shadow-glow" />
          {status === "now_showing" ? "Phim đang chiếu" : "Phim sắp chiếu"}
        </h2>
        {movies.data && <span className="text-sm text-muted">{movies.data.count} phim</span>}
      </div>

      {movies.isPending ? (
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="space-y-3">
              <div className="skeleton aspect-[2/3] rounded-2xl" />
              <div className="skeleton h-4 w-3/4 rounded" />
              <div className="skeleton h-3 w-1/2 rounded" />
            </div>
          ))}
        </div>
      ) : movies.isError ? (
        <ErrorBox error={movies.error} onRetry={() => movies.refetch()} />
      ) : movies.data.results.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-20 text-center">
          <span className="text-5xl opacity-40" aria-hidden>🎞️</span>
          <p className="text-muted">Không có phim phù hợp.</p>
        </div>
      ) : (
        <>
          <div
            className={`stagger grid grid-cols-2 gap-5 transition-opacity sm:grid-cols-3 lg:grid-cols-4 ${
              movies.isPlaceholderData ? "opacity-60" : ""
            }`}
          >
            {movies.data.results.map((movie, i) => (
              <div key={movie.id} style={{ "--i": i } as CSSProperties}>
                <MovieCard movie={movie} />
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-4">
            <button
              type="button"
              className={styles.buttonGhost}
              disabled={!movies.data.previous}
              onClick={() => update({ page: String(page - 1) }, false)}
            >
              ← Trước
            </button>
            <span className="flex h-9 min-w-9 items-center justify-center rounded-full bg-brand px-3 text-sm font-semibold shadow-glow-sm">
              {page}
            </span>
            <button
              type="button"
              className={styles.buttonGhost}
              disabled={!movies.data.next}
              onClick={() => update({ page: String(page + 1) }, false)}
            >
              Sau →
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function HeroSpotlight({ movies }: { movies: Movie[] }) {
  const [index, setIndex] = useState(0);
  const current = movies[index % movies.length];

  useEffect(() => {
    if (movies.length < 2) return;
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % movies.length), HERO_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [movies.length]);

  return (
    <section className="relative -mx-4 -mt-8 overflow-hidden sm:-mx-6" aria-roledescription="carousel" aria-label="Phim nổi bật">
      {movies.map((movie, i) => (
        <div
          key={movie.id}
          className={`absolute inset-0 transition-opacity duration-1000 ${i === index % movies.length ? "opacity-100" : "opacity-0"}`}
          aria-hidden
        >
          <Poster movie={movie} className="h-full animate-kenburns object-cover opacity-50 blur-sm" />
        </div>
      ))}
      <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/80 to-ink/20" />
      <div className="absolute inset-0 bg-gradient-to-t from-ink via-transparent to-ink/40" />

      <div key={current.id} className="relative mx-auto flex min-h-[460px] max-w-7xl items-center gap-10 px-4 py-16 sm:px-6">
        <div className="max-w-2xl animate-fade-up space-y-5">
          <p className="inline-flex items-center gap-2 rounded-full border border-brand/40 bg-brand/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-brand-hover">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand" /> Phim đang hot
          </p>
          <h1 className="font-display text-5xl font-bold uppercase leading-[1.15] tracking-wide drop-shadow-[0_4px_30px_rgba(0,0,0,0.8)] sm:text-7xl">
            {current.title}
          </h1>
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <span>{current.duration_minutes} phút</span>
            <span aria-hidden>·</span>
            <AgeBadge rating={current.age_rating} />
            {current.genres.length > 0 && (
              <>
                <span aria-hidden>·</span>
                <span>{current.genres.map((g) => g.name).join(", ")}</span>
              </>
            )}
          </p>
          {current.synopsis && <p className="line-clamp-2 max-w-xl text-zinc-300">{current.synopsis}</p>}
          <div className="flex flex-wrap gap-3 pt-2">
            <Link to={`/movies/${current.id}`} className={`${styles.button} px-6 py-3`}>
              🎟 Đặt vé ngay
            </Link>
            {current.trailer_url && (
              <a href={current.trailer_url} target="_blank" rel="noreferrer" className={`${styles.buttonGhost} px-5 py-3`}>
                ▶ Xem trailer
              </a>
            )}
          </div>
        </div>
        <div className="ml-auto hidden w-56 shrink-0 rotate-2 animate-fade-up overflow-hidden rounded-2xl border border-white/10 shadow-[0_30px_80px_-20px_rgba(225,29,72,0.45)] lg:block">
          <Poster movie={current} />
        </div>
      </div>

      {movies.length > 1 && (
        <div className="absolute bottom-6 left-1/2 flex -translate-x-1/2 gap-2">
          {movies.map((movie, i) => (
            <button
              key={movie.id}
              type="button"
              aria-label={`Phim nổi bật ${i + 1}`}
              aria-current={i === index % movies.length}
              onClick={() => setIndex(i)}
              className={`h-1.5 rounded-full transition-all duration-500 ${
                i === index % movies.length ? "w-8 bg-brand shadow-glow-sm" : "w-3 bg-white/30 hover:bg-white/60"
              }`}
            />
          ))}
        </div>
      )}
    </section>
  );
}
