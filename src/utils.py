# utils.py
# Includes various functions and plumbing code.
# Not meant for re-use, but having this file makes it easier to read main application code
from config import get_config
Config = get_config()
import os
import re
import boto3
from botocore.exceptions import ClientError
# let's use the pprint module for readability
from pprint import pprint
# import inspect module
import inspect
# import openai
from openai import OpenAI as openai
import base64
import configparser
import requests
import json
import tiktoken
from trafilatura import extract, fetch_url
from trafilatura.settings import use_config
from cachetools import LRUCache
from src.logger_config import get_logger
from src.system_prompt import SystemPrompt, FilePromptStrategy, DynamoDBPromptStrategy, S3PromptStrategy
from src.chat_manager import ChatManager
from langchain.agents import ConversationalChatAgent, AgentExecutor
from langchain.agents.agent_toolkits import create_conversational_retrieval_agent
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.callbacks import StdOutCallbackHandler
from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.chains.summarize import load_summarize_chain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import WebBaseLoader
from langchain.docstore.document import Document
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import ChatMessageHistory
from langchain.prompts import PromptTemplate, ChatPromptTemplate
# from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate, SystemMessage
from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.tools import DuckDuckGoSearchResults
# from langchain_community.tools import DuckDuckGoSearchResults
from search_tool.ddg_search_langchain_override import DuckDuckGoSearchResults
from langchain.vectorstores.base import VectorStoreRetriever
from chat_with_docs.lc_file_handler import create_file_handler, FileRegistry
from chat_with_docs.rag_fusion import RagFusion
# from chat_with_docs.chat_with_pdf import ChatWithDoc
from chat_with_docs.prompt import CONCISE_SUMMARY_PROMPT, CONCISE_SUMMARY_MAP_PROMPT, CONCISE_SUMMARY_COMBINE_PROMPT

# Configure logging
logger = get_logger(__name__)

prompt = SystemPrompt(Config.PROMPT_STRATEGY)
SYSTEM_PROMPT = prompt.get_prompt(Config.DEFAULT_PROMPT)

# config = configparser.ConfigParser()
# config.read('settings.ini')
newconfig = use_config()
newconfig.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")

DEBUG = Config.DEBUG
models = {
    "gpt-3.5-turbo": {"max_token": 4096, "description": "Most capable GPT-3.5 model and optimized for chat at 1/10th the cost of text-davinci-003. Will be updated with our latest model iteration 2 weeks after it is released."},
    "gpt-4": {"max_token": 8192, "description": "More capable than any GPT-3.5 model, able to do more complex tasks, and optimized for chat. Will be updated with our latest model iteration 2 weeks after it is released."},
    "gpt-3.5-turbo-16k": {"max_token": 16385, "description": "Same capabilities as the standard gpt-3.5-turbo model but with 4 times the context."},
    "gpt-4-turbo-preview": {"max_token": 128000, "description": "The latest GPT-4 model with improved instruction following, JSON mode, reproducible outputs, parallel function calling, and more. Returns a maximum of 4,096 output tokens. This preview model is not yet suited for production traffic."},
}
MODEL = "gpt-4-turbo-preview"
MAX_TOKENS = models[MODEL]["max_token"]

SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN_WKID_SMAAHT')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY_WKID_SMAAHT')
SLACK_APP_TOKEN = os.getenv('SLACK_APP_TOKEN_WKID_SMAAHT')

# client = OpenAI(api_key=OPENAI_API_KEY)
client = openai(api_key=OPENAI_API_KEY)

delimiter = "####"
#### EXAMPLE OF GETTING SYSTEM PROMPT FROM LOCAL FILE
# prompt = SystemPrompt(FilePromptStrategy())
# SYSTEM_PROMPT = prompt.get_prompt('gpt4_system_prompts/chataws-system-prompt.txt')

#### EXAMPLE OF GETTING SYSTEM PROMPT FROM DYNAMODB TABLE
# prompt = SystemPrompt(DynamoDBPromptStrategy(table_name='GPTSystemPrompts'))
# SYSTEM_PROMPT = prompt.get_prompt('default')

#### EXAMPLE OF GETTING SYSTEM PROMPT FROM S3

