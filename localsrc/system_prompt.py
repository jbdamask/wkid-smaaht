import boto3
import abc
import os

class PromptStrategy(abc.ABC):
    @abc.abstractmethod
    def get_prompt(self, key):
        pass

    @abc.abstractmethod
    def list_prompts(self):
        pass

class FilePromptStrategy(PromptStrategy):
    def get_prompt(self, file_path):
        with open(file_path, 'r') as file:
            return file.read()
        
    def list_prompts(self):
        return os.listdir()  # assuming prompts are files in the current directory

class DynamoDBPromptStrategy(PromptStrategy):
    def __init__(self, table_name):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')

    def get_prompt(self, prompt_name):
        table = self.dynamodb.Table(self.table_name)
        response = table.get_item(Key={'prompt_name': prompt_name})
        return response['Item']['system_prompt']
    
    def list_prompts(self):
        table = self.dynamodb.Table(self.table_name)
        response = table.scan()
        return [item['prompt_name'] for item in response['Items']]

class S3PromptStrategy(PromptStrategy):
    def __init__(self, bucket_name):
        self.bucket_name = bucket_name
        self.s3 = boto3.client('s3')

    def get_prompt(self, file_key):
        obj = self.s3.get_object(Bucket=self.bucket_name, Key=file_key)
        return obj['Body'].read().decode('utf-8')
    
    def list_prompts(self):
        response = self.s3.list_objects(Bucket=self.bucket_name)
        return [item['Key'] for item in response.get('Contents', [])]

class SystemPrompt:
    def __init__(self, strategy):
        self.strategy = strategy

    def get_prompt(self, key):
        return self.strategy.get_prompt(key)

    def list_prompts(self):
        return self.strategy.list_prompts()