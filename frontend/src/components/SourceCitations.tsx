import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, FileText, Link2 } from "lucide-react";
import type { SourceSnippet } from "../types";

interface Props {
  sources: SourceSnippet[];
}

// Collapsible list of the retrieved chunks that grounded the answer. Collapsed
// by default so answers stay clean, but one click reveals exactly what the
// model saw, with a relevance score — the transparency that makes RAG useful.
export default function SourceCitations({ sources }: Props) {
  const [open, setOpen] = useState(false);
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-line pt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-ink"
      >
        <ChevronDown
          size={14}
          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
        {sources.length} source{sources.length === 1 ? "" : "s"}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-2">
              {sources.map((s, i) => (
                <motion.li
                  key={`${s.item_id}-${i}`}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="rounded-xl border border-line bg-panel/60 p-3"
                >
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-accent">
                      {s.source_url ? <Link2 size={13} /> : <FileText size={13} />}
                    </span>
                    <span className="truncate text-xs font-semibold text-ink">
                      [{i + 1}] {s.title ?? s.source_url ?? "Untitled"}
                    </span>
                    <span className="ml-auto shrink-0 rounded-full bg-accent-soft px-2 py-0.5 text-[10px] font-medium text-accent-hover">
                      {(s.score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  {s.source_url && (
                    <a
                      href={s.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mb-1 block truncate text-[11px] text-accent hover:underline"
                    >
                      {s.source_url}
                    </a>
                  )}
                  <p className="line-clamp-3 text-xs leading-relaxed text-muted">
                    {s.chunk_text}
                  </p>
                </motion.li>
              ))}
            </div>
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
