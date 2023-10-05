
# Borrowed heavily from 
# https://learn.deeplearning.ai/chatgpt-building-system 
# https://github.com/alex000kim/slack-gpt-bot

import os
import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from pprint import pprint
from src.logger_config import get_logger
import json

from localsrc.utils import (N_CHUNKS_TO_CONCAT_BEFORE_UPDATING, OPENAI_API_KEY,
                   SLACK_APP_TOKEN, SLACK_BOT_TOKEN, WAIT_MESSAGE,
                   MAX_TOKENS, DEBUG, prompt, 
                   get_slack_thread, set_prompt_for_user_and_channel, generate_image,
                   num_tokens_from_messages, process_conversation_history,
                   update_chat, moderate_messages, get_completion_from_messages,
                   prepare_payload, get_conversation_history, process_message, search_and_chat,
                   summarize_web_page, summarize_file)  # added imports here

# Configure logging
logger = get_logger(__name__)

# Set the Slack App bot token
app = App(token=SLACK_BOT_TOKEN)

### SLACK EVENT HANDLERS ###
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
# @app.message("hello")
# def message_hello(message, say):
#     say(f"Hey there <@{message.get('user')}>!")

# Process direct messages
@app.event("message")
def handle_message_events(body, context, logger):
    if is_it_bot(body):
        return
    # event_router(body, context)
    # logger.debug(body)
    event = body.get('event')
    if event is None:
        logger.error("Expected event object in Slack body")
        logger.info(body)
        return False
    
    # Do nothing if this is a post by the bot
    if is_it_bot(body):
        logger.debug('Is bot message')
        return

    bot_user_id = body.get('authorizations')[0]['user_id'] if 'authorizations' in body else context.get('bot_user_id')
    channel_id = event.get('channel')

    # If the event is from a DM, go ahead and process
    if channel_id.startswith('D'):
        pass
    # If it's an app_mention, this will be handled by Slack's @app.event("app_mention") listener. 
    # Return so we don't process twice
    # elif f"<@{bot_user_id}>" in event.get('text'):
    elif 'text' in event and f"<@{bot_user_id}>" in event.get('text'):        
        return
    # If it's neither a DM nor an app_mention, then this is none of our business. Return immediately
    else:
        return
    logger.debug("Processing DM message")
    # Check if the event has a subtype
    if 'subtype' in body['event']:
        # If the subtype is 'file_share', do something
        if body['event']['subtype'] == 'file_share':
            ## TODO: CHANGE THIS TO REGISTER FILE AND WAIT FOR USER COMMAND TO LOAD
            deal_with_file(body, context, logger)
    else:
        process_event(body, context)

# Process app mention events
@app.event("app_mention")
def command_handler(body, context):
    # event_router(body, context)
    if 'subtype' in body['event']:
        # If the subtype is 'file_share', do something
        if body['event']['subtype'] == 'file_share':
            deal_with_file(body, context, logger)
    else:
        process_event(body, context)

# Checks to see if a post is from the W'kid Smaaht bot. 
# If so, we don't process
def is_it_bot(body):
    if 'message' in body:
        b = body.get('message[bot_id]') 
        if b is not None:
            return True
    else:
        return False

# Processes file upload
def deal_with_file(body, context, logger):
    channel_id=body['event']['channel']
    thread_id=body['event']['ts']
    slack_resp = app.client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_id,
        text="Ah, I see you uploaded a file. Give me a minute to summarize it for you."
    )
    reply_message_ts = slack_resp.get('message', {}).get('ts')    
    response = ''
    try:
        response = summarize_file(app, body, context)
    except ValueError as e:
        response = f"Sorry, I can't process files of type: {e}"

    update_chat(app, channel_id, reply_message_ts, response)  

# def chat_with_file(body, context, logger):
#     channel_id=body['event']['channel']
#     thread_id=body['event']['ts']
#     slack_resp = app.client.chat_postMessage(
#         channel=channel_id,
#         thread_ts=thread_id,
#         text="Ah, I see you uploaded a file. I'll load it so you can ask questions."
#     )
#     reply_message_ts = slack_resp.get('message', {}).get('ts')    
#     response = ''
#     try:
#         response = chat_with_doc(app, body, context)
#     except ValueError as e:
#         response = f"Sorry, I can't process files of type: {e}"

    update_chat(app, channel_id, reply_message_ts, response) 

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
            text=f"Something went wrong."
        )
        return
    
    if (command_text==WAIT_MESSAGE) or (command_text.startswith("/")):
        # No processing needed if the message was generated by this bot or is a Slack slash command
        return

    if command_text == '':
        app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=f"How can I help you today?"
        )         
        return

    slack_resp = app.client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=WAIT_MESSAGE
    )
    
    reply_message_ts = slack_resp.get('message', {}).get('ts')
    conversation_history = get_conversation_history(app, channel_id, thread_ts)
    if conversation_history is None:
        slack_resp = app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text="Sorry. Slack had a problem processing this message"
        )
        return
    
    messages = process_conversation_history(conversation_history, bot_user_id, channel_id, thread_ts, user_id)
    num_tokens = num_tokens_from_messages(messages)

    if command_text.startswith(":pix "):
        image_text = command_text.replace(":pix ", "").strip()
        if image_text:
            update_chat(app, channel_id, reply_message_ts, "Generating your image...just a sec")
            try:
                response = generate_image(image_text)   
            except Exception as e:
                logger.error(response)
                update_chat(app, channel_id, reply_message_ts, "Sorry. Error generating image: {e}")
                return
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=".", # Used to suppress Slack warnings about not including text in the post
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
            update_chat(app, channel_id, reply_message_ts, "You need to provide some text for me to generate an image. For example, A cat eating ice cream.")
    elif command_text.startswith(":snc "):
        update_chat(app, channel_id, reply_message_ts, "Let me do a bit of research and I'll get right back to you.")
        text = command_text.replace(":snc ", "").strip()
        response = search_and_chat(messages, text)
        update_chat(app, channel_id, reply_message_ts, response)
    elif command_text.startswith(":websum "):
        update_chat(app, channel_id, reply_message_ts, "I'll try to summarize that page. This may take a minute (literally).")
        url = command_text.replace(":websum ", "").split("|")[0].replace("<","").replace(">","").strip()
        logger.info("Dude! WTF??" + url)
        response = summarize_web_page(url)
        update_chat(app, channel_id, reply_message_ts, response)      
    else:
        try:
            openai_response = get_completion_from_messages(messages)
            logger.debug("DEBUG: Got response from OpenAI: ", type(openai_response))
            chunk_n_update(openai_response, app, channel_id, reply_message_ts)
        except Exception as e:
            logger.error(f"Error: {e}")
            app.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=f"I can't provide a response. Encountered an error:\n`\n{e}\n`"
            )
    logger.debug("DEBUG: end command_handler")
    
def chunk_n_update(openai_response, app, channel_id, reply_message_ts):
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

# Start your app
if __name__ == "__main__":
    logger.debug("Starting app")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
