import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "@/auth/store";
import { styles } from "./styles";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `relative py-1 text-sm font-medium transition after:absolute after:inset-x-0 after:-bottom-1 after:h-0.5 after:origin-left after:rounded-full after:bg-brand after:transition-transform after:duration-300 ${
    isActive ? "text-fg after:scale-x-100" : "text-muted hover:text-fg after:scale-x-0"
  }`;

export function Layout() {
  const status = useAuth((s) => s.status);
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/");
  }

  const close = () => setMenuOpen(false);
  const displayName = user ? user.first_name || user.username : "";

  const links =
    status === "authenticated" && user ? (
      <>
        <NavLink to="/bookings" className={navClass} onClick={close}>
          Vé của tôi
        </NavLink>
        {(user.role === "staff" || user.role === "admin") && (
          <NavLink to="/staff/checkin" className={navClass} onClick={close}>
            Soát vé
          </NavLink>
        )}
        {user.role === "admin" && (
          <NavLink to="/dashboard" className={navClass} onClick={close}>
            Báo cáo
          </NavLink>
        )}
      </>
    ) : null;

  const account =
    status === "authenticated" && user ? (
      <>
        <Link to="/account" onClick={close} className="group flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-brand to-rose-900 text-sm font-bold uppercase text-white ring-2 ring-brand/30 transition group-hover:ring-brand">
            {displayName.charAt(0)}
          </span>
          <span className="text-sm text-fg">{displayName}</span>
        </Link>
        <button type="button" onClick={handleLogout} className={styles.buttonGhost}>
          Đăng xuất
        </button>
      </>
    ) : status === "anonymous" ? (
      <>
        <Link to="/login" onClick={close} className="text-sm font-medium text-muted transition hover:text-fg">
          Đăng nhập
        </Link>
        <Link to="/register" onClick={close} className={styles.button}>
          Đăng ký
        </Link>
      </>
    ) : null;

  return (
    <div className="flex min-h-screen flex-col text-fg">
      <header className="sticky top-0 z-40 border-b border-white/5 bg-ink/70 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2 font-display text-2xl font-bold tracking-wider text-brand drop-shadow-[0_0_12px_rgba(225,29,72,0.55)]">
            <span aria-hidden>🎬</span> CINEMA
          </Link>
          <nav className="hidden flex-1 items-center gap-7 md:flex">{links}</nav>
          <div className="hidden items-center gap-4 md:flex">{account}</div>
          <button
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-smoke md:hidden"
            aria-label={menuOpen ? "Đóng menu" : "Mở menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span className="relative block h-3.5 w-5">
              <span className={`absolute left-0 top-0 h-0.5 w-5 rounded bg-fg transition ${menuOpen ? "top-1.5 rotate-45" : ""}`} />
              <span className={`absolute left-0 top-1.5 h-0.5 w-5 rounded bg-fg transition ${menuOpen ? "opacity-0" : ""}`} />
              <span className={`absolute left-0 top-3 h-0.5 w-5 rounded bg-fg transition ${menuOpen ? "top-1.5 -rotate-45" : ""}`} />
            </span>
          </button>
        </div>
      </header>

      {/* Drawer mobile */}
      <div
        className={`fixed inset-0 z-30 bg-black/60 backdrop-blur-sm transition-opacity md:hidden ${
          menuOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={close}
        aria-hidden
      />
      <aside
        className={`fixed right-0 top-16 z-30 flex h-[calc(100svh-4rem)] w-72 flex-col gap-6 border-l border-smoke bg-surface/95 p-6 backdrop-blur-xl transition-transform duration-300 ease-[var(--ease-cinema)] md:hidden ${
          menuOpen ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!menuOpen}
      >
        <nav className="flex flex-col gap-4">{links}</nav>
        <div className="mt-auto flex flex-col items-start gap-4 border-t border-smoke pt-6">{account}</div>
      </aside>

      <main key={location.pathname} className="mx-auto w-full max-w-7xl flex-1 animate-fade-up px-4 py-8 sm:px-6">
        <Outlet />
      </main>

      <footer className="mt-16 border-t border-white/5 bg-black/30">
        <div className="mx-auto flex max-w-7xl flex-wrap items-start justify-between gap-8 px-4 py-10 sm:px-6">
          <div className="space-y-3">
            <p className="font-display text-2xl font-bold tracking-wider text-brand">🎬 CINEMA</p>
            <p className="max-w-xs text-sm text-muted">
              Trải nghiệm điện ảnh đỉnh cao. Đặt vé nhanh, giữ ghế theo thời gian thực.
            </p>
          </div>
          <nav className="flex flex-col gap-2 text-sm">
            <p className={styles.eyebrow}>Khám phá</p>
            <Link to="/" className="text-muted transition hover:text-fg">Phim đang chiếu</Link>
            <Link to="/?status=coming_soon" className="text-muted transition hover:text-fg">Phim sắp chiếu</Link>
            <Link to="/bookings" className="text-muted transition hover:text-fg">Vé của tôi</Link>
          </nav>
        </div>
        <p className="border-t border-white/5 py-5 text-center text-xs text-dim">
          © {new Date().getFullYear()} Cinema. Mọi quyền được bảo lưu.
        </p>
      </footer>
    </div>
  );
}
