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
        <div className="mx-auto max-w-4xl space-y-6">
            <h1 className="text-2xl font-bold">Soát vé</h1>

            {user?.role === "staff" && user.cinema === null && (
                <p role="alert" className={styles.error}>
                    Tài khoản của bạn chưa được gán rạp nên chưa thể soát vé. Hãy liên hệ quản trị viên.
                </p>
            )}

            <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                    <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-black">
                        <video ref={scanner?.videoRef} muted playsInline className="aspect-square w-full object-cover" />
                        {code !== null && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-sm text-slate-200">
                                Đã quét. Xem kết quả bên cạnh.
                            </div>
                        )}
                    </div>
                    {cameraMessage && <p className="text-sm text-slate-400">{cameraMessage}</p>}

                    <form onSubmit={submitManual} className="flex gap-2">
                        <input
                            value={manual}
                            onChange={(e) => setManual(e.target.value)}
                            placeholder="Hoặc nhập mã vé"
                            aria-label="Mã vé"
                            autoCapitalize="characters"
                            className={`${styles.input} font-mono uppercase`}
                        />
                        <button type="submit" className={styles.button}>
                            Tra cứu
                        </button>
                    </form>
                    {notice && (
                        <p role="alert" className="text-sm text-amber-400">
                            {notice}
                        </p>
                    )}
                </div>

                <div className={`${styles.card} h-fit space-y-4`}>
                    {code === null ? (
                        <p className="text-sm text-slate-400">Đưa mã QR vào khung hình hoặc nhập mã vé.</p>
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
    ok: "border-green-800 bg-green-950 text-green-300",
    bad: "border-red-900 bg-red-950 text-red-300",
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
                <div role="alert" className={`rounded-md border px-3 py-2 text-sm font-semibold ${BANNER[banner.tone]}`}>
                    <p>{banner.text}</p>
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
                <p className="text-lg font-semibold">{ticket.movie_title}</p>
                <p className="text-sm text-slate-400">
                    {ticket.cinema_name} · {ticket.room_name}
                </p>
                <p className="text-sm text-slate-400">{formatDateTime(ticket.start_time)}</p>
            </div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
                <dt className="text-slate-400">Ghế</dt>
                <dd className="font-semibold">{ticket.seats.map((s) => s.label).join(", ")}</dd>
                <dt className="text-slate-400">Khách</dt>
                <dd>{ticket.customer}</dd>
                <dt className="text-slate-400">Mã vé</dt>
                <dd className="font-mono">{ticket.code}</dd>
            </dl>

            <div className="flex gap-3">
                {data.can_check_in && !done && (
                    <button
                        type="button"
                        className={styles.button}
                        disabled={checkIn.isPending}
                        onClick={() => checkIn.mutate(ticket.code)}
                    >
                        {checkIn.isPending ? "Đang xử lý…" : "✓ Cho vào"}
                    </button>
                )}
                <button type="button" className={styles.buttonGhost} onClick={onNext}>
                    Quét vé tiếp
                </button>
            </div>
        </div>
    );
}