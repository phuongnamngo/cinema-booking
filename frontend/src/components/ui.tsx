import type { ComponentProps } from "react";
import { Link } from "react-router";
import { styles } from "./styles";

export function Field({
  label, error, id, ...props
}: ComponentProps<"input"> & { label: string; error?: string }) {
  const inputId = id ?? props.name;
  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-xs font-medium uppercase tracking-wider text-muted">
        {label}
      </label>
      <input id={inputId} aria-invalid={error ? true : undefined} className={styles.input} {...props} />
      {error && (
        <p role="alert" className="animate-fade-in text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Đã có lỗi xảy ra.";
  return (
    <div role="alert" className={`${styles.error} animate-shake`}>
      <p>{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={`${styles.buttonGhost} mt-3`}>
          Thử lại
        </button>
      )}
    </div>
  );
}

export function Spinner() {
  return (
    <div className="flex justify-center py-16" role="status" aria-label="Đang tải">
      <div className="h-9 w-9 animate-spin rounded-full border-2 border-smoke border-t-brand shadow-glow-sm" />
    </div>
  );
}

export function NotFound() {
  return (
    <div className="flex min-h-[60vh] animate-fade-up flex-col items-center justify-center text-center">
      <p className="animate-flicker font-display text-[9rem] font-bold leading-none text-brand sm:text-[12rem]">
        404
      </p>
      <h1 className={`${styles.heading} mt-4`}>Không tìm thấy trang</h1>
      <p className="mt-2 max-w-md text-muted">
        Cuộn phim này dường như đã thất lạc, hoặc dữ liệu bạn tìm không còn nữa.
      </p>
      <Link to="/" className={`${styles.button} mt-8`}>
        Về trang chủ
      </Link>
    </div>
  );
}

export function Forbidden() {
  return (
    <div className="animate-fade-up py-20 text-center">
      <p className="font-display text-6xl font-bold text-brand/80">403</p>
      <p className="mt-4 text-lg font-semibold">Bạn không có quyền truy cập trang này.</p>
      <p className="mt-1 text-sm text-muted">Hãy đăng nhập bằng tài khoản phù hợp.</p>
    </div>
  );
}
