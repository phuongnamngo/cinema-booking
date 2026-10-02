import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi } from "@/api/endpoints";
import type { Booking } from "@/api/types";
import { DebouncedSaver, type SaverStatus } from "@/lib/debouncedSaver";
import { adjustQuantity, draftFromBooking, toItems, totalCount, type Draft } from "./comboDraft";
import { isConflict } from "./errors";
import { bookingKeys } from "./queries";

const DEBOUNCE_MS = 500;

export function useComboEditor(booking: Booking) {
  const queryClient = useQueryClient();
  const code = booking.code;

  // Số lượng đang hiển thị: state cục bộ để phản hồi tức thì.
  // Server chỉ là nơi xác nhận và tính tiền, không phải nguồn của con số này
  const [quantities, setQuantities] = useState<Draft>(() => draftFromBooking(booking.combos));
  const [status, setStatus] = useState<SaverStatus>("idle");
  const [error, setError] = useState<Error | null>(null);
  const draftRef = useRef(quantities); // đọc đồng bộ khi bấm liên tiếp, không phải chờ render
  const saverRef = useRef<DebouncedSaver<Draft> | null>(null);

  const { mutateAsync } = useMutation({
    mutationKey: bookingKeys.edit(code, "combos"),
    mutationFn: async (draft: Draft) => {
      // Lần ghi này làm mọi dữ liệu đang tải dở trở thành cũ: hủy chúng
      await queryClient.cancelQueries({ queryKey: bookingKeys.detail(code) });
      return bookingsApi.setCombos(code, toItems(draft));
    },
    // Callback của useMutation vẫn chạy kể cả khi component đã unmount (khác với callback truyền vào mutate())
    onSuccess: (updated) => {
      queryClient.setQueryData(bookingKeys.detail(code), updated);
      void queryClient.invalidateQueries({ queryKey: bookingKeys.lists });
    },
  });

  useEffect(() => {
    const saver = new DebouncedSaver<Draft>({
      delayMs: DEBOUNCE_MS,
      save: async (draft) => {
        await mutateAsync(draft);
      },
      onStatus: setStatus,
      onError: (err) => {
        setError(err instanceof Error ? err : new Error("Không cập nhật được combo."));
        // Quay về trạng thái server đang có: lần ghi thất bại không làm đổi cache
        const server = draftFromBooking(
          queryClient.getQueryData<Booking>(bookingKeys.detail(code))?.combos ?? [],
        );
        draftRef.current = server;
        setQuantities(server);
        // 409: đơn có thể vừa hết hạn hoặc đã có giao dịch chờ. Hỏi lại server
        if (isConflict(err)) {
          void queryClient.invalidateQueries({ queryKey: bookingKeys.detail(code) });
        }
      },
    });
    saverRef.current = saver;
    return () => {
      saverRef.current = null;
      saver.dispose(); // còn thay đổi chưa gửi thì gửi ngay, không để mất
    };
  }, [code, mutateAsync, queryClient]);

  const adjust = useCallback((comboId: number, delta: number) => {
    const next = adjustQuantity(draftRef.current, comboId, delta);
    if (next === draftRef.current) return;
    draftRef.current = next;
    setQuantities(next);
    setError(null);
    saverRef.current?.schedule(next);
  }, []);

  return { quantities, count: totalCount(quantities), status, error, adjust };
}

export type ComboEditor = ReturnType<typeof useComboEditor>;