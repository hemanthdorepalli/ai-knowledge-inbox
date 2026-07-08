import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FileText, Link2, Loader2, X } from "lucide-react";
import { ingest, ApiError } from "../api";
import type { SourceType } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onAdded: () => void;
}

// Modal for adding a note or URL to the knowledge base. Animated backdrop +
// spring-in card. On success it refreshes the sidebar and closes itself.
export default function AddItemModal({ open, onClose, onAdded }: Props) {
  const [type, setType] = useState<SourceType>("note");
  const [content, setContent] = useState("");
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setContent("");
    setUrl("");
    setTitle("");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (type === "note") {
        await ingest({ type: "note", content, title: title || undefined });
      } else {
        await ingest({ type: "url", url, title: title || undefined });
      }
      reset();
      onAdded();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div
            className="absolute inset-0 bg-ink/30 backdrop-blur-sm"
            onClick={() => !submitting && onClose()}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", stiffness: 320, damping: 26 }}
            className="relative w-full max-w-lg rounded-2xl bg-card p-6 shadow-lift"
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">Add to knowledge base</h2>
              <button
                onClick={onClose}
                className="rounded-lg p-1 text-muted transition-colors hover:bg-panel hover:text-ink"
              >
                <X size={18} />
              </button>
            </div>

            <div className="mb-4 grid grid-cols-2 gap-2">
              {(
                [
                  { key: "note", label: "Note", icon: FileText },
                  { key: "url", label: "Link", icon: Link2 },
                ] as const
              ).map(({ key, label, icon: Icon }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setType(key)}
                  className={`flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                    type === key
                      ? "border-accent bg-accent-soft text-accent-hover"
                      : "border-line bg-card text-muted hover:border-accent/30"
                  }`}
                >
                  <Icon size={15} />
                  {label}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <AnimatePresence mode="wait">
                <motion.div
                  key={type}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.15 }}
                >
                  {type === "note" ? (
                    <textarea
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      placeholder="Paste or type a note…"
                      rows={5}
                      required
                      autoFocus
                      className="w-full resize-y rounded-xl border border-line bg-panel/50 px-3.5 py-2.5 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:bg-card focus:outline-none"
                    />
                  ) : (
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://example.com/article"
                      required
                      autoFocus
                      className="w-full rounded-xl border border-line bg-panel/50 px-3.5 py-2.5 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:bg-card focus:outline-none"
                    />
                  )}
                </motion.div>
              </AnimatePresence>

              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Title (optional)"
                className="w-full rounded-xl border border-line bg-panel/50 px-3.5 py-2.5 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:bg-card focus:outline-none"
              />

              {error && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-sm text-accent-hover"
                >
                  {error}
                </motion.p>
              )}

              <div className="flex justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-xl px-4 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-panel"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-60"
                >
                  {submitting && <Loader2 size={15} className="animate-spin" />}
                  {submitting ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
