import ollama
import json
import re
from pydantic import ValidationError
from .schemas import InsuranceAnalysisResponse
from .prompts.insurance_prompt import INSURANCE_ANALYSIS_PROMPT
from .settings import (
    POLICY_NUMBER_PATTERN,
    CLAIM_ID_PATTERN,
    CUSTOMER_ID_PATTERN,
    PAYMENT_ID_PATTERN,
    TICKET_ID_PATTERN,
    ACCESS_CODE_PATTERN,
)
from .insurance_database import (
    get_customer_context,
    get_customer_context_by_policy,
    policy_exists,
)
from .prompts.personal_answer_prompt import PERSONAL_ANSWER_PROMPT
from .document_retriever import retrieve_relevant_chunks
from .prompts.general_answer_prompt import GENERAL_ANSWER_PROMPT


AUTH_SESSIONS = {}
VERIFIED_SESSIONS = {}
MAX_ACCESS_CODE_ATTEMPTS = 3



def create_verified_session(
    session_id: str,
    policy_number: str,
    customer_name: str,
) -> None:
    VERIFIED_SESSIONS[session_id] = {
        "policy_number": policy_number,
        "customer_name": customer_name,
    }


def get_verified_session(session_id: str) -> dict | None:
    return VERIFIED_SESSIONS.get(session_id)


def clear_session(session_id: str) -> None:
    AUTH_SESSIONS.pop(session_id, None)
    VERIFIED_SESSIONS.pop(session_id, None)


POLICY_NUMBER_REQUEST_MESSAGE = "Please provide your policy number."
ACCESS_CODE_REQUEST_MESSAGE = "Policy number received. Please provide your access code."


RAG_NO_ANSWER_MESSAGE = "I do not have enough information in the company documents to answer that."

def rag_failed_to_answer(answer: str) -> bool:
    cleaned_answer = answer.strip().lower()

    return (
        not cleaned_answer
        or RAG_NO_ANSWER_MESSAGE.lower() in cleaned_answer
        or "not enough information" in cleaned_answer
        or "do not have enough information" in cleaned_answer
    )


def extract_policy_number(message: str) -> str | None:
    cleaned_message = message.strip().upper()

    if re.fullmatch(POLICY_NUMBER_PATTERN, cleaned_message):
        return cleaned_message

    return None


def extract_access_code(message: str) -> str | None:
    cleaned_message = message.strip()

    if re.fullmatch(ACCESS_CODE_PATTERN, cleaned_message):
        return cleaned_message

    return None


def run_insurance_assistant(message: str, model: str, temperature: float):
    analysis = analyze_insurance_message(
        message=message,
        model=model,
        temperature=temperature,
    )

    response = build_customer_response(analysis)

    return response


def analyze_insurance_message(message: str, model: str, temperature: float):
    schema = InsuranceAnalysisResponse.model_json_schema()

    schema = InsuranceAnalysisResponse.model_json_schema()
    schema_text = json.dumps(schema, indent=2)

    prompt = (
        INSURANCE_ANALYSIS_PROMPT
        .replace("__SCHEMA__", schema_text)
        .replace("__MESSAGE__", message)
    )

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format=schema,
        options={
            "temperature": temperature
        }
    )

    raw_output = response["message"]["content"]


    try:
        validated_output = InsuranceAnalysisResponse.model_validate_json(raw_output)
        result = validated_output.model_dump()
        result = apply_insurance_guardrails(message, result)
        return result

    except ValidationError as error:
        print("VALIDATION ERROR:")
        print(error)

        retry_prompt = f"""
The previous output was invalid.

Return ONLY valid JSON that matches this schema:

{schema}

Customer message:
{message}
"""

        retry_response = ollama.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": retry_prompt,
                }
            ],
            format=schema,
            options={
                "temperature": 0
            }
        )

        retry_output = retry_response["message"]["content"]


        try:
            validated_retry = InsuranceAnalysisResponse.model_validate_json(retry_output)
            result = validated_retry.model_dump()
            result = apply_insurance_guardrails(message, result)
            return result

        except ValidationError as retry_error:
            print("RETRY VALIDATION ERROR:")
            print(retry_error)

            return {
                "intent": "human_agent",
                "summary": "The message could not be reliably analyzed.",
                "requires_authentication": True,
                "priority": "medium",
                "suggested_response": "Please wait while I transfer you to a human support agent.",
                "confidence": 0.0
            }


