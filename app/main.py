from fastapi import FastAPI
from .schemas import (
    ChatRequest,
    ChatResponse,
    InsuranceAnalysisRequest,
    InsuranceAnalysisResponse,
    InsuranceAssistantResponse,
    CustomerVerificationRequest,
    CustomerVerificationResponse,
    PersonalQuestionRequest,
    PersonalQuestionResponse,
    GeneralQuestionRequest,
    GeneralQuestionResponse,
    SecureLifeAssistantRequest,
    SecureLifeAssistantResponse,
)
from .ollama_client import (
    chat_with_ollama,
    analyze_insurance_message,
    run_insurance_assistant,
    answer_personal_question,
    answer_general_question,
    run_securelife_assistant,
    clear_session,
)
from .insurance_database import verify_customer


app = FastAPI(
    title="SecureLife Local Insurance AI Assistant",
    description="A local offline insurance assistant using FastAPI, Ollama, RAG, and session-based customer verification.",
    version="0.1.0",
)

@app.get("/")
def root():
    return {
        "message": "SecureLife Local Insurance AI Assistant API is running."
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = chat_with_ollama(
        message=request.message,
        model=request.model,
        temperature=request.temperature,
    )
    return result

@app.post("/analyze-insurance-message", response_model=InsuranceAnalysisResponse)
def analyze_message(request: InsuranceAnalysisRequest):
    result = analyze_insurance_message(
        message=request.message,
        model=request.model,
        temperature=request.temperature,
    )
    return result

@app.post("/insurance-assistant", response_model=InsuranceAssistantResponse)
def insurance_assistant(request: InsuranceAnalysisRequest):
    result = run_insurance_assistant(
        message=request.message,
        model=request.model,
        temperature=request.temperature,
    )
    return result

@app.post("/verify-customer", response_model=CustomerVerificationResponse)
def verify_customer_endpoint(request: CustomerVerificationRequest):
    result = verify_customer(
        policy_number=request.policy_number,
        access_code=request.access_code,
    )
    return result

@app.post("/answer-personal-question", response_model=PersonalQuestionResponse)
def answer_personal_question_endpoint(request: PersonalQuestionRequest):
    result = answer_personal_question(
        message=request.message,
        policy_number=request.policy_number,
        access_code=request.access_code,
        model=request.model,
        temperature=request.temperature,
    )
    return result

@app.post("/answer-general-question", response_model=GeneralQuestionResponse)
def answer_general_question_endpoint(request: GeneralQuestionRequest):
    result = answer_general_question(
        message=request.message,
        model=request.model,
        temperature=request.temperature,
    )
    return result

@app.post("/securelife-assistant", response_model=SecureLifeAssistantResponse)
def securelife_assistant_endpoint(request: SecureLifeAssistantRequest):
    result = run_securelife_assistant(
        message=request.message,
        model=request.model,
        temperature=request.temperature,
        session_id=request.session_id,
    )

    return result

@app.post("/end-session")
def end_session(session_id: str):
    clear_session(session_id)

    return {
        "message": "Session ended. Verification has been reset.",
        "session_id": session_id,
    }