# Use this script for local testing
# python localapp.py

# Borrowed heavily from 
# https://learn.deeplearning.ai/chatgpt-building-system 
# https://github.com/alex000kim/slack-gpt-bot

import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from utils import (N_CHUNKS_TO_CONCAT_BEFORE_UPDATING, OPENAI_API_KEY,
                   SLACK_APP_TOKEN, SLACK_BOT_TOKEN, WAIT_MESSAGE,
                   MAX_TOKENS, DEBUG, prompt, 
                   get_slack_thread, set_prompt_for_user_and_channel,
                   num_tokens_from_messages, process_conversation_history,
                   update_chat, moderate_messages, get_completion_from_messages)

app = App(token=SLACK_BOT_TOKEN)

def get_conversation_history(channel_id, thread_ts):
    history = app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )
    # if DEBUG:
        # print(type(history))
        # print(history)
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

@app.command("/prompts")
def list_prompts(ack, respond, command):
    ack()
    p = prompt.list_prompts()
    respond(f"{', '.join(p)}")
    # respond(f"{command['text']}")

@app.command("/get_prompt")
def show_prompt(ack, respond, command):
    ack()
    try:
        respond(f"{prompt.get_prompt(command['text'])}")
    except Exception as e:
        respond(f"No such system prompt exsists")

@app.command("/set_prompt")
def set_prompt(ack, respond, command):
    ack()
    # if DEBUG:
        # print(f"{command['user_id']} : {command['user_name']}")
    if(prompt.get_prompt(command['text'])) is not None:
        set_prompt_for_user_and_channel(command['user_id'], command['channel_id'], command['text'])
        respond(f"Ok, from now on I'll be {command['text']}")
    else:
        respond(f"{command['text']} is not a valid prompt key. Type /prompts to see a list of available system prompts")

# Listens for app invokation
@app.event("app_mention")
def command_handler(body, context):
    if DEBUG:
        print(body)
        print(context)
    # if DEBUG:
    #     print("DEBUG: command_handler - new message")
    channel_id = body['event']['channel']
    thread_ts = body['event'].get('thread_ts', body['event']['ts'])
    bot_user_id = context['bot_user_id']
    user_id = context['user_id']

    if DEBUG:
        print("channel_id: ", channel_id)   
        print("thread_ts: ", thread_ts)   
        print("bot_user_id: ", bot_user_id)
        print("user_id: ", user_id)
    # if DEBUG:
    #     print("DEBUG: app.client.chat_postMessage")          
    slack_resp = app.client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=WAIT_MESSAGE
    )
    reply_message_ts = slack_resp['message']['ts']               
    conversation_history = get_conversation_history(channel_id, thread_ts)
    print("got conversation history")
    messages = process_conversation_history(conversation_history, bot_user_id, channel_id, thread_ts, user_id)
    num_tokens = num_tokens_from_messages(messages)
    try:
        openai_response = get_completion_from_messages(
            messages
        )
        # if DEBUG:
        #     print("DEBUG: Got response from OpenAI: ", type(openai_response))
            
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
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
