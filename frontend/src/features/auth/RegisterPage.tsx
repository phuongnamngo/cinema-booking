import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate, useLocation } from "react-router";
import { getFieldErrors } from "@/api/client";
import type { RegisterInput } from "@/api/types";
import { useAuth } from "@/auth/store";
import { AuthShell } from "@/components/AuthShell";
import { styles } from "@/components/styles";
import { Field } from "@/components/ui";

export function RegisterPage() {
  const status = useAuth((s) => s.status);
  const register = useAuth((s) => s.register);
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [form, setForm] = useState<RegisterInput>({
    username: "", email: "", password: "", password_confirm: "",
  });
  const mutation = useMutation({ mutationFn: () => register(form) });

  if (status === "authenticated") return <Navigate to={from} replace />;

  // Mọi kiểm tra do server làm (Bước 3): FE chỉ hiển thị lại lỗi theo từng field
  const errors = getFieldErrors(mutation.error);
  const field = (key: keyof RegisterInput) => ({
    name: key,
    value: form[key],
    error: errors[key],
    onChange: (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value }),
  });

  return (
    <AuthShell title="Đăng ký" tagline="Gia nhập cộng đồng yêu điện ảnh.">
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <Field label="Tên đăng nhập" autoComplete="username" required {...field("username")} />
        <Field label="Email" type="email" autoComplete="email" required {...field("email")} />
        <Field label="Mật khẩu" type="password" autoComplete="new-password" required {...field("password")} />
        <PasswordMeter password={form.password} />
        <Field
          label="Nhập lại mật khẩu"
          type="password"
          autoComplete="new-password"
          required
          {...field("password_confirm")}
        />
        {errors.detail && <p role="alert" className={`${styles.error} animate-shake`}>{errors.detail}</p>}
        <button type="submit" disabled={mutation.isPending} className={`${styles.button} w-full py-3`}>
          {mutation.isPending ? "Đang tạo tài khoản…" : "Đăng ký"}
        </button>
      </form>
      <p className="text-center text-sm text-muted">
        Đã có tài khoản?{" "}
        <Link to="/login" state={location.state} className="font-semibold text-brand-hover hover:underline">
          Đăng nhập
        </Link>
      </p>
    </AuthShell>
  );
}

const STRENGTH = [
  { label: "Yếu", bar: "w-1/4 bg-red-500" },
  { label: "Trung bình", bar: "w-2/4 bg-amber-500" },
  { label: "Khá", bar: "w-3/4 bg-yellow-400" },
  { label: "Mạnh", bar: "w-full bg-green-500" },
];

/** Chỉ là gợi ý trực quan; quy tắc mật khẩu thật do server kiểm tra */
function PasswordMeter({ password }: { password: string }) {
  if (!password) return null;
  const score =
    Number(password.length >= 8) +
    Number(/[A-Z]/.test(password) && /[a-z]/.test(password)) +
    Number(/\d/.test(password)) +
    Number(/[^A-Za-z0-9]/.test(password));
  const level = STRENGTH[Math.max(0, score - 1)];
  return (
    <div className="-mt-2 space-y-1" aria-live="polite">
      <div className="h-1.5 overflow-hidden rounded-full bg-smoke">
        <div className={`h-full rounded-full transition-all duration-500 ${level.bar}`} />
      </div>
      <p className="text-xs text-muted">Độ mạnh: {level.label}</p>
    </div>
  );
}