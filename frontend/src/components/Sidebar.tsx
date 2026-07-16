import { AnimatePresence, motion } from "framer-motion";
import {
  FileText,
  Link2,
  LogOut,
  MessageSquare,
  PanelLeftClose,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import type { Conversation, Item, Usage } from "../types";

interface Props {
  // knowledge base
  items: Item[];
  loading: boolean;
  error: string | null;
  onAdd: () => void;
  // chat history
  conversations: Conversation[];
  currentConversationId: string | null;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  // chrome
  collapsed: boolean;
  onToggle: () => void;
  userEmail: string;
  onSignOut: () => void;
  usage: Usage | null;
}

export default function Sidebar({
  items,
  loading,
  error,
  onAdd,
  conversations,
  currentConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  collapsed,
  onToggle,
  userEmail,
  onSignOut,
  usage,
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
            onClick={onNewChat}
            className="flex w-full items-center gap-2 rounded-xl bg-accent px-3 py-2.5 text-sm font-semibold text-white shadow-lift transition-all hover:bg-accent-hover hover:brightness-105"
          >
            <Plus size={16} strokeWidth={2.5} />
            New chat
          </button>
        </div>

        <div className="mt-5 flex-1 space-y-6 overflow-y-auto px-3 pb-4">
          {/* Chat history */}
          <section>
            <div className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-white/40">
              Chats
            </div>
            {conversations.length === 0 && (
              <p className="px-1 text-xs leading-relaxed text-white/50">
                No conversations yet. Ask a question to start one.
              </p>
            )}
            <ul className="space-y-0.5">
              <AnimatePresence initial={false}>
                {conversations.map((c) => {
                  const active = c.id === currentConversationId;
                  return (
                    <motion.li
                      key={c.id}
                      layout
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      onClick={() => onSelectConversation(c.id)}
                      className={`group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 transition-colors ${
                        active ? "bg-white/10" : "hover:bg-white/5"
                      }`}
                    >
                      <MessageSquare
                        size={14}
                        className={active ? "text-accent" : "text-white/40"}
                      />
                      <span className="min-w-0 flex-1 truncate text-sm text-white/90">
                        {c.title || "New chat"}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteConversation(c.id);
                        }}
                        className="text-white/30 opacity-0 transition-all hover:text-white group-hover:opacity-100"
                        aria-label="Delete conversation"
                        title="Delete conversation"
                      >
                        <Trash2 size={13} />
                      </button>
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
          </section>

          {/* Knowledge base */}
          <section>
            <div className="mb-2 flex items-center justify-between px-1">
              <span className="text-xs font-semibold uppercase tracking-wide text-white/40">
                Knowledge · {items.length}
              </span>
              <button
                onClick={onAdd}
                className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium text-white/60 transition-colors hover:bg-white/10 hover:text-white"
              >
                <Plus size={13} /> Add
              </button>
            </div>

            {error && <p className="px-1 text-xs text-red-400">{error}</p>}
            {loading && !error && (
              <div className="space-y-2">
                {[0, 1].map((i) => (
                  <div key={i} className="h-12 animate-pulse rounded-xl bg-white/10" />
                ))}
              </div>
            )}
            {!loading && !error && items.length === 0 && (
              <p className="px-1 text-xs leading-relaxed text-white/50">
                Nothing saved yet. Add a note, link, or document.
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
                    className="group cursor-default rounded-xl border border-transparent px-3 py-2 transition-colors hover:border-white/10 hover:bg-white/5"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-accent">
                        {item.type === "url" ? <Link2 size={13} /> : <FileText size={13} />}
                      </span>
                      <span className="truncate text-sm font-medium text-white">
                        {item.title ??
                          (item.type === "url"
                            ? "Untitled link"
                            : item.type === "document"
                              ? "Untitled document"
                              : "Untitled note")}
                      </span>
                      <span className="ml-auto shrink-0 text-[10px] text-white/40">
                        {item.chunk_count}
                      </span>
                    </div>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          </section>
        </div>

        {usage && <UsageBar usage={usage} />}

        <div className="mt-auto flex items-center gap-2 border-t border-white/10 px-4 py-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold uppercase text-white">
            {userEmail.charAt(0)}
          </div>
          <span className="min-w-0 flex-1 truncate text-xs text-white/70" title={userEmail}>
            {userEmail}
          </span>
          <button
            onClick={onSignOut}
            className="rounded-lg p-1.5 text-white/50 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </motion.aside>
  );
}

function UsageBar({ usage }: { usage: Usage }) {
  const pct = usage.tokens_limit > 0 ? Math.min(100, (usage.tokens_used / usage.tokens_limit) * 100) : 0;
  const low = usage.tokens_remaining <= usage.tokens_limit * 0.1;

  return (
    <div className="px-4 pb-1 pt-2">
      <div className="mb-1.5 flex items-center justify-between text-[11px] text-white/50">
        <span>Tokens</span>
        <span className={low ? "font-medium text-accent" : ""}>
          {usage.tokens_used.toLocaleString()} / {usage.tokens_limit.toLocaleString()}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-all ${low ? "bg-accent" : "bg-white/40"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
