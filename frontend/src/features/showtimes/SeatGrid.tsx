import { Fragment, useMemo } from "react";
import type { SeatType, ShowtimeSeat } from "@/api/types";
import { formatVnd } from "@/lib/format";
import type { SeatStatus } from "./seatState";

type Visual = "available" | "selected" | SeatStatus;

const TYPE_LABEL: Record<SeatType, string> = { standard: "Thường", vip: "VIP", couple: "Đôi" };

const VISUAL_LABEL: Record<Visual, string> = {
    available: "còn trống",
    selected: "đang chọn",
    held: "đang có người giữ",
    mine: "bạn đang giữ",
    sold: "đã bán",
};

// Viết đủ tên class (không ghép chuỗi) để Tailwind nhận ra khi quét source
const VISUAL_CLASS: Record<Visual, string> = {
    available: "bg-[#2a2a3a] text-zinc-200 hover:-translate-y-0.5 hover:bg-[#3a3a4e] hover:text-white",
    selected: "animate-seat-pop bg-brand text-white shadow-glow",
    held: "animate-breathe bg-amber-500/70 text-amber-950",
    mine: "bg-hold text-sky-950 shadow-[0_0_14px_rgba(56,189,248,0.45)]",
    sold: "bg-zinc-900 text-zinc-700 line-through",
};

const TYPE_CLASS: Record<SeatType, string> = {
    standard: "w-9",
    vip: "w-9 ring-1 ring-gold/80",
    couple: "w-[4.75rem] ring-1 ring-sweet/80",
};

interface SeatGridProps {
    seats: ShowtimeSeat[];
    statusOf: (seat: ShowtimeSeat) => SeatStatus | undefined;
    selected: number[];
    /** true: không cho chọn thêm ghế (đủ số lượng tối đa, hoặc suất chiếu đã đóng) */
    locked: boolean;
    onToggle: (seat: ShowtimeSeat) => void;
}

export function SeatGrid({ seats, statusOf, selected, locked, onToggle }: SeatGridProps) {
    const rows = useMemo(() => {
        const byRow = new Map<string, ShowtimeSeat[]>();
        for (const seat of seats) {
            const list = byRow.get(seat.row) ?? [];
            list.push(seat);
            byRow.set(seat.row, list);
        }
        return [...byRow.entries()]
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([row, list]) => [row, list.sort((a, b) => a.number - b.number)] as const);
    }, [seats]);

    return (
        <div className="relative overflow-hidden rounded-2xl border border-smoke bg-surface/50 px-4 pb-6 pt-8 backdrop-blur">
            {/* Màn hình cong + chùm sáng chiếu xuống */}
            <div className="relative mx-auto w-4/5" aria-hidden>
                <div className="h-3 rounded-[100%_100%_0_0/100%_100%_0_0] border-t-4 border-white/80 shadow-[0_-6px_30px_rgba(255,255,255,0.35)]" />
                <div className="pointer-events-none absolute left-1/2 top-2 h-40 w-full -translate-x-1/2 bg-[radial-gradient(ellipse_at_top,rgba(255,255,255,0.12),transparent_70%)]" />
            </div>
            <p className="pb-8 pt-2 text-center text-[11px] uppercase tracking-[0.6em] text-dim">Màn hình</p>

            <div className="overflow-x-auto pb-2">
                <div className="mx-auto flex w-max origin-top flex-col gap-2 [transform:perspective(1200px)_rotateX(8deg)]">
                    {rows.map(([row, rowSeats]) => {
                        const aisle = Math.ceil(rowSeats.length / 2);
                        return (
                            <div key={row} className="flex items-center gap-1.5">
                                <span className="w-6 text-center font-mono text-xs text-dim">{row}</span>
                                {rowSeats.map((seat, i) => {
                                    const status = statusOf(seat);
                                    const isSelected = selected.includes(seat.id);
                                    const visual: Visual = status ?? (isSelected ? "selected" : "available");
                                    return (
                                        <Fragment key={seat.id}>
                                            {i === aisle && <span className="w-6" aria-hidden />}
                                            <button
                                                type="button"
                                                disabled={status !== undefined || (locked && !isSelected)}
                                                aria-pressed={isSelected}
                                                aria-label={`Ghế ${seat.label}, ${TYPE_LABEL[seat.seat_type]}, ${formatVnd(seat.price)}, ${VISUAL_LABEL[visual]}`}
                                                title={`${seat.label} · ${TYPE_LABEL[seat.seat_type]} · ${formatVnd(seat.price)}`}
                                                onClick={() => onToggle(seat)}
                                                className={`h-9 rounded-t-xl rounded-b-md text-xs font-semibold transition duration-200 disabled:cursor-not-allowed ${TYPE_CLASS[seat.seat_type]} ${VISUAL_CLASS[visual]}`}
                                            >
                                                {visual === "sold" ? "✕" : visual === "held" ? "🔒" : seat.number}
                                            </button>
                                        </Fragment>
                                    );
                                })}
                                <span className="w-6 text-center font-mono text-xs text-dim">{row}</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

export function SeatLegend() {
    const items: { visual: Visual; label: string }[] = [
        { visual: "available", label: "Trống" },
        { visual: "selected", label: "Đang chọn" },
        { visual: "held", label: "Người khác giữ" },
        { visual: "mine", label: "Bạn đang giữ" },
        { visual: "sold", label: "Đã bán" },
    ];
    return (
        <ul className="flex flex-wrap justify-center gap-2 text-xs text-muted">
            {items.map((item) => (
                <li key={item.visual} className="flex items-center gap-2 rounded-full border border-smoke bg-surface/60 px-3 py-1.5">
                    <span className={`inline-block h-3.5 w-3.5 rounded-t-md rounded-b-sm ${VISUAL_CLASS[item.visual]} animate-none!`} />
                    {item.label}
                </li>
            ))}
            <li className="flex items-center gap-2 rounded-full border border-gold/30 bg-surface/60 px-3 py-1.5 text-gold">
                <span className="inline-block h-3.5 w-3.5 rounded-t-md rounded-b-sm bg-[#2a2a3a] ring-1 ring-gold" /> VIP
            </li>
            <li className="flex items-center gap-2 rounded-full border border-sweet/30 bg-surface/60 px-3 py-1.5 text-sweet">
                <span className="inline-block h-3.5 w-6 rounded-t-md rounded-b-sm bg-[#2a2a3a] ring-1 ring-sweet" /> Đôi
            </li>
        </ul>
    );
}
