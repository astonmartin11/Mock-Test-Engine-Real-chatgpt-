from ai.router import AIRouter
from ai.schemas import AnswerEvaluation
from ai.prompts.answer_grader import GRADER_SYSTEM,GRADER_PROMPT
from assessment.mastery import apply_topics

def grade(question,reference_solution,student_answer,max_score,user_id,topic_context=''):
    result=AIRouter().structured('ANSWER_GRADE',GRADER_PROMPT.format(question=question,solution=reference_solution,answer=student_answer,max_score=max_score,topics=topic_context or 'None'),AnswerEvaluation,GRADER_SYSTEM,'high',3000)
    result_score=min(max(float(result.score),0),float(max_score))
    apply_topics(user_id,result.topics)
    data=result.model_dump(); data['score']=result_score; data['max_score']=max_score
    return data
