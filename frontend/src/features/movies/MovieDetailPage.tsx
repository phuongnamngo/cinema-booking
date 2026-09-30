import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError } from "@/api/client";
import { styles } from "@/components/styles";
import { ErrorBox, NotFound, Spinner } from "@/components/ui";
import { useShowtimes } from "@/features/showtimes/queries";
import {
    formatDayLabel, formatReleaseDate, formatTime, formatVnd, nextDays, toDateParam,
} from "@/lib/format";
import { Poster } from "./MovieCard";
import { useMovie } from "./queries";

export function MovieDetailPage() {
    const { id } = useParams();
    const movieId = Number(id);
    const valid = Number.isInteger(movieId) && movieId > 0;
    const { data: movie, error, isPending, refetch } = useMovie(valid ? movieId : undefined);

    if (!valid) return <NotFound />;
    if (error instanceof ApiError && error.status === 404) return <NotFound />;
    if (error) return <ErrorBox error={error} onRetry={() => refetch()} />;
    if (isPending) return <Spinner />;

    return (
        <div className="space-y-10">
            <div className="grid gap-8 md:grid-cols-[240px_1fr]">
                <Poster movie={movie} />
                <div className="space-y-4">
                    <h1 className="text-3xl font-bold">{movie.title}</h1>
                    <p className="text-sm text-slate-400">
                        {movie.duration_minutes} phút · {movie.age_rating} · Khởi chiếu{" "}
                        {formatReleaseDate(movie.release_date)}
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {movie.genres.map((g) => (
                            <span key={g.id} className="rounded-full bg-slate-800 px-3 py-1 text-xs">
                                {g.name}
                            </span>
                        ))}
                    </div>
                    <p className="leading-relaxed text-slate-300">{movie.synopsis || "Chưa có mô tả."}</p>
                    {movie.trailer_url && (
                        <a href={movie.trailer_url} target="_blank" rel="noreferrer" className={styles.buttonGhost}>
                            ▶ Xem trailer
                        </a>
                    )}
                </div>
            </div>
            <Showtimes movieId={movie.id} />
        </div>
    );
}

function Showtimes({ movieId }: { movieId: number }) {
    const [days] = useState(() => nextDays(7));
    const [selected, setSelected] = useState(0);
    const showtimes = useShowtimes({ movie: movieId, date: toDateParam(days[selected]) });

    const byCinema = useMemo(() => {
        const groups = new Map<number, { id: number; name: string; items: NonNullable<typeof showtimes.data>["results"] }>();
        for (const s of showtimes.data?.results ?? []) {
            const group = groups.get(s.cinema_id) ?? { id: s.cinema_id, name: s.cinema_name, items: [] };
            group.items.push(s);
            groups.set(s.cinema_id, group);
        }
        return [...groups.values()];
    }, [showtimes.data]);

    return (
        <section className="space-y-4">
            <h2 className="text-xl font-bold">Lịch chiếu</h2>
            <div className="flex gap-2 overflow-x-auto pb-1">
                {days.map((day, i) => (
                    <button
                        key={i}
                        type="button"
                        onClick={() => setSelected(i)}
                        className={`shrink-0 rounded-md px-3 py-2 text-sm transition ${selected === i ? "bg-red-600 text-white" : "bg-slate-900 text-slate-300 hover:bg-slate-800"
                            }`}
                    >
                        {formatDayLabel(day)}
                    </button>
                ))}
            </div>

            {showtimes.isPending ? (
                <Spinner />
            ) : showtimes.isError ? (
                <ErrorBox error={showtimes.error} onRetry={() => showtimes.refetch()} />
            ) : byCinema.length === 0 ? (
                <p className="text-slate-400">Chưa có suất chiếu trong ngày này.</p>
            ) : (
                byCinema.map((group) => (
                    <div key={group.id} className="rounded-lg border border-slate-800 p-4">
                        <h3 className="font-semibold">{group.name}</h3>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {group.items.map((s) => (
                                <Link
                                    key={s.id}
                                    to={`/showtimes/${s.id}`}
                                    className="rounded-md border border-slate-700 px-3 py-2 text-center text-sm transition hover:border-red-500"
                                >
                                    <div className="font-semibold">{formatTime(s.start_time)}</div>
                                    <div className="text-xs text-slate-400">từ {formatVnd(s.price_standard)}</div>
                                </Link>
                            ))}
                        </div>
                    </div>
                ))
            )}
        </section>
    );
}