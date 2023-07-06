# Use this script for local testing
# python localapp.py

# Borrowed heavily from 
# https://learn.deeplearning.ai/chatgpt-building-system 
# https://github.com/alex000kim/slack-gpt-bot

import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pprint import pprint
from utils import (N_CHUNKS_TO_CONCAT_BEFORE_UPDATING, OPENAI_API_KEY,
                   SLACK_APP_TOKEN, SLACK_BOT_TOKEN, WAIT_MESSAGE,
                   MAX_TOKENS, DEBUG, prompt, 
                   get_slack_thread, set_prompt_for_user_and_channel, generate_image,
                   num_tokens_from_messages, process_conversation_history,
                   update_chat, moderate_messages, get_completion_from_messages)

app = App(token=SLACK_BOT_TOKEN)

def get_conversation_history(channel_id, thread_ts):
    history = app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )
    if DEBUG:
        print(type(history))
        pprint(history)
    return history

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    print("hello command")
    say(f"Hey there <@{message['user']}>!")

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

@app.command("/generate_image")
def make_image(ack, respond, command):
    ack({ "response_type": "in_channel", "text": "Got your request! Generating image..."})
    if(command['text']) is not None:
        r = generate_image(command['text'])
        respond(r)
    else:
        respond(f"{command['text']} caused a problem")


# Process DMs
@app.event("message")
def handle_message_events(body, context, logger):
    # logger.info(body)
    bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context['bot_user_id']
    channel_id = body['event']['channel']
    # If the event is from a DM, process it as an app_mention
    if channel_id.startswith('D'):
        # your code to handle the message
        print("We got a DM! Process")
        pass
    # If it's an app_mention, process the message
    elif f"<@{bot_user_id}>" in body['event']['text']:
        # your code to handle the mention
        print("We got an app mention! Return!")
        return
    # If it's neither a DM nor an app_mention, return immediately
    else:
        return
    
    print("Processing DM message")
    process_chat(body, context)


# @app.event("message")
@app.event("app_mention")
def command_handler(body, context, say, logger):
    if DEBUG:
        pprint(body)
        # pprint(f"body['event']['text']: {body['event']['text']}")
        # pprint(f"body['event']['blocks'][0]['type']: {body['event']['blocks'][0]['type']}")

    bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context['bot_user_id']
    channel_id = body['event']['channel']
    thread_ts = body['event'].get('thread_ts', body['event']['ts'])
    user_id = body['event'].get('user', context.get('user_id'))

    # If the message is not a DM and doesn't mention the bot, return immediately
    if not channel_id.startswith('D') and f"<@{bot_user_id}>" not in body['event']['text']:
        return

    check_response = body['event']['text']
    if (check_response==WAIT_MESSAGE) or (check_response.startswith("/")) or (check_response.startswith("Got your request!")) or (body['event']['blocks'][0]['type'] == "image"):
        # return immediately if this was a slash command, auto response or image
        return

    # For direct messages, consider all text as the command.
    # For channel messages, only consider the text after the bot's mention as the command.
    # if 'channel_type' in body['event'] and body['event']['channel_type'] == 'im':
    #     command_text = body['event']['text']
    # else:
    #     if 'text' not in body['event'] or f"<@{bot_user_id}>" not in body['event']['text']:
    #         return
    #     command_text = body['event']['text'].split(f"<@{bot_user_id}>")[1].strip()

    # if body['event']['channel_type'] == 'im':
    # Note: channel_type doesn't appear in JSON objects from Slack threads
    if ('channel_type' in body['event']) and (body['event']['channel_type'] == 'im'):
        command_text = body['event']['text']
    else:
        if f"<@{bot_user_id}>" not in body['event']['text']:
            return
        command_text = body['event']['text'].split(f"<@{bot_user_id}>")[1].strip()

    process_chat(body, context)

    # if DEBUG:
    #     print("DEBUG: command_handler - new message")
    #     print("channel_id: ", channel_id)   
    #     print("thread_ts: ", thread_ts)   
    #     print("user_id: ", user_id)
    #     print("bot_user_id: ", bot_user_id)
    #     print("command_text: ", command_text)
    #     print("DEBUG: app.client.chat_postMessage")

    # slack_resp = app.client.chat_postMessage(
    #     channel=channel_id,
    #     thread_ts=thread_ts,
    #     text=WAIT_MESSAGE
    # )
    # reply_message_ts = slack_resp['message']['ts']
    # conversation_history = get_conversation_history(channel_id, thread_ts)
    # print("got conversation history")
    # messages = process_conversation_history(conversation_history, bot_user_id, channel_id, thread_ts, user_id)
    # num_tokens = num_tokens_from_messages(messages)

    # try:
    #     openai_response = get_completion_from_messages(messages)

    #     if DEBUG:
    #         print("DEBUG: Got response from OpenAI: ", type(openai_response))

    #     response_text = ""
    #     ii = 0
    #     for chunk in openai_response:
    #         if chunk.choices[0].delta.get('content'):
    #             ii = ii + 1
    #             response_text += chunk.choices[0].delta.content
    #             if ii > N_CHUNKS_TO_CONCAT_BEFORE_UPDATING:
    #                 update_chat(app, channel_id, reply_message_ts, response_text)
    #                 ii = 0
    #         elif chunk.choices[0].finish_reason == 'stop':
    #             update_chat(app, channel_id, reply_message_ts, response_text)
    # except Exception as e:
    #     print(f"Error: {e}")
    #     app.client.chat_postMessage(
    #         channel=channel_id,
    #         thread_ts=thread_ts,
    #         text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`"
    #     )
        
    if DEBUG:
        print("DEBUG: end command_handler")
        

