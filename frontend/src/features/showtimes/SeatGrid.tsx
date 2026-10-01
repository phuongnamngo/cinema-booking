import { useMemo } from "react";
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
    available: "bg-slate-700 text-slate-100 hover:bg-slate-600",
    selected: "bg-red-600 text-white",
    held: "bg-amber-700/60 text-amber-200",
    mine: "bg-sky-600 text-white",
    sold: "bg-slate-900 text-slate-600 line-through",
};

const TYPE_CLASS: Record<SeatType, string> = {
    standard: "w-9",
    vip: "w-9 ring-1 ring-yellow-500",
    couple: "w-14 ring-1 ring-pink-500",
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
        <div className="space-y-2">
            <div className="mx-auto h-1.5 w-3/4 rounded-full bg-gradient-to-r from-transparent via-slate-400 to-transparent" />
            <p className="pb-4 text-center text-xs uppercase tracking-widest text-slate-500">Màn hình</p>
            <div className="overflow-x-auto pb-2">
                <div className="mx-auto flex w-max flex-col gap-1.5">
                    {rows.map(([row, rowSeats]) => (
                        <div key={row} className="flex items-center gap-1.5">
                            <span className="w-5 text-center text-xs text-slate-500">{row}</span>
                            {rowSeats.map((seat) => {
                                const status = statusOf(seat);
                                const isSelected = selected.includes(seat.id);
                                const visual: Visual = status ?? (isSelected ? "selected" : "available");
                                return (
                                    <button
                                        key={seat.id}
                                        type="button"
                                        disabled={status !== undefined || (locked && !isSelected)}
                                        aria-pressed={isSelected}
                                        aria-label={`Ghế ${seat.label}, ${TYPE_LABEL[seat.seat_type]}, ${formatVnd(seat.price)}, ${VISUAL_LABEL[visual]}`}
                                        title={`${seat.label} · ${TYPE_LABEL[seat.seat_type]} · ${formatVnd(seat.price)}`}
                                        onClick={() => onToggle(seat)}
                                        className={`h-9 rounded-t-lg text-xs font-medium transition disabled:cursor-not-allowed ${TYPE_CLASS[seat.seat_type]} ${VISUAL_CLASS[visual]}`}
                                    >
                                        {seat.number}
                                    </button>
                                );
                            })}
                        </div>
                    ))}
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
        <ul className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-xs text-slate-400">
            {items.map((item) => (
                <li key={item.visual} className="flex items-center gap-1.5">
                    <span className={`inline-block h-4 w-4 rounded-t ${VISUAL_CLASS[item.visual]}`} />
                    {item.label}
                </li>
            ))}
            <li className="flex items-center gap-1.5">
                <span className="inline-block h-4 w-4 rounded-t bg-slate-700 ring-1 ring-yellow-500" /> VIP
            </li>
            <li className="flex items-center gap-1.5">
                <span className="inline-block h-4 w-6 rounded-t bg-slate-700 ring-1 ring-pink-500" /> Đôi
            </li>
        </ul>
    );
}