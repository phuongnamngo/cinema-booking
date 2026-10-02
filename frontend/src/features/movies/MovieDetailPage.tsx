import { useMemo, useRef, useState, type CSSProperties, type MouseEvent } from "react";
import { Link, useParams } from "react-router";
import { ApiError } from "@/api/client";
import type { Movie } from "@/api/types";
import { styles } from "@/components/styles";
import { ErrorBox, NotFound, Spinner } from "@/components/ui";
import { useShowtimes } from "@/features/showtimes/queries";
import { formatReleaseDate, formatTime, formatVnd, nextDays, toDateParam } from "@/lib/format";
import { AgeBadge, Poster } from "./MovieCard";
import { useMovie } from "./queries";

const weekdayFmt = new Intl.DateTimeFormat("vi-VN", { weekday: "short" });

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
        <div className="space-y-14">
            <section className="relative -mx-4 -mt-8 overflow-hidden sm:-mx-6">
                <div className="absolute inset-0" aria-hidden>
                    <Poster movie={movie} className="h-full scale-110 object-cover opacity-40 blur-2xl" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-t from-ink via-ink/70 to-ink/30" />
                <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[260px_1fr] md:items-end">
                    <TiltPoster movie={movie} />
                    <div className="stagger space-y-5">
                        <div className="flex items-center gap-2">
                            <AgeBadge rating={movie.age_rating} />
                            <span className="text-xs uppercase tracking-[0.2em] text-muted">
                                {movie.status === "coming_soon" ? "Sắp chiếu" : "Đang chiếu"}
                            </span>
                        </div>
                        <h1 className="font-display text-5xl font-bold uppercase leading-[1.15] tracking-wide sm:text-6xl">
                            {movie.title}
                        </h1>
                        <p className="flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-zinc-300">
                            <span className="flex items-center gap-1.5">⏱ {movie.duration_minutes} phút</span>
                            <span className="flex items-center gap-1.5">📅 Khởi chiếu {formatReleaseDate(movie.release_date)}</span>
                        </p>
                        {movie.genres.length > 0 && (
                            <div className="flex flex-wrap gap-2">
                                {movie.genres.map((g) => (
                                    <span key={g.id} className="rounded-full border border-smoke bg-white/5 px-3 py-1 text-xs backdrop-blur">
                                        {g.name}
                                    </span>
                                ))}
                            </div>
                        )}
                        <p className="max-w-2xl leading-relaxed text-zinc-300">{movie.synopsis || "Chưa có mô tả."}</p>
                        <div className="flex flex-wrap gap-3">
                            <a href="#lich-chieu" className={`${styles.button} px-6 py-3`}>
                                🎟 Đặt vé ngay
                            </a>
                            {movie.trailer_url && (
                                <a href={movie.trailer_url} target="_blank" rel="noreferrer" className={`${styles.buttonGhost} px-5 py-3`}>
                                    ▶ Xem trailer
                                </a>
                            )}
                        </div>
                    </div>
                </div>
            </section>
            <Showtimes movieId={movie.id} />
        </div>
    );
}

/** Poster nghiêng nhẹ theo vị trí chuột */
function TiltPoster({ movie }: { movie: Movie }) {
    const ref = useRef<HTMLDivElement>(null);

    function handleMove(e: MouseEvent<HTMLDivElement>) {
        const el = ref.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        el.style.transform = `perspective(900px) rotateY(${x * 12}deg) rotateX(${-y * 12}deg)`;
    }

    return (
        <div
            ref={ref}
            onMouseMove={handleMove}
            onMouseLeave={() => {
                if (ref.current) ref.current.style.transform = "";
            }}
            className="mx-auto w-52 animate-fade-up overflow-hidden rounded-2xl border border-white/10 shadow-[0_30px_80px_-20px_rgba(225,29,72,0.5)] transition-transform duration-200 ease-out md:w-full"
        >
            <Poster movie={movie} />
        </div>
    );
}

