
# Borrowed heavily from 
# https://learn.deeplearning.ai/chatgpt-building-system 
# https://github.com/alex000kim/slack-gpt-bot

import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pprint import pprint
from logger_config import get_logger
import json

from utils import (N_CHUNKS_TO_CONCAT_BEFORE_UPDATING, OPENAI_API_KEY,
                   SLACK_APP_TOKEN, SLACK_BOT_TOKEN, WAIT_MESSAGE,
                   MAX_TOKENS, DEBUG, prompt, 
                   get_slack_thread, set_prompt_for_user_and_channel, generate_image,
                   num_tokens_from_messages, process_conversation_history,
                   update_chat, moderate_messages, get_completion_from_messages,
                   get_conversation_history, process_message)  # added imports here

# Configure logging
logger = get_logger(__name__)

# Set the Slack App bot token
app = App(token=SLACK_BOT_TOKEN)

# Slack slash command to return list of all available system prompts
@app.command("/prompts")
def list_prompts(ack, respond):
    ack()
    p = prompt.list_prompts()
    respond(f"{', '.join(p)}")

# Slack slash command to return message associated with a particular system prompt
@app.command("/get_prompt")
def show_prompt(ack, respond, command):
    ack()
    try:
        respond(f"{prompt.get_prompt(command.get('text'))}")
    except Exception as e:
        respond(f"No such system prompt exsists")

# Slack slash command to change system message. This lets users steer Wkid Smaaht at runtime
@app.command("/set_prompt")
def set_prompt(ack, respond, command):
    ack()
    logger.info(f"{command.get('user_id')} : {command.get('user_name')}")
    if(prompt.get_prompt(command.get('text'))) is not None:
        set_prompt_for_user_and_channel(command.get('user_id'), command.get('channel_id'), command.get('text'))
        respond(f"Ok, from now on I'll be {command.get('text')}")
    else:
        respond(f"{command.get('text')} is not a valid prompt key. Type /prompts to see a list of available system prompts")

@app.command("/generate_image")
def make_image(ack, respond, command):
    ack({ "response_type": "in_channel", "text": "Command deprecated. Just type @W'kid Smaaht :pix <your text> instead"})

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("hello")
def message_hello(message, say):
    say(f"Hey there <@{message.get('user')}>!")

# Process DMs
@app.event("message")
def handle_message_events(body, context, logger):
    logger.info("message")
    event = body.get('event')
    if event is None:
        logger.error("Expected event object in Slack body")
        logger.info(body)
        return False
    bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context.get('bot_user_id')
    channel_id = event.get('channel')

    # If the event is from a DM, go ahead and process
    if channel_id.startswith('D'):
        pass

    # If it's an app_mention, this will be handled by Slack's @app.event("app_mention") listener. 
    # Return so we don't process twice
    elif f"<@{bot_user_id}>" in event.get('text'):
        return
    
    # If it's neither a DM nor an app_mention, then this is none of our business. Return immediately
    else:
        return
    
    logger.debug("Processing DM message")
    process_event(body, context)

# Process app mention events
@app.event("app_mention")
def command_handler(body, context):
    logger.debug(body)
    process_event(body, context)

# # Check it oot, as my Canadian friends say
# def is_valid_message_body(body, context):
#     # if not ('channel' in body.get('event')) or not ('text' in body.get('event')):
#     #     return False
#     channel_id = None
#     body_text = None
#     event = body.get('event')
#     if event is None:
#         return False

#     channel_id = event.get('channel')
#     body_text = event.get('text')

#     if (channel_id is None) or (body_text is None):
#         return False

#     # If DM keep going, otherwise grab bot user id
#     if not event.get('channel_type') or event.get('channel_type') != "im":
#         pass
#     # if ('channel_type' in body.get(\'event\')) and (body.get(\'event\')['channel_type'] == 'im'):
#     #     pass
#     else:
#         bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context.get('bot_user_id')
#         # If we're not a DM and the bot user wasn't called out in the text, but we're here, something's amiss
#         # It seems like this should never happen but I've seen it
#         if not channel_id.startswith('D'):
#             # if f"<@{bot_user_id}>" not in body.get(\'event\')['text']:
#             if f"<@{bot_user_id}>" not in event.get('text'):
#                 return False

