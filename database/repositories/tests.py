from __future__ import annotations
from database.connection import execute, execute_returning
class TestRepository:
    def create(self,**k):
        return execute_returning('''INSERT INTO tests(user_id,subject_id,title,difficulty,num_numericals,num_derivations,num_theory,duration_minutes,critical_override,grey_area_snapshot,total_marks,generation_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'completed') RETURNING *;''',(k['user_id'],k['subject_id'],k['title'],k['difficulty'],k['num_numericals'],k['num_derivations'],k['num_theory'],k.get('duration_minutes'),k.get('critical_override'),k.get('grey_area_snapshot',[]),k.get('total_marks',0)))
    def add_question(self,test_id,question_id,question_number): execute('INSERT INTO test_questions(test_id,question_id,question_number) VALUES(%s,%s,%s);',(test_id,question_id,question_number))
class QuestionRepository:
    def create(self,**k):
        return execute_returning('''INSERT INTO questions(subject_id,question_type,difficulty,question_text,solution_json,grading_rubric,expected_answer,marks) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *;''',(k['subject_id'],k['question_type'],k['difficulty'],k['question_text'],k['solution_json'],k['grading_rubric'],k['expected_answer'],k['marks']))
    def add_topic(self,question_id,topic_id,relevance_weight=1.0,is_primary=False): execute('''INSERT INTO question_topics(question_id,topic_id,relevance_weight,is_primary) VALUES(%s,%s,%s,%s) ON CONFLICT(question_id,topic_id) DO UPDATE SET relevance_weight=EXCLUDED.relevance_weight,is_primary=EXCLUDED.is_primary;''',(question_id,topic_id,relevance_weight,is_primary))
