COMPANY_NAME = "SecureLife Insurance"

SUPPORTED_PRODUCTS = [
    "Motor Comprehensive Insurance",
    "Health Gold Insurance",
    "Travel Protect Insurance",
]

POLICY_NUMBER_PATTERN = r"\bSL-(?:MOTOR|HEALTH|TRAVEL)-\d{4}\b"
CLAIM_ID_PATTERN = r"\bCLM-\d{4}\b"
CUSTOMER_ID_PATTERN = r"\bCUST-\d{4}\b"
PAYMENT_ID_PATTERN = r"\bPAY-\d{4}\b"
TICKET_ID_PATTERN = r"\bTCK-\d{4}\b"

ACCESS_CODE_PATTERN = r"\b\d{4}\b"