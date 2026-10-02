export const styles = {
    button:
        "shimmer inline-flex items-center justify-center gap-2 rounded-[10px] bg-brand px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:bg-brand-hover hover:shadow-glow active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-brand disabled:hover:shadow-none",
    buttonGhost:
        "inline-flex items-center justify-center gap-2 rounded-[10px] border border-smoke bg-white/[0.02] px-4 py-2 text-sm text-fg transition duration-200 hover:border-zinc-500 hover:bg-white/[0.06] active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40",
    input:
        "w-full rounded-[10px] border border-smoke bg-field px-3.5 py-2.5 text-sm text-fg placeholder:text-dim transition focus:border-brand focus:shadow-glow-sm focus:outline-none aria-[invalid=true]:border-red-500/70",
    card: "rounded-2xl border border-smoke bg-surface/70 p-6 shadow-[0_20px_50px_-20px_rgba(0,0,0,0.8)] backdrop-blur-xl",
    error: "rounded-[10px] border border-red-500/30 bg-red-950/40 px-3.5 py-2.5 text-sm text-red-300",
    heading: "font-display text-3xl font-semibold uppercase tracking-wide text-fg sm:text-4xl",
    eyebrow: "text-xs font-semibold uppercase tracking-[0.2em] text-brand",
    tabList: "inline-flex gap-1 rounded-full border border-smoke bg-surface/80 p-1 backdrop-blur",
    tab: "rounded-full px-4 py-1.5 text-sm font-medium transition duration-300",
    tabActive: "bg-brand text-white shadow-glow-sm",
    tabIdle: "text-muted hover:text-fg",
} as const;