function Showtimes({ movieId }: { movieId: number }) {
    const [days] = useState(() => nextDays(7));
    const [selected, setSelected] = useState(0);
    const showtimes = useShowtimes({ movie: movieId, date: toDateParam(days[selected]) });
    const data = showtimes.data;

    const byCinema = useMemo(() => {
        const groups = new Map<number, { id: number; name: string; items: NonNullable<typeof data>["results"] }>();
        for (const s of data?.results ?? []) {
            const group = groups.get(s.cinema_id) ?? { id: s.cinema_id, name: s.cinema_name, items: [] };
            group.items.push(s);
            groups.set(s.cinema_id, group);
        }
        return [...groups.values()];
    }, [data]);

    return (
        <section id="lich-chieu" className="scroll-mt-24 space-y-6">
            <h2 className="flex items-center gap-3 font-display text-3xl font-semibold uppercase tracking-wide">
                <span className="h-7 w-1 rounded-full bg-brand shadow-glow" />
                Lịch chiếu
            </h2>
            <div className="no-scrollbar flex gap-3 overflow-x-auto pb-2">
                {days.map((day, i) => {
                    const active = selected === i;
                    return (
                        <button
                            key={i}
                            type="button"
                            aria-pressed={active}
                            onClick={() => setSelected(i)}
                            className={`flex w-20 shrink-0 flex-col items-center rounded-2xl border px-3 py-3 transition duration-300 ${
                                active
                                    ? "-translate-y-0.5 border-brand bg-brand text-white shadow-glow"
                                    : "border-smoke bg-surface/70 text-muted hover:border-zinc-500 hover:text-fg"
                            }`}
                        >
                            <span className="text-[11px] font-medium uppercase tracking-wider">
                                {i === 0 ? "Hôm nay" : weekdayFmt.format(day)}
                            </span>
                            <span className="font-display text-3xl font-bold leading-tight">{day.getDate()}</span>
                            <span className="text-[11px] opacity-80">Th {day.getMonth() + 1}</span>
                        </button>
                    );
                })}
            </div>

            {showtimes.isPending ? (
                <div className="space-y-4">
                    {[0, 1].map((i) => (
                        <div key={i} className="skeleton h-36 rounded-2xl" />
                    ))}
                </div>
            ) : showtimes.isError ? (
                <ErrorBox error={showtimes.error} onRetry={() => showtimes.refetch()} />
            ) : byCinema.length === 0 ? (
                <div className={`${styles.card} flex flex-col items-center gap-3 py-12 text-center`}>
                    <span className="animate-breathe text-4xl" aria-hidden>📅</span>
                    <p className="text-muted">Chưa có suất chiếu trong ngày này.</p>
                </div>
            ) : (
                <div key={selected} className="stagger space-y-4">
                    {byCinema.map((group, gi) => (
                        <div key={group.id} className={styles.card} style={{ "--i": gi } as CSSProperties}>
                            <h3 className="flex items-center gap-2 text-lg font-semibold">
                                <span className="text-brand" aria-hidden>📍</span>
                                {group.name}
                            </h3>
                            <div className="mt-4 flex flex-wrap gap-3">
                                {group.items.map((s) => (
                                    <Link
                                        key={s.id}
                                        to={`/showtimes/${s.id}`}
                                        className="group min-w-24 rounded-xl border border-smoke bg-field px-4 py-3 text-center transition duration-300 hover:-translate-y-1 hover:border-brand hover:shadow-glow-sm"
                                    >
                                        <div className="font-mono text-lg font-semibold tabular-nums group-hover:text-brand-hover">
                                            {formatTime(s.start_time)}
                                        </div>
                                        <div className="text-[11px] text-dim">{s.room_name}</div>
                                        <div className="mt-0.5 text-xs text-muted">từ {formatVnd(s.price_standard)}</div>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}