def apply_insurance_guardrails(message: str, result: dict) -> dict:

    message_lower = message.lower().strip()

    result.setdefault("intent", "general_question")
    result.setdefault("summary", "Customer message analyzed.")
    result.setdefault("requires_authentication", False)
    result.setdefault("priority", "low")
    result.setdefault(
        "suggested_response",
        "Thank you for contacting SecureLife Insurance. How can we help you?"
    )
    result.setdefault("confidence", 0.5)

    def contains_any(phrases: list[str]) -> bool:
        return any(phrase in message_lower for phrase in phrases)

    def priority_at_least_medium():
        if result.get("priority") == "low":
            result["priority"] = "medium"

    # Detect real IDs from your dataset format
    has_policy_number = bool(re.search(POLICY_NUMBER_PATTERN, message, re.IGNORECASE))
    has_claim_id = bool(re.search(CLAIM_ID_PATTERN, message, re.IGNORECASE))
    has_customer_id = bool(re.search(CUSTOMER_ID_PATTERN, message, re.IGNORECASE))
    has_payment_id = bool(re.search(PAYMENT_ID_PATTERN, message, re.IGNORECASE))
    has_ticket_id = bool(re.search(TICKET_ID_PATTERN, message, re.IGNORECASE))

    has_possible_email = bool(
        re.search(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            message,
        )
    )

    has_possible_phone = bool(
        re.search(
            r"(?:\+20[-\s]?)?1[0125]\d[-\s]?\d{3}[-\s]?\d{4}",
            message,
        )
    )

    contains_private_identifier = any([
        has_policy_number,
        has_claim_id,
        has_customer_id,
        has_payment_id,
        has_ticket_id,
        has_possible_email,
        has_possible_phone,
    ])

    personal_case_phrases = [
        "my policy",
        "my claim",
        "my payment",
        "my premium",
        "my account",
        "my renewal",
        "my case",
        "my documents",
        "my coverage",
        "my details",
        "my profile",
        "status of my",
        "check my",
        "i submitted",
        "i paid",
        "i want to cancel my",
        "am i covered",
        "does my policy",
    ]

    is_personal_case = contains_private_identifier or contains_any(personal_case_phrases)

    high_risk_phrases = [
        "legal",
        "lawyer",
        "court",
        "sue",
        "fraud",
        "scam",
        "police",
        "urgent",
        "emergency",
        "hospital",
        "injury",
        "injured",
        "death",
        "angry",
        "ignored",
        "complaint",
        "bad service",
        "terrible",
        "unacceptable",
        "escalate",
    ]

    if contains_any(high_risk_phrases):
        result["priority"] = "high"

        if result["intent"] == "general_question":
            result["intent"] = "complaint"

    # Privacy rule:
    # If customer asks about their own case or provides an ID, authentication is required.
    if is_personal_case:
        result["requires_authentication"] = True

    # These are normally customer-specific.
    always_auth_intents = [
        "claim_status",
        "payment_issue",
        "cancellation_request",
    ]

    if result["intent"] in always_auth_intents:
        result["requires_authentication"] = True
        priority_at_least_medium()

    # These can be general or personal.
    sometimes_auth_intents = [
        "policy_info",
        "coverage_question",
        "renewal_question",
    ]

    if result["intent"] in sometimes_auth_intents and is_personal_case:
        result["requires_authentication"] = True
        priority_at_least_medium()

    if result["intent"] == "complaint":
        result["priority"] = "high"

        if is_personal_case:
            result["requires_authentication"] = True

    # Safer responses when authentication is required
    if result["requires_authentication"]:
        result["suggested_response"] = POLICY_NUMBER_REQUEST_MESSAGE

    # Confidence cleanup
    try:
        result["confidence"] = float(result["confidence"])
    except Exception:
        result["confidence"] = 0.5

    result["confidence"] = max(0.0, min(result["confidence"], 1.0))

    return result


