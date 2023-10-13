# prod.py
from src.system_prompt import SystemPrompt, DynamoDBPromptStrategy

class ProductionConfig:
    DEBUG = False
    PROMPT_STRATEGY = DynamoDBPromptStrategy(table_name='GPTSystemPrompts')
    DEFAULT_PROMPT = 'default'

    # PROMPT = SystemPrompt(PROMPT_STRATEGY)
    # SYSTEM_PROMPT = PROMPT.get_prompt(DEFAULT_PROMPT)
