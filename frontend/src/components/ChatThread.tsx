import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { FileText, Link2, Sparkles, Upload } from "lucide-react";
import type { ChatMessage, SourceType } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  hasItems: boolean;
  onSuggestion: (q: string) => void;
  onAddKnowledge: (type: SourceType) => void;
  userName: string;
}

const SUGGESTIONS = [
  "Summarize everything I've saved",
  "What are the key points?",
  "What did I save about this topic?",
];

export default function ChatThread({
  messages,
  hasItems,
  onSuggestion,
  onAddKnowledge,
  userName,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Keep the latest message in view as the conversation grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <EmptyState
        hasItems={hasItems}
        onSuggestion={onSuggestion}
        onAddKnowledge={onAddKnowledge}
        userName={userName}
      />
    );
  }

  const lastAssistantId = [...messages].reverse().find((m) => m.role === "assistant")?.id;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-8">
      <AnimatePresence initial={false}>
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} animate={m.id === lastAssistantId} />
        ))}
      </AnimatePresence>
      <div ref={bottomRef} />
    </div>
  );
}

const PILLS: { icon: typeof FileText; label: string; type: SourceType }[] = [
  { icon: FileText, label: "Notes", type: "note" },
  { icon: Link2, label: "Links", type: "url" },
  { icon: Upload, label: "Documents", type: "document" },
];

function EmptyState({
  hasItems,
  onSuggestion,
  onAddKnowledge,
  userName,
}: {
  hasItems: boolean;
  onSuggestion: (q: string) => void;
  onAddKnowledge: (type: SourceType) => void;
  userName: string;
}) {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-white shadow-lift"
      >
        <Sparkles size={26} />
      </motion.div>

      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.5 }}
        className="mb-1 text-xs font-semibold uppercase tracking-widest text-accent"
      >
        {greeting}, {userName}
      </motion.p>
      <motion.h2
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="font-serif text-4xl font-medium tracking-tight text-ink"
      >
        Your own AI knowledge assistant
      </motion.h2>
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18, duration: 0.5 }}
        className="mt-3 max-w-lg text-[15px] leading-relaxed text-muted"
      >
        Add your related notes, links, and documents — I'll summarize them, answer
        questions with cited sources, and act like your own private LLM trained on
        your content.
      </motion.p>

      {/* Add-knowledge shortcuts */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.26, duration: 0.5 }}
        className="mt-6 flex flex-wrap justify-center gap-2"
      >
        {PILLS.map(({ icon: Icon, label, type }) => (
          <button
            key={label}
            onClick={() => onAddKnowledge(type)}
            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-card px-3.5 py-1.5 text-xs font-medium text-muted transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:text-ink hover:shadow-soft"
          >
            <Icon size={13} className="text-accent" />
            Add {label}
          </button>
        ))}
      </motion.div>

      {hasItems ? (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.34, duration: 0.5 }}
          className="mt-6 flex flex-wrap justify-center gap-2"
        >
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestion(s)}
              className="rounded-full border border-line bg-card px-4 py-2 text-sm text-ink shadow-soft transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-lift"
            >
              {s}
            </button>
          ))}
        </motion.div>
      ) : (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.34, duration: 0.5 }}
          className="mt-6 text-sm text-faint"
        >
          Use the <span className="font-semibold text-accent">+</span> button below to add
          your first note, link, or document.
        </motion.p>
      )}
    </div>
  );
}