def build_customer_response(analysis: dict) -> dict:
    intent = analysis["intent"]
    requires_authentication = analysis["requires_authentication"]
    suggested_response = analysis["suggested_response"]
    priority = analysis["priority"]

    if intent == "out_of_scope":
        return {
            "action": "out_of_scope",
            "customer_response": suggested_response,
            "analysis": analysis,
        }

    if intent == "human_agent":
        return {
            "action": "transfer_human",
            "customer_response": (
                "I can transfer you to a human support agent. "
                "Please briefly describe your issue so we can route you correctly."
            ),
            "analysis": analysis,
        }

    if intent == "complaint" and priority == "high":
        return {
            "action": "transfer_human",
            "customer_response": (
                "We are sorry for the inconvenience. "
                "Your request should be reviewed by a support specialist. "
                "Please provide your policy number so we can escalate it securely."
            ),
            "analysis": analysis,
        }

    if requires_authentication:
        return {
            "action": "request_authentication",
            "customer_response": suggested_response,
            "analysis": analysis,
        }

    return {
        "action": "answer_general",
        "customer_response": suggested_response,
        "analysis": analysis,
    }

def build_safe_customer_context(customer_context: dict) -> dict:
    return {
        "customer": {
            "customer_id": customer_context["customer"]["customer_id"],
            "full_name": customer_context["customer"]["full_name"],
            "city": customer_context["customer"]["city"],
        },
        "policy": customer_context["policy"],
        "claims": customer_context["claims"],
        "claim_documents": customer_context["claim_documents"],
        "payments": customer_context["payments"],
        "addons": customer_context["addons"],
        "support_tickets": customer_context["support_tickets"],
    }


def generate_personal_answer_from_context(
    message: str,
    customer_context: dict,
    model: str,
    temperature: float,
) -> dict:
    safe_context = build_safe_customer_context(customer_context)
    context_text = json.dumps(safe_context, indent=2)

    prompt = (
        PERSONAL_ANSWER_PROMPT
        .replace("__QUESTION__", message)
        .replace("__CONTEXT__", context_text)
    )

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": temperature
        }
    )

    answer = response["message"]["content"]

    return {
        "verified": True,
        "answer": answer.strip(),
        "policy_number": customer_context["policy"]["policy_number"],
        "customer_name": customer_context["customer"]["full_name"],
    }


def answer_personal_question_for_verified_session(
    message: str,
    policy_number: str,
    model: str,
    temperature: float,
) -> dict:
    customer_context = get_customer_context_by_policy(policy_number)

    if not customer_context["verified"]:
        return {
            "verified": False,
            "answer": "I could not load the verified customer record. Please start verification again.",
            "policy_number": None,
            "customer_name": None,
        }

    return generate_personal_answer_from_context(
        message=message,
        customer_context=customer_context,
        model=model,
        temperature=temperature,
    )


def answer_personal_question(
    message: str,
    policy_number: str,
    access_code: str,
    model: str,
    temperature: float,
) -> dict:
    customer_context = get_customer_context(
        policy_number=policy_number,
        access_code=access_code,
    )

    if not customer_context["verified"]:
        return {
            "verified": False,
            "answer": "Invalid policy number or access code. Please check your details and try again.",
            "policy_number": None,
            "customer_name": None,
        }

    return generate_personal_answer_from_context(
        message=message,
        customer_context=customer_context,
        model=model,
        temperature=temperature,
    )