# Cache that tracks Slack threads with system prompts.
# This will be populated with ChatManager objects and keyed 
# by Slack user_id
cache = LRUCache(maxsize=100)
# fileHandlerCache = LRUCache(maxsize=100)
fileRegistry = FileRegistry()

# Store the GPT4 systemp prompt for the user in the particular channel
def set_prompt_for_user_and_channel(user_id, channel_id, prompt_key):
    c = cache.get(user_id)
    if c is None:
        logger.debug(f"No record for {user_id}, {channel_id}. Creating one")
        cache[user_id] = ChatManager(user_id, channel_id, prompt_key)
    else:
        logger.debug(f"Found record for {user_id}, {channel_id}: ")
        logger.debug(c)
        c.prompt_key = prompt_key

def get_slack_thread(thread_ts):
    return cache.get(thread_ts)

def get_chat_object(user_id, channel_id, thread_ts, prompt_key):
    return cache.setdefault()

WAIT_MESSAGE = "Got your request. Please wait."
N_CHUNKS_TO_CONCAT_BEFORE_UPDATING = 20

# def extract_url_list(text):
#     url_pattern = re.compile(
#         r'<(http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+)>'
#     )
#     url_list = url_pattern.findall(text)
#     return url_list if len(url_list)>0 else None

def extract_url_list(text):
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    url_list = url_pattern.findall(text)
    return url_list if len(url_list) > 0 else None


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
            response = client.moderations.create(input=message)            
            moderation_output = response["results"][0]
            if(moderation_output.flagged):
                logger.debug(f"Moderation output: {moderation_output}")
                return False
            else:
                return 
    except Exception as e:
        logger.debug(f"Moderation error: {e}")
        return False

def prepare_payload(body, context):
    """
    This function prepares the payload for a chat event. It extracts the bot user ID, channel ID, thread timestamp, 
    user ID, and command text from the event body and context.

    Parameters:
    body (dict): The body of the event.
    context (dict): The context of the event.

    Returns:
    tuple: A tuple containing the bot user ID, channel ID, thread timestamp, user ID, and command text.
    """
    event = body.get('event')
    if event is None:
        return None
    bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context.get('bot_user_id')
    channel_id = event.get('channel')
    thread_ts = event.get('thread_ts', event.get('ts'))
    user_id = event.get('user', context.get('user_id'))
    if f"<@{bot_user_id}" in event.get('text'):
        command_text = event.get('text').split(f"<@{bot_user_id}>")[1].strip()
    else:
        command_text = event.get('text')
    return bot_user_id, channel_id, thread_ts, user_id, command_text


def get_completion_from_messages(messages, 
                                 temperature=0, 
                                 model=MODEL,
                                 max_tokens=MAX_TOKENS,
                                 ):
    try:
        response = client.chat.completions.create(model=model,
        messages=messages,
        temperature=temperature,
        stream=True)
        return response
    # TODO All exceptions need to change because the OpenAI API changed!!!!!
    except openai.Timeout as e:
        #Handle timeout error, e.g. retry or log
        logger.error(f"OpenAI API request timed out: {e}")
        pass
    except openai.error.APIError as e:
        #Handle API error, e.g. retry or log
        logger.error(f"OpenAI API returned an API Error: {e}")
        pass
    except openai.error.APIConnectionError as e:
        #Handle connection error, e.g. check network or log
        logger.error(f"OpenAI API request failed to connect: {e}")
        pass
    except openai.error.InvalidRequestError as e:
        #Handle invalid request error, e.g. validate parameters or log
        logger.error(f"OpenAI API request was invalid: {e}")
        pass
    except openai.error.AuthenticationError as e:
        #Handle authentication error, e.g. check credentials or log
        logger.error(f"OpenAI API request was not authorized: {e}")
        pass
    except openai.error.PermissionError as e:
        #Handle permission error, e.g. check scope or log
        logger.error(f"OpenAI API request was not permitted: {e}")
        pass
    except openai.error.RateLimitError as e:
        #Handle rate limit error, e.g. wait or log
        logger.error(f"OpenAI API request exceeded rate limit: {e}")
        pass
    except Exception as e:
        #Handle other error, e.g. retry or log
        logger.error(f"OpenAI API request failed: {e}")
        pass

