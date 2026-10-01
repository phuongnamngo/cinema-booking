import type { ComponentProps } from "react";
import { styles } from "./styles";

export function Field({
  label, error, id, ...props
}: ComponentProps<"input"> & { label: string; error?: string }) {
  const inputId = id ?? props.name;
  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-300">
        {label}
      </label>
      <input id={inputId} aria-invalid={error ? true : undefined} className={styles.input} {...props} />
      {error && (
        <p role="alert" className="text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Đã có lỗi xảy ra.";
  return (
    <div role="alert" className={styles.error}>
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={`${styles.buttonGhost} mt-2`}>
          Thử lại
        </button>
      )}
    </div>
  );
}

export function Spinner() {
  return (
    <div className="flex justify-center py-16" role="status" aria-label="Đang tải">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-700 border-t-red-500" />
    </div>
  );
}

export function NotFound() {
  return <p className="py-16 text-center text-slate-400">Không tìm thấy trang hoặc dữ liệu này.</p>;
}

export function Forbidden() {
  return (
    <div className="py-16 text-center">
      <p className="text-lg font-semibold">Bạn không có quyền truy cập trang này.</p>
      <p className="mt-1 text-sm text-slate-400">Hãy đăng nhập bằng tài khoản phù hợp.</p>
    </div>
  );
}