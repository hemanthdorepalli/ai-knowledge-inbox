import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import type { ChatMessage } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  hasItems: boolean;
  onSuggestion: (q: string) => void;
}

const SUGGESTIONS = [
  "Summarize everything I've saved",
  "What are the key points?",
  "What did I save about this topic?",
];

export default function ChatThread({ messages, hasItems, onSuggestion }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Keep the latest message in view as the conversation grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (messages.length === 0) {
    return <EmptyState hasItems={hasItems} onSuggestion={onSuggestion} />;
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

function EmptyState({
  hasItems,
  onSuggestion,
}: {
  hasItems: boolean;
  onSuggestion: (q: string) => void;
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

      <motion.h2
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
        className="font-serif text-4xl font-medium tracking-tight text-ink"
      >
        {greeting}
      </motion.h2>
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18, duration: 0.5 }}
        className="mt-2 max-w-md text-[15px] text-muted"
      >
        {hasItems
          ? "Ask a question and I'll answer from your saved notes and links."
          : "Save a note or link from the sidebar, then ask me anything about it."}
      </motion.p>

      {hasItems && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28, duration: 0.5 }}
          className="mt-8 flex flex-wrap justify-center gap-2"
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
      )}
    </div>
  );
}
