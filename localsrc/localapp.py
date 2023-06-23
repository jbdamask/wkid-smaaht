# Use this script for local testing
# python localapp.py

# Borrowed heavily from 
# https://learn.deeplearning.ai/chatgpt-building-system 
# https://github.com/alex000kim/slack-gpt-bot


import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

from utils import (N_CHUNKS_TO_CONCAT_BEFORE_UPDATING, OPENAI_API_KEY,
                   SLACK_APP_TOKEN, SLACK_BOT_TOKEN, WAIT_MESSAGE,
                   MAX_TOKENS, DEBUG, 
                   num_tokens_from_messages, process_conversation_history,
                   update_chat, moderate_messages, get_completion_from_messages)

app = App(token=SLACK_BOT_TOKEN)

def get_conversation_history(channel_id, thread_ts):
    history = app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )
    print(type(history))
    print(history)
    return history

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    print("hello command")
    say(f"Hey there <@{message['user']}>!")


@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# Listens for app invokation
@app.event("app_mention")
def command_handler(body, context):
    if DEBUG:
        print("DEBUG: command_handler - new message")
    channel_id = body['event']['channel']
    thread_ts = body['event'].get('thread_ts', body['event']['ts'])
    bot_user_id = context['bot_user_id']
    if DEBUG:
        print("channel_id: ", channel_id)   
        print("thread_ts: ", thread_ts)   
        print("bot_user_id: ", bot_user_id)
    if DEBUG:
        print("DEBUG: app.client.chat_postMessage")          
    slack_resp = app.client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=WAIT_MESSAGE
    )
    reply_message_ts = slack_resp['message']['ts']               
    conversation_history = get_conversation_history(channel_id, thread_ts)
    messages = process_conversation_history(conversation_history, bot_user_id)
    num_tokens = num_tokens_from_messages(messages)
    try:
        openai_response = get_completion_from_messages(
            messages
        )
        if DEBUG:
            print("DEBUG: Got response from OpenAI: ", type(openai_response))
            
        response_text = ""
        ii = 0
        for chunk in openai_response:
            if chunk.choices[0].delta.get('content'):
                ii = ii + 1
                response_text += chunk.choices[0].delta.content
                if ii > N_CHUNKS_TO_CONCAT_BEFORE_UPDATING:
                    update_chat(app, channel_id, reply_message_ts, response_text)
                    ii = 0
            elif chunk.choices[0].finish_reason == 'stop':
                update_chat(app, channel_id, reply_message_ts, response_text)
    except Exception as e:
        print(f"Error: {e}")
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`")
    if DEBUG:
        print("DEBUG: end command_handler ")
        
# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