def answer_general_question(
    message: str,
    model: str,
    temperature: float,
) -> dict:
    chunks = retrieve_relevant_chunks(message, top_k=3)

    if not chunks:
        return {
            "answer": "I do not have enough information in the company documents to answer that."
        }

    context_text = "\n\n".join(
        [
            f"""Document part {index}
Source: {chunk["source"]}
Content:
{chunk["text"]}"""
            for index, chunk in enumerate(chunks, start=1)
        ]
    )

    prompt = (
        GENERAL_ANSWER_PROMPT
        .replace("__QUESTION__", message)
        .replace("__CONTEXT__", context_text)
    )

    response = ollama.chat(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": temperature
        }
    )

    answer = response["message"]["content"].strip()

    return {
        "answer": answer
    }

def handle_failed_access_code_attempt(
    session_id: str,
    pending_auth: dict,
    policy_number: str,
) -> dict:
    attempts = pending_auth.get("access_code_attempts", 0) + 1
    pending_auth["access_code_attempts"] = attempts
    AUTH_SESSIONS[session_id] = pending_auth

    if attempts >= MAX_ACCESS_CODE_ATTEMPTS:
        clear_session(session_id)

        return {
            "action": "transfer_human",
            "customer_response": (
                "The access code was entered incorrectly several times. "
                "Please contact SecureLife support if you forgot your access code."
            ),
            "analysis": pending_auth["analysis"],
            "verified": False,
            "policy_number": policy_number,
            "customer_name": None,
        }

    return {
        "action": "request_access_code",
        "customer_response": "Invalid access code. Please try again.",
        "analysis": pending_auth["analysis"],
        "verified": False,
        "policy_number": policy_number,
        "customer_name": None,
    }


