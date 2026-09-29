from assessment.answer_grader import grade
from assessment.answer_transcriber import transcribe_answer

def evaluate(question,reference_solution,max_score,user_id,answer_text=None,image_bytes=None,mime_type=None,topic_context=''):
    transcription=None; text=answer_text or ''
    if image_bytes:
        transcription=transcribe_answer(image_bytes,mime_type or 'image/jpeg'); text=transcription.transcript_text
    result=grade(question,reference_solution,text,max_score,user_id,topic_context)
    if transcription: result['transcription']=transcription.model_dump()
    return result
