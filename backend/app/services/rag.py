"""Retrieval + answering.

Embeddings come from Gemini; the chat model is Groq (OpenAI-compatible API).
Splitting providers keeps each doing what it's good at -- Groq has no embedding
models, and Gemini's chat free tier is far too small (~20 requests/day).
"""

from openai import APIError

from app import repository
from app.config import settings
from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.schemas import SourceSnippet, ToolCallInfo
from app.services import mcp_tools, usage
from app.services.embeddings import embed_query
from app.services.groq_client import client

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using the provided context "
    "snippets from the user's saved notes and pages, and any connected tools. "
    "Prefer the saved context when it's relevant. If neither the context nor a tool "
    "can answer the question, say so clearly instead of guessing. Keep answers "
    "concise and reference which source number(s) you used, if any. Never mention "
    "internal function/tool names in your answer -- just state the result naturally. "
    "When a tool returns a result, that result is authoritative: report its exact "
    "values verbatim and never substitute your own, even for values that look "
    "random or that you think you could generate yourself."
)


def _is_tool_use_failure(exc: APIError) -> bool:
    """True when the provider rejected the model's own malformed tool call."""
    return "tool_use_failed" in str(exc)


def answer_question(
    question: str, *, user_id: str
) -> tuple[str, list[SourceSnippet], list[ToolCallInfo]]:
    # A query costs at least the embedding of the question; the chat call's
    # exact cost isn't known until it returns, so we just require some
    # headroom before starting and record the precise total afterward.
    usage.check_quota(user_id=user_id, needed_tokens=usage.estimate_tokens(question))

    query_embedding = embed_query(question)
    total_tokens = usage.estimate_tokens(question)

    matches = repository.search_chunks(
        user_id=user_id, query_embedding=query_embedding, top_k=settings.top_k
    )
    tools, name_map = mcp_tools.build_chat_tools(user_id=user_id)

    if not matches and not tools:
        usage.record_usage(user_id=user_id, tokens=total_tokens)
        return (
            "I don't have any saved content or connected tools yet, so I can't answer that. "
            "Add a note/URL or connect an MCP server first.",
            [],
            [],
        )

    sources = [
        SourceSnippet(
            item_id=str(m["item_id"]),
            title=m["title"],
            source_url=m["source_url"],
            chunk_text=m["chunk_text"],
            score=round(float(m["similarity"]), 4),
        )
        for m in matches
    ]

    context_block = (
        "\n\n---\n\n".join(
            f"[Source {i + 1}] {s.title or s.source_url or 'Untitled'}\n{s.chunk_text}"
            for i, s in enumerate(sources)
        )
        if sources
        else "(no saved content matched this question)"
    )

    user_prompt = (
        f"Context snippets:\n\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer using the context above and any tools available to you, and mention "
        "which source number(s) you used, if any."
    )

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    tool_calls: list[ToolCallInfo] = []
    answer = ""

    for _ in range(settings.mcp_max_tool_rounds):
        try:
            response = client.chat.completions.create(
                model=settings.chat_model,
                messages=messages,
                temperature=0.2,
                **({"tools": tools} if tools else {}),
            )
        except APIError as exc:
            # Llama models occasionally emit a malformed tool call, which the
            # provider rejects with `tool_use_failed`. That's a formatting slip,
            # not a real failure -- retry once without tools so the user still
            # gets an answer from their saved content instead of a 502.
            if tools and _is_tool_use_failure(exc):
                logger.warning("tool_use_failed_retrying_without_tools error=%s", exc)
                tools = None
                continue
            usage.record_usage(user_id=user_id, tokens=total_tokens)
            logger.error("chat_completion_failed error=%s", exc)
            raise LlmProviderError(f"Answer generation failed: {exc}") from exc

        if response.usage and response.usage.total_tokens:
            total_tokens += response.usage.total_tokens

        message = response.choices[0].message

        if not message.tool_calls:
            answer = message.content or ""
            break

        # Echo the assistant's tool-call turn back, then one "tool" message per
        # call -- the shape the OpenAI chat API expects.
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in message.tool_calls
                ],
            }
        )
        for tc in message.tool_calls:
            call_info = mcp_tools.execute_tool_call(
                name=tc.function.name, raw_arguments=tc.function.arguments, name_map=name_map
            )
            tool_calls.append(call_info)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": call_info.result}
            )
    else:
        answer = (
            answer
            or "I made several tool calls but couldn't reach a final answer. "
            "Try rephrasing your question."
        )

    usage.record_usage(user_id=user_id, tokens=total_tokens)
    logger.info(
        "query_answered question=%r sources=%d tool_calls=%d tokens=%d",
        question, len(sources), len(tool_calls), total_tokens,
    )
    return answer, sources, tool_calls