# From https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
def num_tokens_from_messages(messages, model="gpt-4"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.warning("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo":
        logger.debug("Warning: gpt-3.5-turbo may change over time. Returning num tokens assuming gpt-3.5-turbo-0301.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301")
    elif model == "gpt-4":
        logger.debug("Warning: gpt-4 may change over time. Returning num tokens assuming gpt-4-0314.")
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

# Retrieve text from the Slack conversation thread
def get_conversation_history(app, channel_id, thread_ts):
    """
    This function retrieves the conversation history of a specific thread in a channel using the Slack API.

    Parameters:
    app (object): The application instance.
    channel_id (str): The ID of the channel where the thread is located.
    thread_ts (str): The timestamp of the thread.

    Returns:
    history (dict): The conversation history of the thread.
    """
    history = app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )
    return history

def process_conversation_history(conversation_history, bot_user_id, channel_id, thread_ts, user_id):
    """
    This function processes the conversation history in a chat. It checks for a ChatManager object for the user and 
    a Channel object for the channel. If found, it retrieves the appropriate system prompt. It then processes each 
    message in the conversation history and appends it to a list of messages.

    Parameters:
    conversation_history (dict): The conversation history.
    bot_user_id (str): The ID of the bot user.
    channel_id (str): The ID of the channel.
    thread_ts (str): The timestamp of the thread.
    user_id (str): The ID of the user.

    Returns:
    messages (list): A list of processed messages from the conversation history.
    """
    sp = SYSTEM_PROMPT
    cm = cache.get(user_id)
    if cm is not None:
        channel = cm.get_channel(channel_id)
        if channel is not None:
            found = False
            for thread, prompt_key in channel.items():  
                if thread_ts == thread:  
                    found = True
                    sp = prompt.get_prompt(prompt_key)            
            if not found:
                sp = cm.prompt_key
                cm.add_thread_to_channel(channel_id, thread_ts, sp)
    else:
        logger.debug(f"No ChatManager object for user {user_id}")

    messages = [{"role": "system", "content": sp}]
    for message in conversation_history['messages'][:-1]:
        role = "assistant" if message['user'] == bot_user_id else "user"
        message_text = process_message(message, bot_user_id)
        if message_text:
            messages.append({"role": role, "content": message_text})
    logger.info(messages)
    return messages

def process_message(message, bot_user_id):
    """
    This function determines the role of the message sender and cleans 
    the message text accordingly.

    Parameters:
    message (dict): The message to be processed.
    bot_user_id (str): The ID of the bot user.

    Returns:
    str: The cleaned message text.
    """
    message_text = message['text']
    role = "assistant" if message['user'] == bot_user_id else "user"
    if (f'<@{bot_user_id}>' in message_text) or (role == "assistant"):
        message_text = message_text.replace(f'<@{bot_user_id}>', '').strip()
    # message_text = clean_message_text(message_text, role, bot_user_id)
    return message_text

# def clean_message_text(message_text, role, bot_user_id):
#     """
#     This function cleans the text of a message. If the message is from the bot or mentions the bot, it removes the 
#     bot's mention from the text.

#     Parameters:
#     message_text (str): The text of the message.
#     role (str): The role of the message sender.
#     bot_user_id (str): The ID of the bot user.

#     Returns:
#     str: The cleaned message text.
#     """
#     if (f'<@{bot_user_id}>' in message_text) or (role == "assistant"):
#         message_text = message_text.replace(f'<@{bot_user_id}>', '').strip()
#     return message_text

def update_chat(app, channel_id, reply_message_ts, response_text):
    """
    This function updates a chat message in a specific channel using the Slack API. It takes in the application 
    instance, channel ID, timestamp of the message to be updated, and the new text for the message.

    Parameters:
    app (object): The application instance.
    channel_id (str): The ID of the channel where the message is located.
    reply_message_ts (str): The timestamp of the message to be updated.
    response_text (str): The new text for the message.

    Returns:
    None
    """
    r = app.client.chat_update(
        channel=channel_id,
        ts=reply_message_ts,
        text=response_text
    )

def generate_image(iPrompt):
    """
    This function generates an image using OpenAI's Image API based on a given prompt. It then constructs a response 
    in a specific format that includes the image URL.

    Parameters:
    iPrompt (str): The prompt used to generate the image.

    Returns:
    j (dict): A dictionary containing the response type, blocks, and image details.
    """
    try:
        response = client.images.generate(model='dall-e-3', prompt=iPrompt, n=1, size="1024x1024")
    # except openai.APIConnectionError as e:
    #     print("Server connection error: {e.__cause__}")  # from httpx.
    #     raise
    # except openai.RateLimitError as e:
    #     print(f"OpenAI RATE LIMIT error {e.status_code}: (e.response)")
    #     raise
    # except openai.APIStatusError as e:
    #     print(f"OpenAI STATUS error {e.status_code}: (e.response)")
    #     raise
    # except openai.BadRequestError as e:
    #     print(f"OpenAI BAD REQUEST error {e.status_code}: (e.response)")
    #     raise
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise

    image_url_list = []
    for image in response.data:
        image_url_list.append(image.model_dump()["url"])

    j = {
        "response_type": "in_channel",
        "blocks": [
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": iPrompt,
                    "emoji": True
                },
                "image_url": image_url_list[0],
                "alt_text": iPrompt
            }
        ]
    }
    return j

