import { Wrench } from "lucide-react";
import type { ToolCallInfo } from "../types";

interface Props {
  toolCalls: ToolCallInfo[];
}

// Shows which MCP tools were actually called while answering, with the
// result on hover -- same transparency purpose as source citations, but for
// live tool calls instead of saved content.
export default function ToolCallChips({ toolCalls }: Props) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="mb-2 flex flex-wrap gap-1.5">
      {toolCalls.map((tc, i) => (
        <span
          key={`${tc.server_name}-${tc.tool_name}-${i}`}
          title={`${tc.result}`}
          className="inline-flex items-center gap-1.5 rounded-full border border-line bg-panel px-2.5 py-1 text-[11px] font-medium text-muted"
        >
          <Wrench size={11} className="text-accent" />
          {tc.tool_name}
          <span className="text-faint">· {tc.server_name}</span>
        </span>
      ))}
    </div>
  );
}
