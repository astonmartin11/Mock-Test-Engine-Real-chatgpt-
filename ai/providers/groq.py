from __future__ import annotations
import json,time
from typing import Any,Type
from groq import Groq
from pydantic import BaseModel
from config import get_env, models

def strict_schema(model:Type[BaseModel])->dict[str,Any]:
    schema=model.model_json_schema()
    defs=schema.get('$defs',{})

    def resolve(node):
        if not isinstance(node,dict): return node
        ref=node.get('$ref')
        if ref and ref.startswith('#/$defs/'):
            name=ref.split('/')[-1]
            return resolve(defs.get(name,{}))
        out={k:v for k,v in node.items() if k not in {'$ref','$defs'}}
        if out.get('type')=='object':
            props=out.get('properties',{})
            out['properties']={k:resolve(v) for k,v in props.items()}
            out['required']=list(out['properties'].keys())
            out['additionalProperties']=False
        elif isinstance(out.get('items'),dict):
            out['items']=resolve(out['items'])
        if isinstance(out.get('anyOf'),list):
            out['anyOf']=[resolve(v) for v in out['anyOf']]
        if isinstance(out.get('allOf'),list):
            out['allOf']=[resolve(v) for v in out['allOf']]
        return out

    return resolve(schema)

class GroqProvider:
    def __init__(self):
        self.client=Groq(api_key=get_env('GROQ_API_KEY'))
        self.model=models()['groq']
    def text(self,prompt,system=None,reasoning_effort='medium',max_tokens=2000):
        messages=[]
        if system: messages.append({'role':'system','content':system})
        messages.append({'role':'user','content':prompt})
        r=self.client.chat.completions.create(model=self.model,messages=messages,reasoning_effort=reasoning_effort,max_completion_tokens=max_tokens)
        if not r.choices[0].message.content: raise RuntimeError('Groq returned empty output.')
        return r.choices[0].message.content
    def structured(self,prompt,schema_model,system=None,reasoning_effort='medium',max_tokens=2600):
        messages=[]
        if system: messages.append({'role':'system','content':system})
        messages.append({'role':'user','content':prompt})
        last=None
        for i in range(3):
            try:
                r=self.client.chat.completions.create(model=self.model,messages=messages,reasoning_effort=reasoning_effort,max_completion_tokens=max_tokens,response_format={'type':'json_schema','json_schema':{'name':schema_model.__name__.lower(),'strict':True,'schema':strict_schema(schema_model)}})
                return schema_model.model_validate(json.loads(r.choices[0].message.content))
            except Exception as e:
                last=e
                if i<2: time.sleep(1)
        raise RuntimeError(f'Groq structured output failed: {last}')