def copy_history_to_langchain(message):
    """
    This function copies the chat history from Slack to LangChain. It iterates through each message and adds it to 
    the LangChain history based on the role of the message sender.

    Parameters:
    message (list): A list of messages from the chat history.

    Returns:
    msgs (ChatMessageHistory): The chat history in LangChain format.
    """
    msgs = ChatMessageHistory()
    for m in message:
        if m.get('role') == 'system':
            pass
        elif m.get('role') == 'user':
            msgs.add_user_message(m.get('content'))
        elif m.get('role') == 'assistant':
            msgs.add_ai_message(m.get('content'))
    return msgs


def search_and_chat(messages, text):
    """
    This function loads Slack chat history into LangChain memory, initializes a ChatOpenAI instance, and sets up a 
    conversational chat agent with DuckDuckGo search results. It then executes the agent with the given text and 
    returns the output.

    Parameters:
    messages (list): A list of messages from Slack chat history.
    text (str): The text to be processed by the chat agent.

    Returns:
    str: The output from the chat agent.
    """
    msgs = copy_history_to_langchain(messages)
    memory = ConversationBufferMemory(
        chat_memory=msgs, return_messages=True, memory_key="chat_history", output_key="output"
    )
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k", openai_api_key=OPENAI_API_KEY, streaming=True)
    tools = [DuckDuckGoSearchResults(name="Search")]
    chat_agent = ConversationalChatAgent.from_llm_and_tools(llm=llm, 
                                                            tools=tools, 
                                                            verbose=DEBUG
                                                            )
    executor = AgentExecutor.from_agent_and_tools(
        agent=chat_agent,
        tools=tools,
        memory=memory,
        return_intermediate_steps=True,
        handle_parsing_errors=True,
    )    
    st_cb = StdOutCallbackHandler()
    response = executor(text, callbacks=[st_cb])
    return response["output"]


def summarize_chain(docs, app, channel_id, reply_message_ts):
    """
    This function runs a LangChain summarization chain on a set of documents. It initializes a ChatOpenAI 
    instance with a fast model and large context window, loads a summarization chain with specific prompts, 
    runs the chain on the documents, and returns the result.

    Parameters:
    docs (list): The documents to be summarized.
    app (object): The Slack application object.
    channel_id (str): The ID of the channel where the chat is happening.
    reply_message_ts (str): The timestamp of the message to which the bot is replying.
    
    Returns:
    result (str): The summarized result.
    """
    import openai as OAI
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-16k", openai_api_key=OPENAI_API_KEY)
    PROMPT = CONCISE_SUMMARY_PROMPT
    try:
        chain = load_summarize_chain(llm, 
                                     chain_type="stuff", 
                                     prompt=CONCISE_SUMMARY_COMBINE_PROMPT, 
                                     verbose=DEBUG
                                     )
        result = chain.run(docs)
    # except openai.error.InvalidRequestError as e:
    except Exception as e:
        warn = "Document length exceeded model capacity. Changing strategy - please be patient"
        logger.warning(warn)
        update_chat(app, channel_id, reply_message_ts, warn)
        # chain = load_summarize_chain(llm, chain_type="map_reduce", map_prompt=PROMPT, combine_prompt=PROMPT)
        chain = load_summarize_chain(llm, 
                                     chain_type="map_reduce", 
                                     map_prompt=CONCISE_SUMMARY_MAP_PROMPT, 
                                     combine_prompt=CONCISE_SUMMARY_COMBINE_PROMPT, 
                                     verbose=DEBUG
                                     )
        result = chain.run(docs)
    return result

