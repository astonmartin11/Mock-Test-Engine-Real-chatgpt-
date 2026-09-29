from ai.router import AIRouter
from ai.schemas import DraftTest
from ai.prompts.question_generator import QUESTION_SYSTEM,QUESTION_PROMPT
from database.repositories.mastery import MasteryRepository
from database.repositories.topics import TopicRepository
from database.repositories.tests import TestRepository,QuestionRepository
from documents.retrieval import retrieve
from assessment.question_validator import validate_question

def generate_mock_test(user_id,subject_id,num_numericals,num_derivations,num_theory,difficulty,critical_override=None):
    topics=TopicRepository().list_for_subject(subject_id); grey=MasteryRepository().grey(user_id,subject_id,5)
    search=' '.join([t['name'] for t in topics[:12]]+[g['topic_name'] for g in grey]) or 'engineering course'
    evidence=retrieve(subject_id,search,10)
    evidence_text='\n\n'.join(f"[CHUNK {x['id']}]\n{x['content'][:2200]}" for x in evidence)
    draft=AIRouter().structured('QUESTION_DRAFT',QUESTION_PROMPT.format(subject=subject_id,difficulty=difficulty,num_numericals=num_numericals,num_derivations=num_derivations,num_theory=num_theory,grey='\n'.join('- '+g['topic_name'] for g in grey) or 'None',override=critical_override or 'None',evidence=evidence_text),DraftTest,QUESTION_SYSTEM,max_tokens=3000)
    qrepo=QuestionRepository(); trepo=TestRepository(); created=[]
    for item in draft.questions:
        validation=validate_question(item.model_dump(),evidence_text)
        if not validation.is_valid: continue
        row=qrepo.create(subject_id=subject_id,question_type=item.question_type,difficulty=item.difficulty,question_text=item.question_text,solution_json={'solution': item.solution},grading_rubric={'rubric': item.grading_rubric},expected_answer=item.expected_answer,marks=item.marks)
        for i,tname in enumerate(item.topic_names):
            match=next((t for t in topics if t['name'].lower()==tname.lower()),None)
            if match: qrepo.add_topic(str(row['id']),str(match['id']),1 if i==0 else .5,i==0)
        created.append(row)
    grey_snapshot=[{'topic_id':str(g['topic_id']),'topic_name':g['topic_name'],'mastery_score':float(g['mastery_score'])} for g in grey]
    test=trepo.create(user_id=user_id,subject_id=subject_id,title='Adaptive Engineering Mock Test',difficulty=difficulty,num_numericals=num_numericals,num_derivations=num_derivations,num_theory=num_theory,duration_minutes=None,critical_override=critical_override,grey_area_snapshot=grey_snapshot,total_marks=sum(float(q['marks']) for q in created))
    for i,q in enumerate(created,1): trepo.add_question(str(test['id']),str(q['id']),i)
    return {'test':test,'questions':created,'grey_areas':grey_snapshot}
