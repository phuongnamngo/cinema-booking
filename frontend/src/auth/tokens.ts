export const REFRESH_KEY = "cinema.refresh";

// Access token chỉ sống trong bộ nhớ: reload là mất, sẽ được lấy lại bằng refresh token
let accessToken: string | null = null;

function readRefresh(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export const tokens = {
  getAccess: () => accessToken,
  getRefresh: readRefresh,
  set(access: string, refresh: string) {
    accessToken = access;
    try {
      localStorage.setItem(REFRESH_KEY, refresh);
    } catch {
      /* storage bị chặn: chỉ mất khả năng giữ phiên khi reload */
    }
  },
  clear() {
    accessToken = null;
    try {
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* bỏ qua */
    }
  },
};