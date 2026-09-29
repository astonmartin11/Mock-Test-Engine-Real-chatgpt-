from __future__ import annotations
import streamlit as st
from database.connection import check_connection
from database.repositories.mastery import MasteryRepository
from database.repositories.topics import TopicRepository
from database.repositories.documents import DocumentRepository
from documents.pipeline import ingest_document
from assessment.question_generator import generate_mock_test
from assessment.evaluator import evaluate
from tutor.tutor import answer as tutor_answer
from utils.auth import current_user
from utils.ui import active_subject

st.set_page_config(page_title='Adaptive AI Mock Test Engine',page_icon='🎓',layout='wide')

def main():
    st.title('🎓 Adaptive AI Mock Test Engine')
    if not check_connection(): st.error('Neon database connection failed. Check DATABASE_URL.'); st.stop()
    user=current_user(); subject=active_subject(user['id'])
    with st.sidebar:
        st.header('Student'); st.write(user.get('display_name') or user.get('email'))
        st.header('Active Subject'); st.write(subject['name'])
        st.subheader('Grey Areas')
        grey=MasteryRepository().grey(user['id'],subject['id'],5)
        if grey:
            for g in grey: st.write(f"• {g['topic_name']} — {float(g['mastery_score'])*10:.1f}/10")
        else: st.caption('No grey areas yet.')
    dash,docs,test,ev,tutor=st.tabs(['Dashboard','Documents','Mock Test','Evaluate','Tutor'])
    with dash:
        c1,c2=st.columns(2); c1.metric('Topics',TopicRepository().count_for_subject(subject['id'])); c2.metric('Documents',len(DocumentRepository().list_for_subject(subject['id'])))
        st.info('Routing: deterministic work → Python/SQL; document/vision → Gemini; deep reasoning/grading → GPT-OSS 120B.')
    with docs:
        upload=st.file_uploader('Course material',type=['pdf','pptx','txt'])
        dtype=st.selectbox('Type',['syllabus','notes','slides','pyq','reference'])
        if upload and st.button('Process document',type='primary'):
            with st.spinner('Uploading, extracting and indexing...'):
                try:
                    r=ingest_document(user['id'],subject['id'],upload.name,upload.type or 'application/octet-stream',upload.getvalue(),dtype)
                    st.success(f"Indexed {r['chunk_count']} chunks and {r['topic_count']} topics.")
                except Exception as e: st.error(str(e))
    with test:
        n=st.number_input('Numericals',0,10,3); d=st.number_input('Derivations',0,10,2); t=st.number_input('Theory',0,10,3); diff=st.slider('Difficulty',1,5,3); override=st.text_area('Critical Override')
        if st.button('Generate adaptive test',type='primary'):
            with st.spinner('Generating and validating questions...'):
                try:
                    result=generate_mock_test(user['id'],subject['id'],n,d,t,diff,override or None)
                    st.session_state['latest_test']=result
                    for i,q in enumerate(result['questions'],1): st.markdown(f"### Q{i}. {q['question_text']}\n**{q['marks']} marks**")
                except Exception as e: st.error(str(e))
    with ev:
        question=st.text_area('Question'); solution=st.text_area('Reference solution'); answer=st.text_area('Student answer')
        img=st.file_uploader('Or upload handwritten answer image',type=['png','jpg','jpeg'])
        if st.button('Evaluate',type='primary'):
            if not question or (not answer and not img): st.warning('Provide a question and answer.'); return
            with st.spinner('Evaluating...'):
                try:
                    r=evaluate(question,solution,10,user['id'],answer if answer else None,img.getvalue() if img else None,img.type if img else None)
                    st.success(f"Score: {r['score']:.2f}/{r['max_score']:.2f}"); st.write(r['feedback']); st.json(r)
                except Exception as e: st.error(str(e))
    with tutor:
        prompt=st.chat_input('Ask your engineering tutor...')
        if prompt:
            with st.chat_message('user'): st.write(prompt)
            with st.chat_message('assistant'):
                with st.spinner('Thinking...'):
                    try: st.write(tutor_answer(user['id'],subject['id'],prompt)['answer'])
                    except Exception as e: st.error(str(e))

if __name__=='__main__': main()
