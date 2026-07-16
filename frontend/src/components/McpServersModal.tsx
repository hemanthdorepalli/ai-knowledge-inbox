import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Plug, Plus, RefreshCw, Trash2, Wrench, X } from "lucide-react";
import {
  listMcpServers,
  addMcpServer,
  deleteMcpServer,
  toggleMcpServer,
  refreshMcpServer,
  ApiError,
} from "../api";
import type { McpServer } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

// Manage the user's connected MCP servers: add by URL, see discovered tools,
// enable/disable, refresh the tool list, or remove. Connected tools become
// available to the assistant during chat (via function calling).
export default function McpServersModal({ open, onClose }: Props) {
  const [servers, setServers] = useState<McpServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setServers(await listMcpServers());
    } catch {
      /* keep whatever was previously loaded */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setAddError(null);
    setAdding(true);
    try {
      await addMcpServer({ name, url, auth_token: authToken || undefined });
      setName("");
      setUrl("");
      setAuthToken("");
      await load();
    } catch (err) {
      setAddError(err instanceof ApiError ? err.message : "Could not connect to that server");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    setBusyId(id);
    try {
      await deleteMcpServer(id);
      setServers((prev) => prev.filter((s) => s.id !== id));
    } finally {
      setBusyId(null);
    }
  }

  async function handleToggle(server: McpServer) {
    setBusyId(server.id);
    try {
      const updated = await toggleMcpServer(server.id, !server.enabled);
      setServers((prev) => prev.map((s) => (s.id === server.id ? updated : s)));
    } finally {
      setBusyId(null);
    }
  }

  async function handleRefresh(id: string) {
    setBusyId(id);
    try {
      const updated = await refreshMcpServer(id);
      setServers((prev) => prev.map((s) => (s.id === id ? updated : s)));
    } catch {
      /* leave the stale tool list in place */
    } finally {
      setBusyId(null);
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
          <div className="absolute inset-0 bg-ink/30 backdrop-blur-sm" onClick={onClose} />

          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 8 }}
            transition={{ type: "spring", stiffness: 320, damping: 26 }}
            className="relative flex max-h-[85vh] w-full max-w-lg flex-col rounded-2xl bg-card p-6 shadow-lift"
          >
            <div className="mb-1 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
                <Plug size={18} className="text-accent" />
                MCP Servers
              </h2>
              <button
                onClick={onClose}
                className="rounded-lg p-1 text-muted transition-colors hover:bg-panel hover:text-ink"
              >
                <X size={18} />
              </button>
            </div>
            <p className="mb-4 text-xs text-faint">
              Connect a remote MCP server to give the assistant extra tools it can call while
              answering.
            </p>

            <div className="min-h-0 flex-1 overflow-y-auto">
              {loading ? (
                <div className="space-y-2">
                  {[0, 1].map((i) => (
                    <div key={i} className="h-16 animate-pulse rounded-xl bg-panel" />
                  ))}
                </div>
              ) : servers.length === 0 ? (
                <p className="rounded-xl bg-panel/60 px-3 py-4 text-center text-sm text-muted">
                  No servers connected yet.
                </p>
              ) : (
                <ul className="space-y-2">
                  {servers.map((s) => (
                    <li key={s.id} className="rounded-xl border border-line bg-panel/50 p-3">
                      <div className="flex items-start gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="truncate text-sm font-semibold text-ink">
                              {s.name}
                            </span>
                            {!s.enabled && (
                              <span className="shrink-0 rounded-full bg-faint/20 px-2 py-0.5 text-[10px] font-medium text-faint">
                                disabled
                              </span>
                            )}
                          </div>
                          <p className="truncate text-xs text-faint">{s.url}</p>
                          {s.tools.length > 0 && (
                            <div className="mt-1.5 flex flex-wrap gap-1">
                              {s.tools.map((t) => (
                                <span
                                  key={t.name}
                                  title={t.description}
                                  className="inline-flex items-center gap-1 rounded-full bg-accent-soft px-2 py-0.5 text-[10px] font-medium text-accent-hover"
                                >
                                  <Wrench size={10} />
                                  {t.name}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>

                        <div className="flex shrink-0 items-center gap-1">
                          <button
                            onClick={() => handleRefresh(s.id)}
                            disabled={busyId === s.id}
                            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-card hover:text-ink disabled:opacity-50"
                            title="Refresh tool list"
                          >
                            {busyId === s.id ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <RefreshCw size={14} />
                            )}
                          </button>
                          <button
                            onClick={() => handleToggle(s)}
                            disabled={busyId === s.id}
                            className={`rounded-full px-2 py-1 text-[10px] font-semibold transition-colors disabled:opacity-50 ${
                              s.enabled
                                ? "bg-accent text-white hover:bg-accent-hover"
                                : "bg-faint/20 text-muted hover:bg-faint/30"
                            }`}
                          >
                            {s.enabled ? "On" : "Off"}
                          </button>
                          <button
                            onClick={() => handleDelete(s.id)}
                            disabled={busyId === s.id}
                            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-card hover:text-accent-hover disabled:opacity-50"
                            title="Remove server"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <form onSubmit={handleAdd} className="mt-4 space-y-2 border-t border-line pt-4">
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Server name"
                  required
                  className="rounded-xl border border-line bg-panel/50 px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:bg-card focus:outline-none"
                />
                <input
                  type="text"
                  value={authToken}
                  onChange={(e) => setAuthToken(e.target.value)}
                  placeholder="Auth token (optional)"
                  className="rounded-xl border border-line bg-panel/50 px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:bg-card focus:outline-none"
                />
              </div>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://your-mcp-server.example.com/mcp"
                required
                className="w-full rounded-xl border border-line bg-panel/50 px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-accent/40 focus:bg-card focus:outline-none"
              />

              {addError && <p className="text-sm text-accent-hover">{addError}</p>}

              <button
                type="submit"
                disabled={adding}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-60"
              >
                {adding ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />}
                {adding ? "Connecting…" : "Connect server"}
              </button>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
