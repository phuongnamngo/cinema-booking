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

  return (
    <div className={`${styles.card} mx-auto max-w-md`}>
      <h1 className="mb-1 text-xl font-bold">Tài khoản</h1>
      <p className="mb-6 text-sm text-slate-400">
        {user.username} · {user.email} · vai trò: {user.role}
      </p>
      <form
        className="space-y-4"
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
        {mutation.isSuccess && <p className="text-sm text-green-400">Đã lưu.</p>}
        <button type="submit" disabled={mutation.isPending} className={styles.button}>
          {mutation.isPending ? "Đang lưu…" : "Lưu thay đổi"}
        </button>
      </form>
    </div>
  );
}