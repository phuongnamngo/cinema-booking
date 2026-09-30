import { useSearchParams } from "react-router";
import type { MovieStatus } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox } from "@/components/ui";
import { MovieCard } from "./MovieCard";
import { useGenres, useMovies } from "./queries";

const TABS: { value: MovieStatus; label: string }[] = [
  { value: "now_showing", label: "Đang chiếu" },
  { value: "coming_soon", label: "Sắp chiếu" },
];

export function HomePage() {
  // URL là nguồn sự thật của bộ lọc: link chia sẻ được, nút Back hoạt động
  const [params, setParams] = useSearchParams();
  const status: MovieStatus = params.get("status") === "coming_soon" ? "coming_soon" : "now_showing";
  const genre = Number(params.get("genre")) || undefined;
  const search = params.get("search") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);

  const movies = useMovies({ status, genre, search: search || undefined, page });
  const genres = useGenres();

  function update(changes: Record<string, string | undefined>, resetPage = true) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetPage) next.delete("page");
    setParams(next);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <div role="tablist" className="flex gap-1 rounded-lg bg-slate-900 p-1">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              type="button"
              role="tab"
              aria-selected={status === tab.value}
              onClick={() => update({ status: tab.value === "now_showing" ? undefined : tab.value })}
              className={`rounded-md px-4 py-1.5 text-sm font-medium transition ${
                status === tab.value ? "bg-red-600 text-white" : "text-slate-300 hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <select
          aria-label="Thể loại"
          value={genre ?? ""}
          onChange={(e) => update({ genre: e.target.value || undefined })}
          className={`${styles.input} w-auto`}
        >
          <option value="">Tất cả thể loại</option>
          {genres.data?.map((g) => (
            <option key={g.id} value={g.id}>
              {g.name}
            </option>
          ))}
        </select>

        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const q = new FormData(e.currentTarget).get("search");
            update({ search: String(q ?? "").trim() || undefined });
          }}
        >
          <input
            key={search} // URL đổi (vd bấm Back) thì ô nhập được reset theo
            name="search"
            defaultValue={search}
            placeholder="Tìm phim…"
            className={`${styles.input} w-48`}
          />
          <button type="submit" className={styles.buttonGhost}>
            Tìm
          </button>
        </form>
      </div>

      {movies.isPending ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="aspect-[2/3] animate-pulse rounded-lg bg-slate-900" />
          ))}
        </div>
      ) : movies.isError ? (
        <ErrorBox error={movies.error} onRetry={() => movies.refetch()} />
      ) : movies.data.results.length === 0 ? (
        <p className="py-16 text-center text-slate-400">Không có phim phù hợp.</p>
      ) : (
        <>
          <div
            className={`grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 ${
              movies.isPlaceholderData ? "opacity-60" : ""
            }`}
          >
            {movies.data.results.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
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
            <span className="text-sm text-slate-400">Trang {page}</span>
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