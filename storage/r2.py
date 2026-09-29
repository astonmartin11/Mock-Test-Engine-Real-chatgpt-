from functools import lru_cache
import boto3
from config import get_env

@lru_cache(maxsize=1)
def client():
    return boto3.client('s3',endpoint_url=get_env('R2_ENDPOINT'),aws_access_key_id=get_env('R2_ACCESS_KEY_ID'),aws_secret_access_key=get_env('R2_SECRET_ACCESS_KEY'),region_name='auto')
class R2Storage:
    def __init__(self): self.bucket=get_env('R2_BUCKET_NAME')
    def put(self,key,data,content_type): client().put_object(Bucket=self.bucket,Key=key,Body=data,ContentType=content_type)
    def get(self,key): return client().get_object(Bucket=self.bucket,Key=key)['Body'].read()
    def delete(self,key): client().delete_object(Bucket=self.bucket,Key=key)
    def presigned_get(self,key,expires=3600): return client().generate_presigned_url('get_object',Params={'Bucket':self.bucket,'Key':key},ExpiresIn=expires)
    def presigned_put(self,key,content_type,expires=3600): return client().generate_presigned_url('put_object',Params={'Bucket':self.bucket,'Key':key,'ContentType':content_type},ExpiresIn=expires)
