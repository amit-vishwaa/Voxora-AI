"""Request bodies. Validation lives here so routers stay short."""
from typing import Literal, Optional

from pydantic import BaseModel, Field

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Lang = Literal["en", "hi", "gu"]


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    industry: str = Field(min_length=2, max_length=40)
    plan: str = "trial"
    contact_email: str = Field(default="", max_length=120)
    admin_name: str = Field(min_length=2, max_length=80)
    admin_email: str = Field(pattern=EMAIL, max_length=120)
    admin_password: str = Field(min_length=8, max_length=200)


class CompanyPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    industry: Optional[str] = None
    plan: Optional[str] = None
    status: Optional[Literal["active", "suspended"]] = None
    contact_email: Optional[str] = Field(default=None, max_length=120)


class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(pattern=EMAIL, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["client_admin", "client_user"] = "client_user"


class UserPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=200)


class AgentIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    pack_key: str
    language: Lang = "en"
    voice: str = "anushka"
    greeting: str = Field(default="", max_length=400)
    instructions: str = Field(default="", max_length=1500)
    active: bool = True


class AgentPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=40)
    pack_key: Optional[str] = None
    language: Optional[Lang] = None
    voice: Optional[str] = None
    greeting: Optional[str] = Field(default=None, max_length=400)
    instructions: Optional[str] = Field(default=None, max_length=1500)
    active: Optional[bool] = None


class KnowledgeIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=2, max_length=4000)
    agent_id: Optional[int] = None


class RecordPatch(BaseModel):
    status: Literal["new", "contacted", "won", "closed"]


class TTSIn(BaseModel):
    text: str = Field(min_length=1, max_length=2400)
    language: Lang = "en"
    voice: str = "anushka"
