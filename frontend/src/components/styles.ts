export const styles = {
    button:
        "inline-flex items-center justify-center rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-50",
    buttonGhost:
        "inline-flex items-center justify-center rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 transition hover:bg-slate-800 disabled:opacity-50",
    input:
        "w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-red-500 focus:outline-none",
    card: "rounded-xl border border-slate-800 bg-slate-900 p-6",
    error: "rounded-md border border-red-900 bg-red-950 px-3 py-2 text-sm text-red-300",
} as const;