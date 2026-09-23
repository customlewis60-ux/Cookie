import base64
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from core import CATEGORIES

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Envelope(StrictModel):
    algorithm: Literal['AES-GCM'] = 'AES-GCM'
    iv: str = Field(min_length=16, max_length=16)
    ciphertext: str = Field(min_length=24, max_length=300000)
    @field_validator('iv', 'ciphertext')
    @classmethod
    def valid_base64(cls, value):
        try: base64.b64decode(value, validate=True)
        except Exception: raise ValueError('Invalid encrypted envelope')
        return value

class VaultInput(StrictModel):
    salt: str = Field(min_length=24, max_length=24)
    verifier: Envelope
    iterations: Literal[310000] = 310000
    @field_validator('salt')
    @classmethod
    def valid_salt(cls, value):
        if len(base64.b64decode(value, validate=True)) != 16: raise ValueError('Salt must contain 16 bytes')
        return value

class DemoInput(StrictModel):
    credential: str = Field(pattern=r'^[a-f0-9]{64}$')

class MemoryInput(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    category: str
    privacy: Literal['private', 'shareable'] = 'private'
    encrypted_payload: Envelope
    @field_validator('title')
    @classmethod
    def clean_title(cls, value):
        if not value.strip(): raise ValueError('Title cannot be empty')
        return value.strip()
    @field_validator('category')
    @classmethod
    def valid_category(cls, value):
        if value not in CATEGORIES: raise ValueError('Unknown category')
        return value

class AgentInput(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    developer: str = Field(default='Independent developer', min_length=1, max_length=80)
    kind: Literal['personal', 'trading', 'coding', 'research', 'custom'] = 'custom'

class AgentUpdate(StrictModel):
    status: Literal['connected', 'disconnected']

class PermissionInput(StrictModel):
    agent_id: str
    target_type: Literal['memory', 'category'] = 'memory'
    target: str

class KeyInput(StrictModel):
    name: str = Field(min_length=1, max_length=80)
    agent_id: str
    can_write: bool = False

class ImportInput(StrictModel):
    memories: list[MemoryInput] = Field(min_length=1, max_length=1000)

class MemoryResponse(MemoryInput):
    model_config = ConfigDict(extra='ignore')
    id: str
    user_id: str
    created_at: str
    updated_at: str
    last_accessed: Optional[str] = None