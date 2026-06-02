from pydantic import BaseModel, Field
from typing import Literal


class InsuranceAnalysisRequest(BaseModel):
    message: str
    model: str = "qwen2.5:7b"
    temperature: float = 0.0


class InsuranceAnalysisResponse(BaseModel):
    intent: Literal[
        "general_question",
        "policy_info",
        "claim_status",
        "payment_issue",
        "complaint",
        "coverage_question",
        "cancellation_request",
        "renewal_question",
        "human_agent",
        "out_of_scope",
    ]
    summary: str
    requires_authentication: bool
    priority: Literal["low", "medium", "high"]
    suggested_response: str
    confidence: float = Field(ge=0, le=1)


class InsuranceAssistantResponse(BaseModel):
    action: Literal[
        "answer_general",
        "request_authentication",
        "transfer_human",
        "out_of_scope"
    ]
    customer_response: str
    analysis: InsuranceAnalysisResponse


class CustomerVerificationRequest(BaseModel):
    policy_number: str
    access_code: str


class CustomerVerificationResponse(BaseModel):
    verified: bool
    message: str
    customer_id: str | None = None
    customer_name: str | None = None
    policy_number: str | None = None
    product_name: str | None = None
    policy_status: str | None = None


class PersonalQuestionRequest(BaseModel):
    message: str
    policy_number: str
    access_code: str
    model: str = "qwen2.5:7b"
    temperature: float = 0.0


class PersonalQuestionResponse(BaseModel):
    verified: bool
    answer: str
    policy_number: str | None = None
    customer_name: str | None = None


class GeneralQuestionRequest(BaseModel):
    message: str
    model: str = "qwen2.5:7b"
    temperature: float = 0.0


class GeneralQuestionResponse(BaseModel):
    answer: str


class SecureLifeAssistantRequest(BaseModel):
    message: str
    session_id: str = "default"
    model: str = "qwen2.5:7b"
    temperature: float = 0


class SecureLifeAssistantResponse(BaseModel):
    action: Literal[
        "answer_general",
        "request_authentication",
        "request_policy_number",
        "request_access_code",
        "answer_personal",
        "transfer_human",
        "out_of_scope",
        "verification_failed",
    ]
    customer_response: str
    analysis: InsuranceAnalysisResponse
    verified: bool | None = None
    policy_number: str | None = None
    customer_name: str | None = None