#     if (body_text==WAIT_MESSAGE) or (body_text.startswith("/")):
#         # or (body_text.startswith("Got your request!")):    <- Not sure why I had this. It's nearly a repeat of WAIT_MESSAGE
#         # Return False if this was a slash command, auto response.
#         # This prevents W'kid Smaaht from thinking these
#         return False

#     return True

# Where's the beef? Oh, it's here
# def extract_command_text(event, bot_user_id):
#     if f"<@{bot_user_id}" in event.get('text'):
#         command_text = event.get('text').split(f"<@{bot_user_id}>")[1].strip()
#     else:
#         command_text = event.get('text')
#     return command_text

# Where's the beef? Oh, it's here
def prepare_payload(body, context):
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


# Where the magic happens
def process_event(body, context):
    logger.info("process_event() body object:)")
    logger.info(body)
    logger.debug("process_event() context object:)")
    logger.debug(context)
    event = body.get('event')
    if event is None:
        return False
    bot_user_id, channel_id, thread_ts, user_id, command_text = prepare_payload(body, context)
    if any(var is None for var in [bot_user_id, channel_id, thread_ts, user_id, command_text]):
        logger.error("process_event problem. Check body object")
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            # text=f"Generated image: {response}"
            text=f"Something went wrong."
        )
        return
    
    if (command_text==WAIT_MESSAGE) or (command_text.startswith("/")):
        # Indicates the message received was either generated by this bot or is a Slack slash command
        return


    # command_text = extract_command_text(event, bot_user_id)
    if command_text == '':
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            # text=f"Generated image: {response}"
            text=f"How can I help you today?"
        )         
        return

    if command_text.startswith(":pix "):
        image_text = command_text.replace(":pix ", "").strip()
        if image_text:
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                # text=f"Generated image: {response}"
                text=f"Generating your image...just a sec"
            )              
            try:
                response = generate_image(image_text)   
            except Exception as e:
                logger.error(response)
                app.client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=f"Error generating image: {e}"
                )
                return
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=".", # Used to suppress Slack warnings about not inclding text in the post
                blocks=[
                    {
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": image_text,
                            "emoji": True
                        },
                        "image_url": response['blocks'][0]['image_url'],
                        "alt_text": image_text
                    }
                ]                
            )
        else:
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text="No text provided for image generation."
            )
        return

    # handle_message(body, context, bot_user_id, channel_id, thread_ts, user_id)
    logger.debug("DEBUG: command_handler - new message")
    logger.debug("channel_id: ", channel_id)   
    logger.debug("thread_ts: ", thread_ts)   
    logger.debug("user_id: ", user_id)
    logger.debug("bot_user_id: ", bot_user_id)
    logger.debug("DEBUG: app.client.chat_postMessage")

    slack_resp = app.client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=WAIT_MESSAGE
    )
    # reply_message_ts = slack_resp.get('message')['ts']
    reply_message_ts = slack_resp.get('message', {}).get('ts')
    conversation_history = get_conversation_history(app, channel_id, thread_ts)
    if conversation_history is None:
        slack_resp = app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Sorry. Slack had a problem processing this message"
        )
        return
    logger.debug("got conversation history")
    messages = process_conversation_history(conversation_history, bot_user_id, channel_id, thread_ts, user_id)
    num_tokens = num_tokens_from_messages(messages)

    try:
        openai_response = get_completion_from_messages(messages)

        logger.debug("DEBUG: Got response from OpenAI: ", type(openai_response))

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
        response_json = {"response_text": response_text}
        logger.info(json.dumps(response_json))
        
    except Exception as e:
        logger.error(f"Error: {e}")
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`"
        )
        
    logger.debug("DEBUG: end command_handler")    


# Start your app
if __name__ == "__main__":
    logger.debug("Starting app")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
