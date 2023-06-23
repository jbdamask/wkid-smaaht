# Borrowed heavily from 
# https://learn.deeplearning.ai/chatgpt-building-system 
# https://github.com/alex000kim/slack-gpt-bot


import os
# import openai
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from utils import (N_CHUNKS_TO_CONCAT_BEFORE_UPDATING, OPENAI_API_KEY,
                   SLACK_APP_TOKEN, SLACK_BOT_TOKEN, WAIT_MESSAGE,
                   MAX_TOKENS,
                   num_tokens_from_messages, process_conversation_history,
                   update_chat, moderate_messages, get_completion_from_messages)

app = App(token=SLACK_BOT_TOKEN)

def get_conversation_history(channel_id, thread_ts):
    return app.client.conversations_replies(
        channel=channel_id,
        ts=thread_ts,
        inclusive=True
    )

# Listens to incoming messages that contain "hello"
# To learn available listener arguments,
# visit https://slack.dev/bolt-python/api-docs/slack_bolt/kwargs_injection/args.html
@app.message("hello")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(f"Hey there <@{message['user']}>! :wave:")

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

# Listens for app invokation
@app.event("app_mention")
def command_handler(body, context):
    try:
        channel_id = body['event']['channel']
        thread_ts = body['event'].get('thread_ts', body['event']['ts'])
        bot_user_id = context['bot_user_id']
        slack_resp = app.client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts,
            text=WAIT_MESSAGE
        )
        reply_message_ts = slack_resp['message']['ts']
        conversation_history = get_conversation_history(channel_id, thread_ts)
        messages = process_conversation_history(conversation_history, bot_user_id)
        
        # if not moderate_messages(messages):
        #     return

        # if not moderate_messages(messages):
        #     app.client.chat_postMessage(
        #         channel=channel_id,
        #         thread_ts=thread_ts,
        #         text="This message cannot be processed due to OpenAI content moderation policies."
        #     )
        #     return            

        num_tokens = num_tokens_from_messages(messages)
        print(f"Number of tokens: {num_tokens}")

        # TODO: Add a moderation step here

        openai_response = get_completion_from_messages(
            messages
        )

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

# def get_completion_from_messages(messages, 
#                                 #  model="gpt-3.5-turbo", 
#                                  model="gpt-4",
#                                  temperature=0, 
#                                  max_tokens=MAX_TOKENS,
#                                  stream=True
#                                  ):
#     response = openai.ChatCompletion.create(
#         model=model,
#         messages=messages,
#         temperature=temperature, 
#         stream=True
#     )
#     return response

# Start your app
if __name__ == "__main__":
    print("Starting app")
    # print("SLACK_BOT_TOKEN: ", SLACK_BOT_TOKEN)
    # print("OPENAI_API_KEY: ", OPENAI_API_KEY)
    # print("SLACK_APP_TOKEN: ", SLACK_APP_TOKEN)
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
    # SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