def run_securelife_assistant(
    message: str,
    model: str,
    temperature: float,
    session_id: str = "default",
) -> dict:
    message = message.strip()

    pending_auth = AUTH_SESSIONS.get(session_id)

    # --------------------------------------------------
    # Step A: Waiting for policy number
    # --------------------------------------------------
    if pending_auth and pending_auth["step"] == "waiting_policy_number":
        policy_number = extract_policy_number(message)

        if policy_number:
            if not policy_exists(policy_number):
                return {
                    "action": "request_policy_number",
                    "customer_response": "I could not find that policy number. Please provide your policy number.",
                    "analysis": pending_auth["analysis"],
                    "verified": False,
                    "policy_number": None,
                    "customer_name": None,
                }

            AUTH_SESSIONS[session_id] = {
                "step": "waiting_access_code",
                "pending_question": pending_auth["pending_question"],
                "policy_number": policy_number,
                "analysis": pending_auth["analysis"],
                "access_code_attempts": 0,
            }

            return {
                "action": "request_access_code",
                "customer_response": ACCESS_CODE_REQUEST_MESSAGE,
                "analysis": pending_auth["analysis"],
                "verified": False,
                "policy_number": policy_number,
                "customer_name": None,
            }

        # Broken policy format:
        # cancel authentication and continue as a fresh user message
        AUTH_SESSIONS.pop(session_id, None)

    # --------------------------------------------------
    # Step B: Waiting for access code
    # --------------------------------------------------
    if pending_auth and pending_auth["step"] == "waiting_access_code":
        policy_number = pending_auth["policy_number"]
        original_question = pending_auth["pending_question"]

        access_code = extract_access_code(message)

        if not access_code:
            return handle_failed_access_code_attempt(
                session_id=session_id,
                pending_auth=pending_auth,
                policy_number=policy_number,
            )

        personal_answer = answer_personal_question(
            message=original_question,
            policy_number=policy_number,
            access_code=access_code,
            model=model,
            temperature=temperature,
        )

        if not personal_answer["verified"]:
            return handle_failed_access_code_attempt(
                session_id=session_id,
                pending_auth=pending_auth,
                policy_number=policy_number,
            )

        create_verified_session(
            session_id=session_id,
            policy_number=personal_answer["policy_number"],
            customer_name=personal_answer["customer_name"],
        )

        AUTH_SESSIONS.pop(session_id, None)

        return {
            "action": "answer_personal",
            "customer_response": personal_answer["answer"],
            "analysis": pending_auth["analysis"],
            "verified": True,
            "policy_number": personal_answer["policy_number"],
            "customer_name": personal_answer["customer_name"],
        }

    # --------------------------------------------------
    # If there is no active authentication session,
    # do not accept standalone policy numbers or access codes.
    # --------------------------------------------------
    if not AUTH_SESSIONS.get(session_id):
        if extract_policy_number(message):
            return {
                "action": "request_authentication",
                "customer_response": "Please ask your question first so I know what information you want to check.",
                "analysis": {
                    "intent": "policy_info",
                    "summary": "The customer provided a policy number without asking a question.",
                    "requires_authentication": True,
                    "priority": "low",
                    "suggested_response": "Please ask your question first so I know what information you want to check.",
                    "confidence": 1.0,
                },
                "verified": False,
                "policy_number": None,
                "customer_name": None,
            }

        if extract_access_code(message):
            return {
                "action": "request_authentication",
                "customer_response": "Please ask your question first. Do not send an access code unless I ask for it.",
                "analysis": {
                    "intent": "policy_info",
                    "summary": "The customer provided an access code without an active verification session.",
                    "requires_authentication": True,
                    "priority": "low",
                    "suggested_response": "Please ask your question first. Do not send an access code unless I ask for it.",
                    "confidence": 1.0,
                },
                "verified": False,
                "policy_number": None,
                "customer_name": None,
            }

    # --------------------------------------------------
    # Step C: Normal fresh message analysis
    # --------------------------------------------------
    analysis = analyze_insurance_message(
        message=message,
        model=model,
        temperature=temperature,
    )

    route = build_customer_response(analysis)
    action = route["action"]

    if action == "out_of_scope":
        return {
            "action": "out_of_scope",
            "customer_response": route["customer_response"],
            "analysis": analysis,
            "verified": None,
            "policy_number": None,
            "customer_name": None,
        }

    if action == "transfer_human":
        return {
            "action": "transfer_human",
            "customer_response": route["customer_response"],
            "analysis": analysis,
            "verified": None,
            "policy_number": None,
            "customer_name": None,
        }

    if action == "answer_general":
        general_answer = answer_general_question(
            message=message,
            model=model,
            temperature=temperature,
        )

        final_answer = general_answer["answer"]

        if rag_failed_to_answer(final_answer):
            final_answer = analysis["suggested_response"]

        return {
            "action": "answer_general",
            "customer_response": final_answer,
            "analysis": analysis,
            "verified": None,
            "policy_number": None,
            "customer_name": None,
        }

    if action == "request_authentication":
        verified_session = get_verified_session(session_id)

        if verified_session:
            personal_answer = answer_personal_question_for_verified_session(
                message=message,
                policy_number=verified_session["policy_number"],
                model=model,
                temperature=temperature,
            )

            if personal_answer["verified"]:
                return {
                    "action": "answer_personal",
                    "customer_response": personal_answer["answer"],
                    "analysis": analysis,
                    "verified": True,
                    "policy_number": personal_answer["policy_number"],
                    "customer_name": personal_answer["customer_name"],
                }

            clear_session(session_id)

        AUTH_SESSIONS[session_id] = {
            "step": "waiting_policy_number",
            "pending_question": message,
            "analysis": analysis,
        }

        return {
            "action": "request_policy_number",
            "customer_response": POLICY_NUMBER_REQUEST_MESSAGE,
            "analysis": analysis,
            "verified": False,
            "policy_number": None,
            "customer_name": None,
        }

    return {
        "action": "transfer_human",
        "customer_response": "Please wait while we transfer you to a SecureLife support agent.",
        "analysis": analysis,
        "verified": None,
        "policy_number": None,
        "customer_name": None,
    }
