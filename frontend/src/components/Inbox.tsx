import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { PanelLeftOpen } from "lucide-react";
import {
  fetchItems,
  query,
  listConversations,
  getMessages,
  deleteConversation as apiDeleteConversation,
  getUsage,
  ApiError,
} from "../api";
import type { ChatMessage, Conversation, Item, SourceType, Usage } from "../types";
import Sidebar from "./Sidebar";
import AddItemModal from "./AddItemModal";
import ChatThread from "./ChatThread";
import Composer from "./Composer";

const uid = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);

interface Props {
  userName: string;
  userEmail: string;
  onSignOut: () => void;
}

export default function Inbox({ userName, userEmail, onSignOut }: Props) {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [collapsed, setCollapsed] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalType, setModalType] = useState<SourceType>("note");

  const openAdd = useCallback((type: SourceType = "note") => {
    setModalType(type);
    setModalOpen(true);
  }, []);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [asking, setAsking] = useState(false);
  const [usage, setUsage] = useState<Usage | null>(null);

  const loadUsage = useCallback(async () => {
    try {
      setUsage(await getUsage());
    } catch {
      /* non-fatal: usage bar just stays hidden */
    }
  }, []);

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

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
    } catch {
      /* non-fatal: the chat still works without the history list */
    }
  }, []);

  useEffect(() => {
    loadItems();
    loadConversations();
    loadUsage();
  }, [loadItems, loadConversations, loadUsage]);

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
        const res = await query(question, currentConversationId);
        setCurrentConversationId(res.conversation_id);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: res.answer, sources: res.sources, pending: false }
              : m
          )
        );
        loadConversations();
        loadUsage();
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
    [asking, currentConversationId, loadConversations, loadUsage]
  );

  const newChat = useCallback(() => {
    setCurrentConversationId(null);
    setMessages([]);
  }, []);

  const selectConversation = useCallback(
    async (id: string) => {
      if (id === currentConversationId) return;
      setCurrentConversationId(id);
      try {
        const history = await getMessages(id);
        setMessages(
          history.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            sources: m.sources ?? undefined,
          }))
        );
      } catch {
        setMessages([]);
      }
    },
    [currentConversationId]
  );

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      try {
        await apiDeleteConversation(id);
      } catch {
        /* ignore */
      }
      if (id === currentConversationId) newChat();
      loadConversations();
    },
    [currentConversationId, newChat, loadConversations]
  );

  return (
    <div className="flex h-screen overflow-hidden bg-app">
      <Sidebar
        items={items}
        loading={loading}
        error={loadError}
        onAdd={() => openAdd()}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewChat={newChat}
        onSelectConversation={selectConversation}
        onDeleteConversation={handleDeleteConversation}
        collapsed={collapsed}
        onToggle={() => setCollapsed(true)}
        userEmail={userEmail}
        onSignOut={onSignOut}
        usage={usage}
      />

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
          <ChatThread
            messages={messages}
            hasItems={items.length > 0}
            onSuggestion={handleAsk}
            onAddKnowledge={openAdd}
            userName={userName}
          />
        </div>
        <Composer onSend={handleAsk} disabled={asking} onAddKnowledge={() => openAdd()} />
      </main>

      <AddItemModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onAdded={() => {
          loadItems();
          loadUsage();
        }}
        initialType={modalType}
      />
    </div>
  );
}
