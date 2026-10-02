import type { ReactNode } from "react";
import { styles } from "./styles";

/** Bố cục chia đôi cho trang đăng nhập/đăng ký: mảng trang trí điện ảnh + form kính mờ */
export function AuthShell({ title, tagline, children }: { title: string; tagline: string; children: ReactNode }) {
  return (
    <div className="grid min-h-[70vh] overflow-hidden rounded-3xl border border-smoke bg-surface/40 backdrop-blur lg:grid-cols-[1.2fr_1fr]">
      <div className="relative hidden overflow-hidden lg:block" aria-hidden>
        <div className="absolute -left-24 -top-24 h-96 w-96 animate-kenburns rounded-full bg-brand/40 blur-3xl" />
        <div className="absolute -bottom-32 right-0 h-[28rem] w-[28rem] animate-kenburns rounded-full bg-rose-900/50 blur-3xl [animation-delay:-6s]" />
        <div className="absolute inset-0 bg-[repeating-linear-gradient(90deg,transparent_0,transparent_46px,rgba(0,0,0,0.5)_46px,rgba(0,0,0,0.5)_54px)] opacity-40" />
        <div className="absolute inset-y-0 left-6 flex flex-col justify-around">
          {Array.from({ length: 10 }, (_, i) => (
            <span key={i} className="h-3 w-4 rounded-sm bg-black/60" />
          ))}
        </div>
        <div className="relative flex h-full flex-col justify-end gap-4 p-14">
          <p className="font-display text-2xl font-bold tracking-wider text-brand drop-shadow-[0_0_12px_rgba(225,29,72,0.6)]">
            🎬 CINEMA
          </p>
          <p className="max-w-md font-display text-5xl font-bold uppercase leading-[1.15] tracking-wide">{tagline}</p>
          <p className="max-w-sm text-sm text-zinc-300">Đặt vé trong vài giây, chọn ghế theo thời gian thực.</p>
        </div>
      </div>
      <div className="flex items-center justify-center p-6 sm:p-12">
        <div className="stagger w-full max-w-sm space-y-6">
          <h1 className={styles.heading}>{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}
