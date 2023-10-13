# local_dev.py
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
from src.system_prompt import SystemPrompt, FilePromptStrategy

import os

class DevelopmentConfig:
    DEBUG = True
    PROMPT_STRATEGY = FilePromptStrategy(file_path='gpt4_system_prompts')
    DEFAULT_PROMPT = 'default-system-prompt.txt'

    # PROMPT = SystemPrompt(PROMPT_STRATEGY)
    # SYSTEM_PROMPT = PROMPT.get_prompt(DEFAULT_PROMPT)
