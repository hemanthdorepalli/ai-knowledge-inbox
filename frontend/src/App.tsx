import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { PanelLeftOpen } from "lucide-react";
import { fetchItems, query, ApiError } from "./api";
import type { ChatMessage, Item } from "./types";
import Sidebar from "./components/Sidebar";
import AddItemModal from "./components/AddItemModal";
import ChatThread from "./components/ChatThread";
import Composer from "./components/Composer";

const uid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

export default function App() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [collapsed, setCollapsed] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [asking, setAsking] = useState(false);

  const loadItems = useCallback(async () => {
    setLoadError(null);
    try {
      setItems(await fetchItems());
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Failed to load items");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const handleAsk = useCallback(
    async (question: string) => {
      if (asking) return;
      const assistantId = uid();
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "user", content: question },
        { id: assistantId, role: "assistant", content: "", pending: true },
      ]);
      setAsking(true);

      try {
        const res = await query(question);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: res.answer, sources: res.sources, pending: false }
              : m
          )
        );
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: message, pending: false, error: true } : m
          )
        );
      } finally {
        setAsking(false);
      }
    },
    [asking]
  );

  return (
    <div className="flex h-screen overflow-hidden bg-app">
      <Sidebar
        items={items}
        loading={loading}
        error={loadError}
        collapsed={collapsed}
        onToggle={() => setCollapsed(true)}
        onAdd={() => setModalOpen(true)}
      />

      {/* Floating button to reopen the sidebar when collapsed */}
      <AnimatePresence>
        {collapsed && (
          <motion.button
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -8 }}
            onClick={() => setCollapsed(false)}
            className="absolute left-3 top-3.5 z-20 rounded-lg border border-line bg-card p-2 text-muted shadow-soft transition-colors hover:text-ink"
            aria-label="Open sidebar"
          >
            <PanelLeftOpen size={17} />
          </motion.button>
        )}
      </AnimatePresence>

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ChatThread messages={messages} hasItems={items.length > 0} onSuggestion={handleAsk} />
        </div>
        <Composer onSend={handleAsk} disabled={asking} />
      </main>

      <AddItemModal open={modalOpen} onClose={() => setModalOpen(false)} onAdded={loadItems} />
    </div>
  );
}
