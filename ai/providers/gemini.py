from __future__ import annotations
import json,time
from typing import Any
from io import BytesIO
from google import genai
from google.genai import types
from config import get_env, models

class GeminiProvider:
    def __init__(self):
        self.client=genai.Client(api_key=get_env('GEMINI_API_KEY'))
        self.model=models()['gemini']
    def text(self,prompt,system=None,temperature=.2):
        cfg=types.GenerateContentConfig(temperature=temperature,system_instruction=system)
        r=self.client.models.generate_content(model=self.model,contents=prompt,config=cfg)
        if not getattr(r,'text',None): raise RuntimeError('Gemini returned empty output.')
        return r.text
    def json(self,prompt,system=None,retries=2):
        last=None
        for i in range(retries+1):
            try:
                cfg=types.GenerateContentConfig(response_mime_type='application/json',temperature=.1,system_instruction=system)
                r=self.client.models.generate_content(model=self.model,contents=prompt,config=cfg)
                return json.loads(r.text)
            except Exception as e:
                last=e
                if i<retries: time.sleep(1)
        raise RuntimeError(f'Gemini JSON failed: {last}')
    def vision(self,data,mime_type,prompt):
        part=types.Part.from_bytes(data=data,mime_type=mime_type)
        r=self.client.models.generate_content(model=self.model,contents=[part,prompt],config=types.GenerateContentConfig(temperature=0))
        if not getattr(r,'text',None): raise RuntimeError('Gemini vision returned empty output.')
        return r.text
    def pdf(self,data,prompt):
        uploaded=self.client.files.upload(file=BytesIO(data),config={'mime_type':'application/pdf'})
        r=self.client.models.generate_content(model=self.model,contents=[uploaded,prompt])
        if not getattr(r,'text',None): raise RuntimeError('Gemini PDF analysis returned empty output.')
        return r.text
