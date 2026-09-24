from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from models import MemoryResponse


class StudioInput(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)


class PrepareInput(StudioInput):
    agent_id: str = Field(min_length=1, max_length=80)
    memory_ids: list[str] = Field(default_factory=list, max_length=6)
    task_digest: str = Field(pattern=r'^[a-f0-9]{64}$')

    @field_validator('memory_ids')
    @classmethod
    def unique_ids(cls, values):
        if len(values) != len(set(values)) or any(len(v) > 80 for v in values):
            raise ValueError('Choose up to six distinct memories.')
        return values


class ContextInput(StudioInput):
    memory_id: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=20000)


class ExecuteInput(StudioInput):
    consent_token: str = Field(min_length=32, max_length=100)
    approved: Literal[True]
    task: str = Field(min_length=1, max_length=4000)
    contexts: list[ContextInput] = Field(default_factory=list, max_length=6)

    @field_validator('task')
    @classmethod
    def nonempty_task(cls, value):
        if not value.strip():
            raise ValueError('A task is required.')
        return value

    @field_validator('contexts')
    @classmethod
    def bounded_context(cls, values):
        ids = [v.memory_id for v in values]
        if len(ids) != len(set(ids)) or sum(len(v.content) for v in values) > 30000:
            raise ValueError('Choose unique memories with at most 30,000 context characters.')
        return values


class PreparedResponse(BaseModel):
    consent_token: str
    expires_at: str
    provider: str
    model: str
    memories: list[MemoryResponse]


class RunReceipt(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str
    agent_id: str
    agent_name: str
    model: str
    provider: str
    memory_ids: list[str]
    memory_count: int
    status: str
    created_at: str
    finished_at: str | None = None
    duration_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error_code: str | None = None


class StudioConfig(BaseModel):
    configured: bool
    provider: str
    model: str
    model_label: str
    max_memories: int = 6
    max_context_characters: int = 30000
    timeout_seconds: int
    hourly_limit: int