from __future__ import annotations
import math
from database.connection import execute_returning, fetch_all, fetch_one
class MasteryRepository:
    def get(self,user_id,topic_id):
        return fetch_one('SELECT * FROM topic_mastery WHERE user_id=%s AND topic_id=%s LIMIT 1;', (user_id,topic_id))
    def grey(self,user_id,subject_id,limit=5):
        return fetch_all('''SELECT tm.*,t.name AS topic_name,t.subject_id FROM topic_mastery tm JOIN topics t ON t.id=tm.topic_id WHERE tm.user_id=%s AND t.subject_id=%s AND tm.is_grey_area=TRUE ORDER BY tm.mastery_score ASC, tm.confidence ASC, tm.low_score_streak DESC LIMIT %s;''',(user_id,subject_id,limit))
    def update(self,user_id,topic_id,score):
        score=max(0.0,min(1.0,float(score)))
        prev=self.get(user_id,topic_id)
        if prev is None:
            execute_returning('INSERT INTO topic_mastery(user_id,topic_id) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING *;', (user_id,topic_id))
            prev=self.get(user_id,topic_id)
        old=float(prev['raw_ema_score'] or .5); attempts=int(prev['attempt_count'] or 0); streak=int(prev['low_score_streak'] or 0)
        ema=.75*old+.25*score; attempts+=1; conf=1-math.exp(-attempts/5); mastery=conf*ema+(1-conf)*.5
        streak=streak+1 if score<.6 else 0; grey=(attempts>=2 and mastery<.6) or streak>=2
        return execute_returning('''UPDATE topic_mastery SET mastery_score=%s,raw_ema_score=%s,confidence=%s,attempt_count=%s,low_score_streak=%s,recent_score=%s,highest_score=GREATEST(COALESCE(highest_score,0),%s),is_grey_area=%s,last_attempt_at=NOW(),updated_at=NOW() WHERE user_id=%s AND topic_id=%s RETURNING *;''',(mastery,ema,conf,attempts,streak,score,score,grey,user_id,topic_id))
