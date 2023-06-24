#!/bin/bash

read -p "Enter Slack Bot Token: " slack_bot_token
read -p "Enter Slack App Token: " slack_app_token
read -p "Enter OpenAI API Key: " openai_api_key
read -p "Enter Region: " region

aws secretsmanager create-secret --name "SLACK_BOT_TOKEN_CHATAWS3" --secret-string "$slack_bot_token" --region "$region"

aws secretsmanager create-secret --name "SLACK_APP_TOKEN_CHATAWS3" --secret-string "$slack_app_token" --region "$region"

aws secretsmanager create-secret --name "OPENAI_API_KEY_CHATAWS3" --secret-string "$openai_api_key" --region "$region"



# aws secretsmanager create-secret --name "SLACK_BOT_TOKEN_CHATAWS" --secret-string "your-secret-value" --region "your-region"

# aws secretsmanager create-secret --name "SLACK_APP_TOKEN_CHATAWS" --secret-string "your-secret-value" --region "your-region"

# aws secretsmanager create-secret --name "OPENAI_API_KEY_CHATAWS" --secret-string "your-secret-value" --region "your-region"
