import { Link, Outlet, useNavigate } from "react-router";
import { useAuth } from "@/auth/store";
import { styles } from "./styles";

export function Layout() {
  const status = useAuth((s) => s.status);
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold text-red-500">
            🎬 Cinema
          </Link>
          <nav className="flex items-center gap-3 text-sm">
            {status === "authenticated" && user ? (
              <>
                <Link to="/bookings" className="text-slate-300 hover:text-white">
                  Vé của tôi
                </Link>
                {(user.role === "staff" || user.role === "admin") && (
                  <Link to="/staff/checkin" className="text-slate-300 hover:text-white">
                    Soát vé
                  </Link>
                )}
                {user.role === "admin" && (
                  <Link to="/dashboard" className="text-slate-300 hover:text-white">
                    Báo cáo
                  </Link>
                )}
                <Link to="/account" className="text-slate-300 hover:text-white">
                  {user.first_name || user.username}
                </Link>
                <button type="button" onClick={handleLogout} className={styles.buttonGhost}>
                  Đăng xuất
                </button>
              </>
            ) : status === "anonymous" ? (
              <>
                <Link to="/login" className="text-slate-300 hover:text-white">
                  Đăng nhập
                </Link>
                <Link to="/register" className={styles.button}>
                  Đăng ký
                </Link>
              </>
            ) : null}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}