def summarize_web_page(url, app="", channel_id="", thread_ts="", reply_message_ts=""):
    """
    This function summarizes the content of a web page. It creates a file handler using the OpenAI API key, reads the 
    web page content, and then summarizes it.

    Parameters:
    url (str): The URL of the web page to be summarized.
    app (object): The Slack application object.
    channel_id (str): The ID of the channel where the chat is happening.
    reply_message_ts (str): The timestamp of the message to which the bot is replying.    

    Returns:
    str: The summarized content of the web page.
    """
    # handler = create_file_handler(url, OPENAI_API_KEY, SLACK_BOT_TOKEN, webpage=True)
    handler = register_file(url, channel_id, thread_ts)
    docs = handler.read_file(url)
    return summarize_chain(docs, app, channel_id, reply_message_ts)
    
# Throw doc to a summarize chain
def summarize_file(file, app, channel_id, thread_ts, reply_message_ts):
    """
    This function summarizes the content of a file. It creates a file handler using the OpenAI API key, reads the file 
    from a private URL using the Slack bot token, and then summarizes the document content.

    Parameters:
    file (dict): A dictionary containing file information.
    app (object): The application object.
    channel_id (str): The ID of the channel where the chat is happening.
    thread_ts (str): The timestamp of the thread where the file is located.
    reply_message_ts (str): The timestamp of the message to which the bot is replying.    

    Returns:
    result (str): The summarized content of the file.
    """
    f = fileRegistry.get_files(file, channel_id, thread_ts)
    handler = f[0].get('handler')
    filepath = handler.download_local_file()
    handler.instantiate_loader(filepath)
    documents = handler.loader.load()
    result = summarize_chain(documents, app, channel_id, reply_message_ts)
    handler.delete_local_file(filepath)
    return result

def register_file(file, channel_id, thread_ts):
    """
    This function registers a file with the system. It creates a file handler using the OpenAI API key, reads the file 
    from a private URL using the Slack bot token, and loads the document into a ChatWithDoc object. The file is then added to the 
    file registry with its name, channel ID, thread timestamp, file ID, private URL, handler, and chat object.

    Parameters:
    file (dict): A dictionary containing file information.
    channel_id (str): The ID of the channel where the file is located.
    thread_ts (str): The timestamp of the thread where the file is located.

    Returns:
    None
    """
    # file = {'name': file, 'id': file, 'url_private': file}
    handler = create_file_handler(file, OPENAI_API_KEY, SLACK_BOT_TOKEN)
    if 'WebHandler' in str(type(handler)):
        # file = {'name': file, 'id': file, 'url_private': file}
        # fileRegistry.add_file(file, channel_id, thread_ts, file, file, handler)
        handler.load_split_store()
        # fileRegistry.add_file(file.get('name'), channel_id, thread_ts, file.get('id'), file.get('url_private'), handler)
        fileRegistry.add_file(filename=file, 
                              channel_id=channel_id, 
                              thread_ts=thread_ts, 
                              file_id=file, 
                              url_private=file, 
                              handler=handler)
    else:
        handler.download_and_store()
        fileRegistry.add_file(filename=file.get('name'), 
                              channel_id=channel_id, 
                              thread_ts=thread_ts, 
                              file_id=file.get('id'), 
                              url_private=file.get('url_private'), 
                              handler=handler)
    return handler

