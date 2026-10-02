import { useState, type FormEvent } from "react";
import { skipToken, useMutation, useQuery, type UseMutationResult } from "@tanstack/react-query";
import { staffApi } from "@/api/endpoints";
import type { Ticket, TicketLookup } from "@/api/types";
import { useAuth } from "@/auth/store";
import { styles } from "@/components/styles";
import { ErrorBox, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/format";
import { getTicketRejection, normalizeTicketCode } from "./ticketCode";
import { useQrScanner, type ScannerStatus } from "./useQrScanner";

const SCANNER_MESSAGE: Record<ScannerStatus, string | null> = {
    starting: "Đang bật camera…",
    scanning: null,
    denied: "Chưa được cấp quyền camera. Hãy cho phép camera hoặc nhập mã vé bên dưới.",
    unsupported: "Trình duyệt không hỗ trợ camera (cần HTTPS hoặc localhost). Hãy nhập mã vé bên dưới.",
    error: "Không mở được camera. Hãy nhập mã vé bên dưới.",
};

export function CheckInPage() {
    const user = useAuth((s) => s.user);
    const [code, setCode] = useState<string | null>(null);
    const [manual, setManual] = useState("");
    const [notice, setNotice] = useState<string | null>(null);

    const lookup = useQuery({
        queryKey: ["staff", "ticket", code] as const,
        queryFn: code === null ? skipToken : ({ signal }) => staffApi.lookup(code, signal),
        staleTime: 0, // trạng thái vé phải luôn tươi
        gcTime: 0,
        retry: false, // 403/404 là câu trả lời, không phải lỗi thoáng qua
    });

    const checkIn = useMutation({
        mutationFn: (ticketCode: string) => staffApi.checkIn(ticketCode),
        // Có thể người khác vừa quét: tra cứu lại để hiện ai đã quét và lúc nào
        onError: () => void lookup.refetch(),
    });

    const scanner = useQrScanner({
        paused: code !== null, // có kết quả thì dừng quét, tránh gọi API liên tục
        onScan: (raw) => {
            const normalized = normalizeTicketCode(raw);
            if (normalized) {
                setNotice(null);
                setCode(normalized);
            } else {
                setNotice("Mã QR này không phải vé của hệ thống.");
            }
        },
    });

    function reset() {
        setCode(null);
        setManual("");
        setNotice(null);
        checkIn.reset();
    }

    function submitManual(event: FormEvent) {
        event.preventDefault();
        const normalized = normalizeTicketCode(manual);
        if (!normalized) {
            setNotice("Mã vé gồm 6 đến 12 ký tự chữ và số.");
            return;
        }
        setNotice(null);
        setCode(normalized);
    }

    const cameraMessage = SCANNER_MESSAGE[scanner?.status];

    return (
        <div className="mx-auto max-w-5xl space-y-6">
            <h1 className={styles.heading}>Soát vé</h1>

            {user?.role === "staff" && user.cinema === null && (
                <p role="alert" className={styles.error}>
                    Tài khoản của bạn chưa được gán rạp nên chưa thể soát vé. Hãy liên hệ quản trị viên.
                </p>
            )}

            <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                    <div className="relative overflow-hidden rounded-2xl border border-smoke bg-black shadow-[0_20px_60px_-20px_rgba(225,29,72,0.35)]">
                        <video ref={scanner?.videoRef} muted playsInline className="aspect-square w-full object-cover" />
                        <div className="pointer-events-none absolute inset-6" aria-hidden>
                            <span className="absolute left-0 top-0 h-10 w-10 rounded-tl-xl border-l-4 border-t-4 border-brand drop-shadow-[0_0_8px_rgba(225,29,72,0.8)]" />
                            <span className="absolute right-0 top-0 h-10 w-10 rounded-tr-xl border-r-4 border-t-4 border-brand drop-shadow-[0_0_8px_rgba(225,29,72,0.8)]" />
                            <span className="absolute bottom-0 left-0 h-10 w-10 rounded-bl-xl border-b-4 border-l-4 border-brand drop-shadow-[0_0_8px_rgba(225,29,72,0.8)]" />
                            <span className="absolute bottom-0 right-0 h-10 w-10 rounded-br-xl border-b-4 border-r-4 border-brand drop-shadow-[0_0_8px_rgba(225,29,72,0.8)]" />
                            {code === null && (
                                <span className="absolute inset-x-2 h-0.5 animate-laser bg-brand shadow-[0_0_12px_2px_rgba(225,29,72,0.8)]" />
                            )}
                        </div>
                        {code !== null && (
                            <div className="absolute inset-0 flex animate-fade-in items-center justify-center bg-black/70 text-sm text-zinc-200 backdrop-blur-sm">
                                Đã quét. Xem kết quả bên cạnh.
                            </div>
                        )}
                    </div>
                    {cameraMessage && <p className="text-sm text-muted">{cameraMessage}</p>}

                    <form onSubmit={submitManual} className="flex gap-2">
                        <input
                            value={manual}
                            onChange={(e) => setManual(e.target.value)}
                            placeholder="Hoặc nhập mã vé"
                            aria-label="Mã vé"
                            autoCapitalize="characters"
                            className={`${styles.input} py-3 font-mono text-lg uppercase tracking-widest`}
                        />
                        <button type="submit" className={`${styles.button} px-6`}>
                            Tra cứu
                        </button>
                    </form>
                    {notice && (
                        <p role="alert" className="animate-shake text-sm text-amber-400">
                            {notice}
                        </p>
                    )}
                </div>

                <div className={`${styles.card} h-fit space-y-4`}>
                    {code === null ? (
                        <div className="flex flex-col items-center gap-3 py-12 text-center">
                            <span className="animate-breathe text-5xl" aria-hidden>📷</span>
                            <p className="text-sm text-muted">Đưa mã QR vào khung hình hoặc nhập mã vé.</p>
                        </div>
                    ) : lookup.isLoading ? (
                        <Spinner />
                    ) : lookup.isError ? (
                        <>
                            <ErrorBox error={lookup.error} />
                            <button type="button" className={styles.buttonGhost} onClick={reset}>
                                Quét vé khác
                            </button>
                        </>
                    ) : lookup.data ? (
                        <TicketPanel data={lookup.data} checkIn={checkIn} onNext={reset} />
                    ) : null}
                </div>
            </div>
        </div>
    );
}

const BANNER = {
    ok: "animate-success-pulse border-green-500/50 bg-green-950/60 text-green-300",
    bad: "animate-shake border-red-500/40 bg-red-950/50 text-red-300",
} as const;

function TicketPanel({
    data,
    checkIn,
    onNext,
}: {
    data: TicketLookup;
    checkIn: UseMutationResult<Ticket, Error, string>;
    onNext: () => void;
}) {
    const done = checkIn.isSuccess;
    const ticket = checkIn.data ?? data.ticket; // sau khi cho vào, dùng dữ liệu mới nhất server trả về
    const raceRejection = getTicketRejection(checkIn.error);

    const banner = done
        ? { tone: "ok" as const, text: "✓ Đã cho vào" }
        : data.can_check_in
            ? null
            : { tone: "bad" as const, text: data.message ?? "Vé không hợp lệ." };

    return (
        <div className="space-y-4">
            {banner && (
                <div role="alert" className={`rounded-xl border px-4 py-3 font-semibold ${BANNER[banner.tone]}`}>
                    <p className={banner.tone === "ok" ? "text-xl" : ""}>{banner.text}</p>
                    {!done && ticket.checked_in_at && (
                        <p className="mt-1 font-normal">
                            Quét lúc {formatDateTime(ticket.checked_in_at)}
                            {ticket.checked_in_by && ` bởi ${ticket.checked_in_by}`}
                        </p>
                    )}
                </div>
            )}

            {checkIn.isError && !raceRejection && <ErrorBox error={checkIn.error} />}

            <div className="space-y-1">
                <p className="font-display text-2xl font-semibold uppercase tracking-wide">{ticket.movie_title}</p>
                <p className="text-sm text-muted">
                    {ticket.cinema_name} · {ticket.room_name}
                </p>
                <p className="font-mono text-sm text-muted">{formatDateTime(ticket.start_time)}</p>
            </div>
            <dl className="grid grid-cols-[auto_1fr] items-baseline gap-x-6 gap-y-2 rounded-xl border border-smoke bg-field p-4 text-sm">
                <dt className="text-xs uppercase tracking-wider text-dim">Ghế</dt>
                <dd className="font-mono text-2xl font-bold">{ticket.seats.map((s) => s.label).join(", ")}</dd>
                <dt className="text-xs uppercase tracking-wider text-dim">Khách</dt>
                <dd>{ticket.customer}</dd>
                <dt className="text-xs uppercase tracking-wider text-dim">Mã vé</dt>
                <dd className="font-mono tracking-widest">{ticket.code}</dd>
            </dl>

            <div className="flex flex-wrap gap-3">
                {data.can_check_in && !done && (
                    <button
                        type="button"
                        className="shimmer inline-flex flex-1 items-center justify-center gap-2 rounded-[10px] bg-green-600 px-5 py-3.5 text-base font-semibold text-white transition duration-200 hover:bg-green-500 hover:shadow-[0_0_24px_rgba(34,197,94,0.45)] active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
                        disabled={checkIn.isPending}
                        onClick={() => checkIn.mutate(ticket.code)}
                    >
                        {checkIn.isPending ? "Đang xử lý…" : "✓ Cho vào"}
                    </button>
                )}
                <button type="button" className={`${styles.buttonGhost} py-3.5`} onClick={onNext}>
                    Quét vé tiếp
                </button>
            </div>
        </div>
    );
}