import json
from ai.router import AIRouter
from ai.schemas import QuestionValidation
from ai.prompts.question_validator import VALIDATOR_SYSTEM,VALIDATOR_PROMPT

def validate_question(question,evidence):
    return AIRouter().structured('QUESTION_VALIDATE',VALIDATOR_PROMPT.format(question=question['question_text'],expected=question['expected_answer'],solution=json.dumps(question['solution']),rubric=json.dumps(question['grading_rubric']),evidence=evidence),QuestionValidation,VALIDATOR_SYSTEM,'high',1200)