def doc_q_and_a(file, question, app, channel_id, thread_ts, reply_message_ts):
    """
    This function answers questions about a file.
    
    Parameters:
    file (str): The name of the file to retrieve.
    channel_id (str): The ID of the Slack channel where the file was uploaded.
    thread_ts (str): The timestamp of the Slack thread where the file was uploaded.
    question (str): The question to be answered.
    
    Returns:
    response (str): The response from the RetrievalQA run method.
    
    Note: This function uses the OpenAI API and requires the OPENAI_API_KEY to be set.
    """
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", openai_api_key=OPENAI_API_KEY)
    f = fileRegistry.get_files(file, channel_id, thread_ts)
    # db = f[0].get('chat').db
    handler = f[0].get('handler')
    db = handler.db
    # db = f[0].get('handler').db
    if 'WebHandler' in str(type(handler)):
        search_kwargs={"filter": {"filename":file}, 'score_threshold': 0.3}
    else:
        search_kwargs={"filter": {"filename": file.split('/')[-1]}, 'score_threshold': 0.3}
    retriever = VectorStoreRetriever(vectorstore=db, search_kwargs=search_kwargs)
    qa = RetrievalQA.from_chain_type(llm=llm, 
                                     chain_type="stuff", 
                                     retriever=retriever, 
                                     return_source_documents = True, 
                                     verbose=DEBUG
                                     )
    response = qa({'query': question})
    response = response.get('result')
    # response = qa(question).get('result')
    # add some reponse check logic here
    truefalse = check_response(question, response)
    
    if bool(truefalse.lower() == 'false'):
        update_chat(app, channel_id, reply_message_ts, "I didn't get a result for that question, let me make some tweaks and try again")
        rf = RagFusion(OPENAI_API_KEY, db)
        question_variants = rf.generate_question_variants(question)
        results_docs = {}
        for q in question_variants:
            if q:
                results_docs[q] = rf.db_lookup(q)
        reranked_results = rf.reciprocal_rank_fusion(results_docs)  
        revised_question = list(reranked_results.keys())[0]
        top_result_docs = results_docs.get(list(reranked_results.keys())[0])
        top_docs = [doc for doc, _ in top_result_docs]
        # from langchain.chains.summarize import load_summarize_chain
        llm = ChatOpenAI(model_name='gpt-3.5-turbo-16k', openai_api_key=OPENAI_API_KEY, streaming=False)
        chain = load_summarize_chain(llm, 
                                    chain_type="stuff", 
                                    verbose=DEBUG
                                    )
        output_summary = chain.run(top_docs)
        # if check_response(revised_question, output_summary):
        #     output = ""
        #     cnt = 1
        #     for doc, _ in top_result_docs:
        #         output += f"{cnt}. {doc.metadata['filename']}, Page: {doc.metadata['page']}\n"
        #         cnt += 1

            # print(output)
            # response = f"This revised version of your question got an answer: \n{revised_question}\n\n{output_summary}\n\nSources:\n{output}"
        response = f"This revised version of your question got an answer: \n{revised_question}\n\n{output_summary}"

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{response}"
                # "text": f"{response.get('result')}"
            }
        }
    ]
    return blocks

def check_response(question, answer):
  system_template = """You review a question and answer and make a true or false determination of whether the question was answered adequately.
  Any responses such as 'The given context does not provide information...' or 'I dont know' are considered inadequate responses. You can only return 
  either True or False. No other text is acceptable.

  Examples:
  Question: Does CoVe improve the correctness of the overall response?
  Answer: The given context does not provide information about whether CoVe improves the correctness of the overall response.
  Response: False

  Question: Can CoVe enhance the accuracy of the overall response?
  Answer: The study introduces the Chain-of-Verification (CoVe) method to reduce hallucinations in large language models. Experiments show that CoVe decreases hallucinations across various tasks, including list-based questions, closed book QA, and longform text generation. The factored and 2-step versions of CoVe perform better than the joint version. The study also compares CoVe with other baselines and shows that it outperforms them in reducing hallucinations and improving precision. However, CoVe does not completely eliminate hallucinations and is limited by the capabilities of the base language model.
  Response: True

  """

  # create a prompt template for a System role
  system_message_prompt_template = SystemMessagePromptTemplate.from_template(
      system_template)

  # create a string template for a Human role with input variables
  human_template = "{question} {answer}"

  # create a prompt template for a Human role
  human_message_prompt_template = HumanMessagePromptTemplate.from_template(human_template)

  # create chat prompt template 
  chat_prompt_template = ChatPromptTemplate.from_messages(
      [system_message_prompt_template, human_message_prompt_template])

  # Create chat prompt
  final_prompt = chat_prompt_template.format_prompt(question=question, answer=answer).to_messages()

  llm = ChatOpenAI(model_name='gpt-3.5-turbo', openai_api_key=OPENAI_API_KEY, streaming=False)
  response_string = llm(final_prompt)
  return(response_string.content)