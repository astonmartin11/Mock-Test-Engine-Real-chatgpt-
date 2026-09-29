from database.repositories.mastery import MasteryRepository

def apply_topics(user_id,topics):
    repo=MasteryRepository()
    for topic in topics: repo.update(user_id,topic.topic_id,float(topic.normalized_score))
