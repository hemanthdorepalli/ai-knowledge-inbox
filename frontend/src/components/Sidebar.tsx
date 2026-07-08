import { AnimatePresence, motion } from "framer-motion";
import { FileText, Link2, Plus, PanelLeftClose, Sparkles } from "lucide-react";
import type { Item } from "../types";

interface Props {
  items: Item[];
  loading: boolean;
  error: string | null;
  collapsed: boolean;
  onToggle: () => void;
  onAdd: () => void;
}

export default function Sidebar({
  items,
  loading,
  error,
  collapsed,
  onToggle,
  onAdd,
}: Props) {
  return (
    <motion.aside
      animate={{ width: collapsed ? 0 : 300 }}
      transition={{ type: "spring", stiffness: 300, damping: 34 }}
      className="relative z-10 shrink-0 overflow-hidden bg-sidebar text-white"
    >
      <div className="flex h-full w-[300px] flex-col">
        <div className="flex items-center justify-between px-4 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-white">
              <Sparkles size={15} />
            </div>
            <span className="text-sm font-semibold text-white">Knowledge Inbox</span>
          </div>
          <button
            onClick={onToggle}
            className="rounded-lg p-1.5 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose size={17} />
          </button>
        </div>

        <div className="px-3">
          <button
            onClick={onAdd}
            className="flex w-full items-center gap-2 rounded-xl bg-accent px-3 py-2.5 text-sm font-semibold text-white shadow-lift transition-all hover:bg-accent-hover hover:brightness-105"
          >
            <Plus size={16} strokeWidth={2.5} />
            Add note or link
          </button>
        </div>

        <div className="mt-5 flex items-center justify-between px-4">
          <span className="text-xs font-semibold uppercase tracking-wide text-white/40">
            Saved
          </span>
          <span className="text-xs text-white/40">{items.length}</span>
        </div>

        <div className="mt-2 flex-1 overflow-y-auto px-3 pb-4">
          {error && <p className="px-1 text-xs text-red-400">{error}</p>}
          {loading && !error && (
            <div className="space-y-2">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-14 animate-pulse rounded-xl bg-white/10"
                  style={{ animationDelay: `${i * 120}ms` }}
                />
              ))}
            </div>
          )}
          {!loading && !error && items.length === 0 && (
            <p className="px-1 pt-2 text-xs leading-relaxed text-white/50">
              Nothing saved yet. Add a note or link to build your knowledge base.
            </p>
          )}

          <ul className="space-y-1.5">
            <AnimatePresence initial={false}>
              {items.map((item) => (
                <motion.li
                  key={item.id}
                  layout
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="group cursor-default rounded-xl border border-transparent px-3 py-2.5 transition-colors hover:border-white/10 hover:bg-white/5"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-accent">
                      {item.type === "url" ? <Link2 size={13} /> : <FileText size={13} />}
                    </span>
                    <span className="truncate text-sm font-medium text-white">
                      {item.title ?? (item.type === "url" ? "Untitled link" : "Untitled note")}
                    </span>
                    <span className="ml-auto shrink-0 text-[10px] text-white/40">
                      {item.chunk_count}
                    </span>
                  </div>
                  <p className="mt-0.5 line-clamp-2 pl-5 text-xs leading-snug text-white/50">
                    {item.snippet}
                  </p>
                </motion.li>
              ))}
            </AnimatePresence>
          </ul>
        </div>
      </div>
    </motion.aside>
  );
}
