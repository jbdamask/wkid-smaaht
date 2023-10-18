# prod.py
from src.system_prompt import SystemPrompt, DynamoDBPromptStrategy

class ProductionConfig:
    DEBUG = False
    PROMPT_STRATEGY = DynamoDBPromptStrategy(table_name='GPTSystemPrompts')
    DEFAULT_PROMPT = 'default'
