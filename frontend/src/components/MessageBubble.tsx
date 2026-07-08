import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import type { ChatMessage } from "../types";
import { useTypewriter } from "../hooks/useTypewriter";
import ThinkingDots from "./ThinkingDots";
import SourceCitations from "./SourceCitations";

interface Props {
  message: ChatMessage;
  /** Only the latest assistant answer gets the typewriter reveal. */
  animate: boolean;
}

export default function MessageBubble({ message, animate }: Props) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-white shadow-soft">
          <Sparkles size={16} />
        </div>
      )}

      <div className={`min-w-0 max-w-[78%] ${isUser ? "order-first" : ""}`}>
        {isUser ? (
          <div className="rounded-2xl rounded-tr-md bg-user px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-soft">
            {message.content}
          </div>
        ) : (
          <div className="rounded-2xl rounded-tl-md bg-card px-4 py-3 shadow-soft ring-1 ring-line">
            {message.pending ? (
              <ThinkingDots />
            ) : (
              <AssistantContent message={message} animate={animate} />
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function AssistantContent({ message, animate }: Props) {
  const text = useTypewriter(message.content, animate);

  return (
    <>
      <div
        className={`prose-answer whitespace-pre-wrap text-[15px] leading-relaxed ${
          message.error ? "text-accent-hover" : "text-ink"
        }`}
      >
        {text}
        {animate && text.length < message.content.length && (
          <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-pulse bg-accent" />
        )}
      </div>
      {message.sources && <SourceCitations sources={message.sources} />}
    </>
  );
}
