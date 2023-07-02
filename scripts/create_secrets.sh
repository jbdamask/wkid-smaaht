#!/bin/bash

read -p "Enter Slack Bot Token: " slack_bot_token
read -p "Enter Slack App Token: " slack_app_token
read -p "Enter OpenAI API Key: " openai_api_key
read -p "Enter Region: " region

aws secretsmanager create-secret --name "SLACK_BOT_TOKEN_WKID_SMAAHT" --description "Bot token for Wkid Smaaht Slack app" --secret-string "$slack_bot_token" --region "$region"

aws secretsmanager create-secret --name "SLACK_APP_TOKEN_WKID_SMAAHT" --description "App token for Wkid Smaaht Slack app" --secret-string "$slack_app_token" --region "$region"

aws secretsmanager create-secret --name "OPENAI_API_KEY_WKID_SMAAHT" --description "OpenAI API key for Wkid Smaaht Slack app" --secret-string "$openai_api_key" --region "$region"
