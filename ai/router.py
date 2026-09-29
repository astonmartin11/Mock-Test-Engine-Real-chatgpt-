from ai.providers.gemini import GeminiProvider
from ai.providers.groq import GroqProvider

GEMINI_TASKS={'DOCUMENT_SUMMARIZE','DOCUMENT_VISION','TOPIC_EXTRACTION','QUESTION_DRAFT','ANSWER_TRANSCRIBE','TUTOR_SIMPLE'}
GROQ_TASKS={'QUESTION_VALIDATE','SOLUTION_GENERATE','ANSWER_GRADE','TUTOR_ADVANCED'}

class AIRouter:
    def __init__(self): self._gemini=None; self._groq=None
    @property
    def gemini(self):
        if self._gemini is None: self._gemini=GeminiProvider()
        return self._gemini
    @property
    def groq(self):
        if self._groq is None: self._groq=GroqProvider()
        return self._groq
    def text(self,task,prompt,system=None,reasoning_effort='medium',max_tokens=2000):
        if task in GEMINI_TASKS: return self.gemini.text(prompt,system)
        if task in GROQ_TASKS: return self.groq.text(prompt,system,reasoning_effort,max_tokens)
        raise ValueError(f'No text route for {task}')
    def structured(self,task,prompt,schema_model,system=None,reasoning_effort='medium',max_tokens=2600):
        if task in GEMINI_TASKS: return schema_model.model_validate(self.gemini.json(prompt,system))
        if task in GROQ_TASKS: return self.groq.structured(prompt,schema_model,system,reasoning_effort,max_tokens)
        raise ValueError(f'No structured route for {task}')
