import json
from ai.providers.gemini import GeminiProvider
from ai.schemas import Transcription
from ai.prompts.answer_transcriber import TRANSCRIBER_SYSTEM,TRANSCRIBER_PROMPT

def transcribe_answer(image_bytes,mime_type):
    raw=GeminiProvider().vision(image_bytes,mime_type,TRANSCRIBER_SYSTEM+'\n'+TRANSCRIBER_PROMPT)
    try: return Transcription.model_validate(json.loads(raw))
    except Exception: return Transcription(transcript_text=raw,latex_text=raw,confidence=.5,notes=['The provider response was not machine-readable JSON.'])
