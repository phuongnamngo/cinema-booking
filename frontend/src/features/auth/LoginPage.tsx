import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, Navigate, useLocation } from "react-router";
import { ApiError } from "@/api/client";
import { useAuth } from "@/auth/store";
import { styles } from "@/components/styles";
import { Field } from "@/components/ui";

export function LoginPage() {
  const status = useAuth((s) => s.status);
  const login = useAuth((s) => s.login);
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({ mutationFn: () => login(username, password) });

  // Đã đăng nhập (kể cả vừa đăng nhập xong) thì chuyển đi, không cần gọi navigate() thủ công
  if (status === "authenticated") return <Navigate to={from} replace />;

  const error = mutation.error;
  const message =
    error instanceof ApiError && error.status === 401
      ? "Sai tài khoản hoặc mật khẩu."
      : error?.message;

  return (
    <div className={`${styles.card} mx-auto max-w-md`}>
      <h1 className="mb-6 text-xl font-bold">Đăng nhập</h1>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <Field
          label="Email hoặc tên đăng nhập"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <Field
          label="Mật khẩu"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {message && (
          <p role="alert" className={styles.error}>
            {message}
          </p>
        )}
        <button type="submit" disabled={mutation.isPending} className={`${styles.button} w-full`}>
          {mutation.isPending ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
      </form>
      <p className="mt-4 text-center text-sm text-slate-400">
        Chưa có tài khoản?{" "}
        <Link to="/register" state={location.state} className="text-red-400 hover:underline">
          Đăng ký
        </Link>
      </p>
    </div>
  );
}