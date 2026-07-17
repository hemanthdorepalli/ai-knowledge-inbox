from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class IngestRequest(BaseModel):
    type: Literal["note", "url"]
    content: str | None = Field(default=None, description="Required when type='note'")
    url: str | None = Field(default=None, description="Required when type='url'")
    title: str | None = None

    @model_validator(mode="after")
    def check_required_fields(self) -> "IngestRequest":
        if self.type == "note":
            if not self.content or not self.content.strip():
                raise ValueError("content is required and cannot be empty when type='note'")
        if self.type == "url":
            if not self.url or not self.url.strip():
                raise ValueError("url is required and cannot be empty when type='url'")
            if not (self.url.startswith("http://") or self.url.startswith("https://")):
                raise ValueError("url must start with http:// or https://")
        return self


class IngestResponse(BaseModel):
    id: str
    type: Literal["note", "url", "document"]
    title: str | None
    source_url: str | None
    created_at: datetime
    chunk_count: int


class ItemSummary(BaseModel):
    id: str
    type: Literal["note", "url", "document"]
    title: str | None
    source_url: str | None
    snippet: str
    created_at: datetime
    chunk_count: int


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    # Continue an existing chat, or omit/null to start a new one.
    conversation_id: str | None = None

    @model_validator(mode="after")
    def check_question(self) -> "QueryRequest":
        if not self.question.strip():
            raise ValueError("question cannot be empty")
        return self


class SourceSnippet(BaseModel):
    item_id: str
    title: str | None
    source_url: str | None
    chunk_text: str
    score: float


class ToolCallInfo(BaseModel):
    server_name: str
    tool_name: str
    arguments: dict
    result: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceSnippet]
    conversation_id: str
    tool_calls: list[ToolCallInfo] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: str
    title: str | None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    sources: list[SourceSnippet] | None = None
    tool_calls: list[ToolCallInfo] | None = None
    created_at: datetime


class UsageResponse(BaseModel):
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    resets_at: datetime


class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=1)
    auth_token: str | None = None

    @model_validator(mode="after")
    def check_url(self) -> "McpServerCreate":
        if not (self.url.startswith("http://") or self.url.startswith("https://")):
            raise ValueError("url must start with http:// or https://")
        return self


class McpToolInfo(BaseModel):
    name: str
    description: str


class McpServerSummary(BaseModel):
    id: str
    name: str
    url: str
    enabled: bool
    tools: list[McpToolInfo]
    created_at: datetime
