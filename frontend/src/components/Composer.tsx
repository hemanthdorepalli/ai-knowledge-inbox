import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp } from "lucide-react";

interface Props {
  onSend: (question: string) => void;
  disabled: boolean;
}

// Chat input pinned to the bottom. Auto-grows with content; Enter sends,
// Shift+Enter inserts a newline.
export default function Composer({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  function grow() {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }

  function send() {
    const q = value.trim();
    if (!q || disabled) return;
    onSend(q);
    setValue("");
    if (ref.current) ref.current.style.height = "auto";
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="pointer-events-none sticky bottom-0 bg-gradient-to-t from-app via-app to-transparent px-4 pb-5 pt-6">
      <div className="pointer-events-auto mx-auto w-full max-w-3xl">
        <div className="flex items-end gap-2 rounded-3xl border border-line bg-card p-2 pl-4 shadow-lift transition-shadow focus-within:border-accent/40">
          <textarea
            ref={ref}
            value={value}
            rows={1}
            disabled={disabled}
            onChange={(e) => {
              setValue(e.target.value);
              grow();
            }}
            onKeyDown={onKeyDown}
            placeholder="Ask anything about your saved content…"
            className="max-h-[200px] flex-1 resize-none bg-transparent py-2 text-[15px] leading-relaxed text-ink placeholder:text-faint focus:outline-none disabled:opacity-60"
          />
          <motion.button
            onClick={send}
            disabled={disabled || !value.trim()}
            whileTap={{ scale: 0.9 }}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-faint"
            aria-label="Send"
          >
            <ArrowUp size={18} strokeWidth={2.5} />
          </motion.button>
        </div>
        <p className="mt-2 text-center text-[11px] text-faint">
          Answers are generated from your saved content and cited.
        </p>
      </div>
    </div>
  );
}
