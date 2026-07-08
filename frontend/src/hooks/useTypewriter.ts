import { useEffect, useState } from "react";

// Reveals `text` progressively for a "streaming" feel, since the backend
// returns the whole answer at once. Uses setInterval (not requestAnimationFrame)
// so it keeps advancing and always converges to the full text even if the tab
// is backgrounded or the renderer isn't painting. Respects reduced-motion.
export function useTypewriter(text: string, enabled: boolean, charsPerTick = 3, tickMs = 16) {
  const [shown, setShown] = useState(enabled ? "" : text);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!enabled || reduce || !text) {
      setShown(text);
      return;
    }

    let i = 0;
    setShown("");
    const id = setInterval(() => {
      i = Math.min(text.length, i + charsPerTick);
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, tickMs);

    return () => clearInterval(id);
  }, [text, enabled, charsPerTick, tickMs]);

  return shown;
}
