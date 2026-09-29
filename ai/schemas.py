from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field

class DraftQuestion(BaseModel):
    question_type: Literal['numerical','derivation','theory']
    difficulty: int = Field(ge=1, le=5)
    question_text: str
    expected_answer: str
    marks: float = Field(gt=0)
    solution: dict[str, Any]
    grading_rubric: dict[str, Any]
    topic_names: list[str]
    evidence_chunk_ids: list[str]

class DraftTest(BaseModel):
    title: str
    questions: list[DraftQuestion]

class QuestionValidation(BaseModel):
    is_valid: bool
    academic_correctness: bool
    difficulty_match: bool
    source_grounded: bool
    solution_consistent: bool
    ambiguity: bool
    issues: list[str]

class EvaluationStep(BaseModel):
    step_number: int
    student_step: str
    expected_step: str
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    status: Literal['correct','partially_correct','incorrect','missing']
    error_type: str | None
    feedback: str

class TopicEvaluation(BaseModel):
    topic_id: str
    normalized_score: float = Field(ge=0, le=1)
    error_severity: float = Field(ge=0, le=1)

class AnswerEvaluation(BaseModel):
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    correctness: float = Field(ge=0, le=1)
    feedback: str
    final_verdict: str
    needs_manual_review: bool
    is_grey_area: bool
    steps: list[EvaluationStep]
    topics: list[TopicEvaluation]

class Transcription(BaseModel):
    transcript_text: str
    latex_text: str
    confidence: float = Field(ge=0, le=1)
    notes: list[str]

class TopicExtraction(BaseModel):
    topics: list[dict[str, Any]]
