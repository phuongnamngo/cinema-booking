import { useMutation, useQueryClient } from "@tanstack/react-query";
import { bookingsApi } from "@/api/endpoints";
import { isConflict } from "./errors";
import { bookingKeys } from "./queries";

export type VoucherAction = { kind: "apply"; code: string } | { kind: "remove" };

/** Một mutation cho cả áp và gỡ mã: chỉ có một trạng thái pending/error để hiển thị */
export function useVoucherActions(code: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: bookingKeys.edit(code, "voucher"),
    mutationFn: async (action: VoucherAction) => {
      await queryClient.cancelQueries({ queryKey: bookingKeys.detail(code) });
      return action.kind === "apply"
        ? bookingsApi.applyVoucher(code, action.code)
        : bookingsApi.removeVoucher(code);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(bookingKeys.detail(code), updated);
      void queryClient.invalidateQueries({ queryKey: bookingKeys.lists });
    },
    onError: (error) => {
      if (isConflict(error)) void queryClient.invalidateQueries({ queryKey: bookingKeys.detail(code) });
    },
  });
}

export type VoucherActions = ReturnType<typeof useVoucherActions>;