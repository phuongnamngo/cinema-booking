import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate, useLocation } from "react-router";
import { getFieldErrors } from "@/api/client";
import type { RegisterInput } from "@/api/types";
import { useAuth } from "@/auth/store";
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
    <div className={`${styles.card} mx-auto max-w-md`}>
      <h1 className="mb-6 text-xl font-bold">Đăng ký</h1>
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
        <Field
          label="Nhập lại mật khẩu"
          type="password"
          autoComplete="new-password"
          required
          {...field("password_confirm")}
        />
        {errors.detail && <p role="alert" className={styles.error}>{errors.detail}</p>}
        <button type="submit" disabled={mutation.isPending} className={`${styles.button} w-full`}>
          {mutation.isPending ? "Đang tạo tài khoản…" : "Đăng ký"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-400">
        Đã có tài khoản?{" "}
        <Link to="/login" state={location.state} className="text-red-400 hover:underline">
          Đăng nhập
        </Link>
      </p>
    </div>
  );
}