def process_chat(body, context):
    if DEBUG:
        pprint(body)
        # pprint(f"body['event']['text']: {body['event']['text']}")
        # pprint(f"body['event']['blocks'][0]['type']: {body['event']['blocks'][0]['type']}")

    bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context['bot_user_id']
    channel_id = body['event']['channel']
    thread_ts = body['event'].get('thread_ts', body['event']['ts'])
    user_id = body['event'].get('user', context.get('user_id'))

    # If the message is not a DM and doesn't mention the bot, return immediately
    if not channel_id.startswith('D') and f"<@{bot_user_id}>" not in body['event']['text']:
        return

    check_response = body['event']['text']
    if (check_response==WAIT_MESSAGE) or (check_response.startswith("/")) or (check_response.startswith("Got your request!")) or (body['event']['blocks'][0]['type'] == "image"):
        # return immediately if this was a slash command, auto response or image
        return

    # For direct messages, consider all text as the command.
    # For channel messages, only consider the text after the bot's mention as the command.
    # if 'channel_type' in body['event'] and body['event']['channel_type'] == 'im':
    #     command_text = body['event']['text']
    # else:
    #     if 'text' not in body['event'] or f"<@{bot_user_id}>" not in body['event']['text']:
    #         return
    #     command_text = body['event']['text'].split(f"<@{bot_user_id}>")[1].strip()

    # if body['event']['channel_type'] == 'im':
    # Note: channel_type doesn't appear in JSON objects from Slack threads
    if ('channel_type' in body['event']) and (body['event']['channel_type'] == 'im'):
        command_text = body['event']['text']
    else:
        if f"<@{bot_user_id}>" not in body['event']['text']:
            return
        command_text = body['event']['text'].split(f"<@{bot_user_id}>")[1].strip()

    if DEBUG:
        print("DEBUG: command_handler - new message")
        print("channel_id: ", channel_id)   
        print("thread_ts: ", thread_ts)   
        print("user_id: ", user_id)
        print("bot_user_id: ", bot_user_id)
        print("command_text: ", command_text)
        print("DEBUG: app.client.chat_postMessage")

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
        openai_response = get_completion_from_messages(messages)

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
            text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`"
        )
        
    if DEBUG:
        print("DEBUG: end command_handler")    

# Start your app
if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
