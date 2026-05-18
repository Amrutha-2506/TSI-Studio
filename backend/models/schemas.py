from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParseEmailRequest(BaseModel):
    emailThread: str = Field(..., min_length=20, max_length=100000)
    selectedCategory: str = Field(default="", max_length=80)
    agentInstructions: str = Field(default="", max_length=4000)


class AddEmailRequest(BaseModel):
    sessionId: str = Field(..., min_length=1, max_length=120)
    emailContent: str = Field(..., min_length=20, max_length=50000)


class ParsedEmail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    position: int = 0
    type: str
    sender: str
    senderType: str = "Customer"
    from_: str = Field(default="", alias="from")
    fromName: str = ""
    to: str = ""
    subject: str = ""
    date: str = ""
    timestamp: str
    preview: str
    body: str
    hasServiceAddress: bool = False


class EmailListResponse(BaseModel):
    sessionId: str
    emails: list[ParsedEmail]
    detectedCategory: str = ""
    selectedCategory: str = ""
    prompt: str = ""
    generatedReply: str = ""


class GenerateReplyRequest(BaseModel):
    sessionId: str = Field(default="", max_length=120)
    emails: list[dict[str, Any]] = Field(default_factory=list)
    selectedCategory: str = Field(default="", max_length=80)
    agentInstructions: str = Field(default="", max_length=4000)
    accountData: dict[str, Any] = Field(default_factory=dict)
    prompt: str = Field(default="", max_length=4000)


class ReplyRegenerateRequest(BaseModel):
    sessionId: str = Field(default="", max_length=120)
    emails: list[dict[str, Any]] = Field(default_factory=list)
    selectedCategory: str = Field(default="", max_length=80)
    agentInstructions: str = Field(default="", max_length=4000)
    accountData: dict[str, Any] = Field(default_factory=dict)
    previousReply: str = Field(default="", max_length=12000)
    regenerationInstruction: str = Field(default="", max_length=1000)


class ReplyResponse(BaseModel):
    reply: str
    qualityCheck: dict[str, Any] = Field(default_factory=dict)


class SessionResetRequest(BaseModel):
    sessionId: str = Field(..., min_length=1, max_length=120)


class SessionResetResponse(BaseModel):
    success: bool
    message: str


class SessionResponse(BaseModel):
    sessionId: str
    emails: list[ParsedEmail]
    detectedCategory: str = ""
    selectedCategory: str = ""
    prompt: str = ""
    generatedReply: str = ""


EmailParseRequest = ParseEmailRequest
EmailAddRequest = AddEmailRequest
ReplyGenerateRequest = GenerateReplyRequest
