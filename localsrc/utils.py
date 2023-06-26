import os
import re
import boto3
from botocore.exceptions import ClientError
# let's use the pprint module for readability
from pprint import pprint
# import inspect module
import inspect
import openai
import base64
import configparser
import requests
import json
import tiktoken
from trafilatura import extract, fetch_url
from trafilatura.settings import use_config
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
from system_prompt import SystemPrompt, FilePromptStrategy, DynamoDBPromptStrategy, S3PromptStrategy


# config = configparser.ConfigParser()
# config.read('settings.ini')
newconfig = use_config()
newconfig.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

DEBUG = True
models = {
    "gpt-3.5-turbo": {"max_token": 4096, "description": "Most capable GPT-3.5 model and optimized for chat at 1/10th the cost of text-davinci-003. Will be updated with our latest model iteration 2 weeks after it is released."},
    "gpt-4": {"max_token": 8192, "description": "More capable than any GPT-3.5 model, able to do more complex tasks, and optimized for chat. Will be updated with our latest model iteration 2 weeks after it is released."}
}
MODEL = "gpt-4"
MAX_TOKENS = models[MODEL]["max_token"]

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN_CHATAWS')
# SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY_CHATAWS')
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN_CHATAWS')
# SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN')
if DEBUG:
    print("SLACK_BOT_TOKEN: ", SLACK_BOT_TOKEN)
    print("SLACK_APP_TOKEN: ", SLACK_APP_TOKEN)

openai.api_key = OPENAI_API_KEY

delimiter = "####"
prompt = SystemPrompt(FilePromptStrategy())
SYSTEM_PROMPT = prompt.get_prompt('gpt4_system_prompts/chataws-system-prompt.txt')

WAIT_MESSAGE = "Got your request. Please wait."
N_CHUNKS_TO_CONCAT_BEFORE_UPDATING = 20
# MAX_TOKENS = 8192

def extract_url_list(text):
    url_pattern = re.compile(
        r'<(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)>'
    )
    url_list = url_pattern.findall(text)
    return url_list if len(url_list)>0 else None

def augment_user_message(user_message, url_list):
    all_url_content = ''
    for url in url_list:
        downloaded = fetch_url(url)
        url_content = extract(downloaded, config=newconfig)
        user_message = user_message.replace(f'<{url}>', '')
        all_url_content = all_url_content + f' Contents of {url} : \n """ {url_content} """'
    user_message = user_message + "\n" + all_url_content
    return user_message

# Make sure the message passes OpenAI's moderation guidelines
def moderate_messages(messages):
    try:
        # Check each message for moderation
        for message in messages:
            response = openai.Moderation.create(
                input=message
            )            
            moderation_output = response["results"][0]
            if(moderation_output.flagged):
                print(f"Moderation output: {moderation_output}")
                return False
            else:
                return 
    except Exception as e:
        print(f"Moderation error: {e}")
        return False

def get_completion_from_messages(messages, 
                                #  model="gpt-3.5-turbo", 
                                #  model="gpt-4",
                                 temperature=0, 
                                 model=MODEL,
                                 max_tokens=MAX_TOKENS,
                                #  stream=True
                                 ):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True
        )
        return response
    except openai.error.Timeout as e:
        #Handle timeout error, e.g. retry or log
        print(f"OpenAI API request timed out: {e}")
        pass
    except openai.error.APIError as e:
        #Handle API error, e.g. retry or log
        print(f"OpenAI API returned an API Error: {e}")
        pass
    except openai.error.APIConnectionError as e:
        #Handle connection error, e.g. check network or log
        print(f"OpenAI API request failed to connect: {e}")
        pass
    except openai.error.InvalidRequestError as e:
        #Handle invalid request error, e.g. validate parameters or log
        print(f"OpenAI API request was invalid: {e}")
        pass
    except openai.error.AuthenticationError as e:
        #Handle authentication error, e.g. check credentials or log
        print(f"OpenAI API request was not authorized: {e}")
        pass
    except openai.error.PermissionError as e:
        #Handle permission error, e.g. check scope or log
        print(f"OpenAI API request was not permitted: {e}")
        pass
    except openai.error.RateLimitError as e:
        #Handle rate limit error, e.g. wait or log
        print(f"OpenAI API request exceeded rate limit: {e}")
        pass
    except Exception as e:
        #Handle other error, e.g. retry or log
        print(f"OpenAI API request failed: {e}")
        pass

# From https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(messages, model="gpt-4"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        print("Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        print("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
        return num_tokens_from_messages(messages, model="gpt-4-0314")
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == "gpt-4-0314":
        tokens_per_message = 3
        tokens_per_name = 1
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens

# This builds the message object, including any previous interactions in the thread
def process_conversation_history(conversation_history, bot_user_id):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in conversation_history['messages'][:-1]:
        role = "assistant" if message['user'] == bot_user_id else "user"
        message_text = process_message(message, bot_user_id)
        if message_text:
            messages.append({"role": role, "content": message_text})
    if DEBUG:
        print("process_conversation_history()")
        pprint(messages)
    return messages


def process_message(message, bot_user_id):
    message_text = message['text']
    role = "assistant" if message['user'] == bot_user_id else "user"
    if role == "user":
        url_list = extract_url_list(message_text)
        if url_list:
            message_text = augment_user_message(message_text, url_list)
    message_text = clean_message_text(message_text, role, bot_user_id)
    return message_text


def clean_message_text(message_text, role, bot_user_id):
    if (f'<@{bot_user_id}>' in message_text) or (role == "assistant"):
        message_text = message_text.replace(f'<@{bot_user_id}>', '').strip()
        return message_text
    return None


def update_chat(app, channel_id, reply_message_ts, response_text):
    app.client.chat_update(
        channel=channel_id,
        ts=reply_message_ts,
        text=response_text
    )
