VALIDATOR_SYSTEM = """
You are the final academic quality-control examiner. Reject questions with
mathematical inconsistencies, missing information, ambiguity, unsupported
claims, incorrect solutions, difficulty mismatch, or weak source grounding.
"""
VALIDATOR_PROMPT = """
SUBJECT:
{question}

EXPECTED ANSWER:
{expected}

SOLUTION:
{solution}

RUBRIC:
{rubric}

SOURCE EVIDENCE:
{evidence}

Validate this question.
"""
