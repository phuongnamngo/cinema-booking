import { useState, type ChangeEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { getFieldErrors } from "@/api/client";
import { authApi } from "@/api/endpoints";
import type { User } from "@/api/types";
import { useAuth } from "@/auth/store";
import { styles } from "@/components/styles";
import { Field } from "@/components/ui";

export function AccountPage() {
  const user = useAuth((s) => s.user);
  if (!user) return null; // RequireAuth đã đảm bảo có user, dòng này chỉ để thu hẹp kiểu
  return <ProfileForm user={user} />;
}

function ProfileForm({ user }: { user: User }) {
  const setUser = useAuth((s) => s.setUser);
  const [form, setForm] = useState({
    first_name: user.first_name, last_name: user.last_name, phone: user.phone,
  });
  const mutation = useMutation({
    mutationFn: () => authApi.updateMe(form),
    onSuccess: (updated) => setUser(updated),
  });
  const errors = getFieldErrors(mutation.error);

  const bind = (key: keyof typeof form) => ({
    name: key,
    value: form[key],
    error: errors[key],
    onChange: (e: ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value }),
  });

  const initial = (user.first_name || user.username).charAt(0);

  return (
    <div className={`${styles.card} relative mx-auto max-w-md overflow-hidden`}>
      <div className="pointer-events-none absolute -right-20 -top-20 h-56 w-56 rounded-full bg-brand/20 blur-3xl" aria-hidden />
      <div className="relative mb-8 flex flex-col items-center text-center">
        <div className="relative h-24 w-24">
          <span
            className="absolute inset-0 animate-spin-slow rounded-full bg-[conic-gradient(from_0deg,#e11d48,#f5c451,#e11d48,transparent,#e11d48)]"
            aria-hidden
          />
          <span className="absolute inset-1 flex items-center justify-center rounded-full bg-surface font-display text-4xl font-bold uppercase">
            {initial}
          </span>
        </div>
        <h1 className={`${styles.heading} mt-4`}>Tài khoản</h1>
        <p className="mt-1 text-sm text-muted">
          {user.username} · {user.email}
        </p>
        <span className="mt-3 rounded-full border border-gold/40 bg-gold/10 px-3 py-0.5 text-xs font-semibold uppercase tracking-wider text-gold">
          {user.role}
        </span>
      </div>
      <form
        className="relative space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <Field label="Họ" {...bind("last_name")} />
        <Field label="Tên" {...bind("first_name")} />
        <Field label="Số điện thoại" type="tel" {...bind("phone")} />
        {mutation.isError && !Object.keys(errors).length && (
          <p role="alert" className={styles.error}>{mutation.error.message}</p>
        )}
        {mutation.isSuccess && (
          <p role="status" className="flex animate-fade-up items-center gap-2 rounded-[10px] border border-green-500/30 bg-green-950/40 px-3.5 py-2.5 text-sm text-green-300">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
              <path d="M5 12.5l4.5 4.5L19 7.5" strokeDasharray="48" className="animate-draw" />
            </svg>
            Đã lưu.
          </p>
        )}
        <button type="submit" disabled={mutation.isPending} className={`${styles.button} w-full py-3`}>
          {mutation.isPending ? "Đang lưu…" : "Lưu thay đổi"}
        </button>
      </form>
    </div>
  );
}
