import { create } from "zustand";
import { refreshAccessToken, setSessionExpiredHandler } from "@/api/client";
import { authApi } from "@/api/endpoints";
import { queryClient } from "@/api/queryClient";
import type { RegisterInput, User } from "@/api/types";
import { tokens } from "./tokens";

type Status = "loading" | "authenticated" | "anonymous";

interface AuthState {
  status: Status;
  user: User | null;
  bootstrap: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

export const useAuth = create<AuthState>()((set, get) => ({
  status: "loading",
  user: null,

  /** Gọi 1 lần lúc khởi động: có refresh token thì đổi lấy access token và tải user */
  async bootstrap() {
    if (!tokens.getRefresh()) {
      set({ status: "anonymous", user: null });
      return;
    }
    try {
      const access = await refreshAccessToken();
      if (!access) {
        set({ status: "anonymous", user: null });
        return;
      }
      set({ status: "authenticated", user: await authApi.me() });
    } catch {
      // Lỗi mạng/server: không xóa token, tạm coi là khách, reload sẽ thử lại
      set({ status: "anonymous", user: null });
    }
  },

  async login(username, password) {
    const pair = await authApi.login(username, password);
    tokens.set(pair.access, pair.refresh);
    try {
      set({ status: "authenticated", user: await authApi.me() });
    } catch (error) {
      tokens.clear();
      throw error;
    }
  },

  async register(input) {
    await authApi.register(input);
    await get().login(input.username, input.password);
  },

  async logout() {
    const refresh = tokens.getRefresh();
    tokens.clear();
    set({ status: "anonymous", user: null });
    queryClient.clear(); // xóa cache dữ liệu gắn với người dùng cũ
    if (refresh) {
      try {
        await authApi.logout(refresh); // đưa refresh token vào blacklist
      } catch {
        /* không sao: token sẽ tự hết hạn */
      }
    }
  },

  setUser: (user) => set({ user }),
}));

// Refresh thất bại giữa chừng (bị blacklist, hết hạn 7 ngày...) -> về trạng thái khách
setSessionExpiredHandler(() => {
  useAuth.setState({ status: "anonymous", user: null });
  queryClient.clear();
});