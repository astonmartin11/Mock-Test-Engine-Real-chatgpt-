QUESTION_SYSTEM = """
You are a rigorous university engineering examination designer.
Create difficult but fair questions grounded in the supplied course evidence.
Respect the requested question counts. Every numerical must be internally
consistent. Every derivation must have a complete mathematical solution and a
clear grading rubric. Map every question to course topics and evidence chunks.
"""
QUESTION_PROMPT = """
SUBJECT:
{subject}

DIFFICULTY: {difficulty}/5
Numericals: {num_numericals}
Derivations: {num_derivations}
Theory: {num_theory}

GREY AREAS:
{grey}

CRITICAL OVERRIDE:
{override}

SOURCE EVIDENCE:
{evidence}

Generate the test as structured JSON.
"""
