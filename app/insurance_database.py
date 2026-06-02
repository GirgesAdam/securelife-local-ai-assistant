import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "private"


def load_csv(filename: str) -> list[dict]:
    file_path = DATA_DIR / filename

    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)


def get_customer_by_id(customer_id: str) -> dict | None:
    customers = load_csv("customers.csv")

    for customer in customers:
        if customer["customer_id"] == customer_id:
            return customer

    return None


def get_policy_by_number(policy_number: str) -> dict | None:
    policies = load_csv("policies.csv")

    for policy in policies:
        if policy["policy_number"].upper() == policy_number.upper():
            return policy

    return None

def policy_exists(policy_number: str) -> bool:
    policy = get_policy_by_number(policy_number)
    return policy is not None


def verify_customer(policy_number: str, access_code: str) -> dict:
    policy = get_policy_by_number(policy_number)

    if not policy:
        return {
            "verified": False,
            "message": "Invalid policy number or access code."
        }

    customer = get_customer_by_id(policy["customer_id"])

    if not customer:
        return {
            "verified": False,
            "message": "Invalid policy number or access code."
        }

    if str(customer["access_code"]) != str(access_code):
        return {
            "verified": False,
            "message": "Invalid policy number or access code."
        }

    return {
        "verified": True,
        "message": "Customer verified successfully.",
        "customer_id": customer["customer_id"],
        "customer_name": customer["full_name"],
        "policy_number": policy["policy_number"],
        "product_name": policy["product_name"],
        "policy_status": policy["status"],
    }

def get_claims_by_policy(policy_number: str) -> list[dict]:
    claims = load_csv("claims.csv")

    return [
        claim for claim in claims
        if claim["policy_number"].upper() == policy_number.upper()
    ]


def get_claim_documents_by_claim_ids(claim_ids: list[str]) -> list[dict]:
    documents = load_csv("claim_documents.csv")

    return [
        document for document in documents
        if document["claim_id"] in claim_ids
    ]


def get_payments_by_policy(policy_number: str) -> list[dict]:
    payments = load_csv("payments.csv")

    return [
        payment for payment in payments
        if payment["policy_number"].upper() == policy_number.upper()
    ]


def get_addons_by_policy(policy_number: str) -> list[dict]:
    addons = load_csv("policy_addons.csv")

    return [
        addon for addon in addons
        if addon["policy_number"].upper() == policy_number.upper()
    ]


def get_support_tickets_by_policy(policy_number: str) -> list[dict]:
    tickets = load_csv("support_tickets.csv")

    return [
        ticket for ticket in tickets
        if ticket["policy_number"].upper() == policy_number.upper()
    ]


def get_customer_context(policy_number: str, access_code: str) -> dict:
    verification = verify_customer(
        policy_number=policy_number,
        access_code=access_code,
    )

    if not verification["verified"]:
        return {
            "verified": False,
            "message": "Invalid policy number or access code.",
        }

    policy = get_policy_by_number(policy_number)
    customer = get_customer_by_id(policy["customer_id"])

    claims = get_claims_by_policy(policy_number)
    claim_ids = [claim["claim_id"] for claim in claims]

    claim_documents = get_claim_documents_by_claim_ids(claim_ids)
    payments = get_payments_by_policy(policy_number)
    addons = get_addons_by_policy(policy_number)
    support_tickets = get_support_tickets_by_policy(policy_number)

    return {
        "verified": True,
        "customer": customer,
        "policy": policy,
        "claims": claims,
        "claim_documents": claim_documents,
        "payments": payments,
        "addons": addons,
        "support_tickets": support_tickets,
    }

def get_customer_context_by_policy(policy_number: str) -> dict:
    """
    Load private customer context after a session has already been verified.

    This function does not check the access code. It should only be called from
    code paths that have already confirmed the customer's identity.
    """
    policy = get_policy_by_number(policy_number)

    if not policy:
        return {
            "verified": False,
            "message": "Policy not found.",
        }

    customer = get_customer_by_id(policy["customer_id"])

    if not customer:
        return {
            "verified": False,
            "message": "Customer not found.",
        }

    claims = get_claims_by_policy(policy_number)
    claim_ids = [claim["claim_id"] for claim in claims]

    return {
        "verified": True,
        "customer": customer,
        "policy": policy,
        "claims": claims,
        "claim_documents": get_claim_documents_by_claim_ids(claim_ids),
        "payments": get_payments_by_policy(policy_number),
        "addons": get_addons_by_policy(policy_number),
        "support_tickets": get_support_tickets_by_policy(policy_number),
    }
