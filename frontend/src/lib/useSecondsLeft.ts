import { useEffect, useState } from "react";

/** Số giây còn lại đến mốc `deadlineMs` (epoch ms). null = không đếm. */
export function useSecondsLeft(deadlineMs: number | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (deadlineMs === null) return;
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, [deadlineMs]);

  if (deadlineMs === null) return 0;
  return Math.max(0, Math.ceil((deadlineMs - now) / 1000));
}