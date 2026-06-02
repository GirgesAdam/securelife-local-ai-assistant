# Test Questions

## General company questions

```text
What policies does SecureLife offer?
What insurance plans do you provide?
What are your customer support hours?
How can I submit a claim?
How long does claim review usually take?
How can I file a complaint?
What are the complaint escalation levels?
How can I renew my policy?
Can I cancel my travel policy after the trip starts?
Does the chatbot calculate refund amounts?
```

## Motor coverage questions

```text
What does Motor Comprehensive Insurance cover?
Does motor insurance cover theft?
What documents are needed for a motor accident claim?
What documents are needed for a theft claim?
What are the optional motor add-ons?
What is not covered by the motor policy?
Should I repair the car before SecureLife inspects it?
```

## Personal questions requiring verification

Use `session_id` consistently through the flow.

```text
What is the status of my claim?
Did you receive my claim documents?
What payments do I have?
Which add-ons are included in my policy?
What is my policy coverage limit?
Do I have agency repair?
Is there any open support ticket on my policy?
```

## Authentication tests

```text
What is the status of my claim?
SL-MOTOR-1001
1234
Which add-ons are included in my policy?
```

Wrong-code test:

```text
What is the status of my claim?
SL-MOTOR-1001
0000
1111
2222
```

Broken policy format test:

```text
What is the status of my claim?
MOTOR1001
```

Standalone code test:

```text
1234
```

## Out-of-scope tests

```text
What is the weather today?
Write me a poem about football.
What is the price of Bitcoin?
```
