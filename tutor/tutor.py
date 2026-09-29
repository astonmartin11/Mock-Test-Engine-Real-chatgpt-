from ai.router import AIRouter
from ai.prompts.tutor import TUTOR_SYSTEM,TUTOR_PROMPT
from database.repositories.mastery import MasteryRepository
from database.repositories.tutor import TutorRepository
from tutor.memory import get_memories
from tutor.retrieval import retrieve

def answer(user_id,subject_id,question,conversation_id=None):
    grey=MasteryRepository().grey(user_id,subject_id,5); memories=get_memories(user_id,subject_id,8); evidence=retrieve(subject_id,question,8)
    state={'grey_areas':[{'topic':g['topic_name'],'mastery':float(g['mastery_score'])} for g in grey],'memories':[{'type':m['memory_type'],'text':m['memory_text']} for m in memories]}
    repo=TutorRepository(); history='None'
    if conversation_id:
        history='\n'.join(f"{x['role']}: {x['content']}" for x in reversed(repo.recent(conversation_id,6)))
    advanced=any(k in question.lower() for k in ['derive','prove','calculate','solve','matrix','equation','jacobian','kalman'])
    task='TUTOR_ADVANCED' if advanced else 'TUTOR_SIMPLE'
    response=AIRouter().text(task,TUTOR_PROMPT.format(question=question,conversation=history),TUTOR_SYSTEM.format(state=state,evidence='\n\n'.join(x['content'][:2200] for x in evidence)),('high' if advanced else 'medium'),2200)
    if conversation_id is None: conversation_id=str(repo.create_conversation(user_id,subject_id,question[:80])['id'])
    repo.add_message(conversation_id,'user',question); repo.add_message(conversation_id,'assistant',response,'openai/gpt-oss-120b' if advanced else 'gemini-3.8-flash')
    return {'answer':response,'conversation_id':conversation_id,'advanced':advanced}
