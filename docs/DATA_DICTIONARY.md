# Data Dictionary

The project uses fictional sample data for demonstration.

## General knowledge files

| File | Purpose |
|---|---|
| `company_profile.txt` | Company overview, supported products, support channels, and general chatbot rules |
| `motor_comprehensive_policy.txt` | Motor product summary, coverage, add-ons, deductible, exclusions, and claim rules |
| `claims_process_faq.txt` | Claim submission process, review steps, status meanings, timelines, and required documents |
| `complaints_escalation.txt` | Complaint submission, escalation levels, expected information, and chatbot handling rules |
| `renewals_cancellations_refunds.txt` | Renewal, cancellation, refund, non-payment, and travel cancellation rules |

## Private customer files

| File | Main key | Purpose |
|---|---|---|
| `customers.csv` | `customer_id` | Customer identity and access code |
| `policies.csv` | `policy_number` | Policy record, product, dates, premium, deductible, coverage limit, and vehicle fields |
| `claims.csv` | `claim_id` | Claim status, submitted date, resolution estimate, amount, and last update |
| `claim_documents.csv` | `document_id` | Claim-document statuses linked to claims |
| `payments.csv` | `payment_id` | Payment amount, due date, status, and paid date |
| `policy_addons.csv` | `addon_id` | Included or not-included policy add-ons |
| `support_tickets.csv` | `ticket_id` | Support tickets linked to customers and policies |

## Authentication relation

`policy_number` links a request to a policy. The policy contains `customer_id`. The customer row contains the `access_code`. After verification, the assistant loads claims, payments, add-ons, documents, and support tickets connected to the policy.
