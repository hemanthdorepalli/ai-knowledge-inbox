from google.genai import errors, types

from app import repository
from app.config import settings
from app.errors import LlmProviderError
from app.logging_config import get_logger
from app.schemas import SourceSnippet, ToolCallInfo
from app.services import mcp_tools, usage
from app.services.embeddings import embed_query
from app.services.gemini_client import client

logger = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using the provided context "
    "snippets from the user's saved notes and pages, and any connected tools. "
    "Prefer the saved context when it's relevant. If neither the context nor a tool "
    "can answer the question, say so clearly instead of guessing. Keep answers "
    "concise and reference which source number(s) you used, if any. Never mention "
    "internal function/tool names in your answer -- just state the result naturally."
)


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
    tools, name_map = mcp_tools.build_gemini_tools(user_id=user_id)

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

    contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]
    tool_calls: list[ToolCallInfo] = []
    answer = ""

    for round_num in range(settings.mcp_max_tool_rounds):
        try:
            response = client.models.generate_content(
                model=settings.chat_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                    tools=tools,
                ),
            )
        except errors.APIError as exc:
            usage.record_usage(user_id=user_id, tokens=total_tokens)
            logger.error("chat_completion_failed error=%s", exc)
            raise LlmProviderError(f"Answer generation failed: {exc}") from exc

        if response.usage_metadata and response.usage_metadata.total_token_count:
            total_tokens += response.usage_metadata.total_token_count
        else:
            total_tokens += usage.estimate_tokens(response.text or "")

        model_content = response.candidates[0].content
        function_calls = [p.function_call for p in model_content.parts if p.function_call]

        if not function_calls:
            answer = response.text or ""
            break

        contents.append(model_content)
        response_parts = []
        for fc in function_calls:
            call_info = mcp_tools.execute_tool_call(function_call=fc, name_map=name_map)
            tool_calls.append(call_info)
            response_parts.append(
                types.Part.from_function_response(name=fc.name, response={"result": call_info.result})
            )
        contents.append(types.Content(role="user", parts=response_parts))
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
