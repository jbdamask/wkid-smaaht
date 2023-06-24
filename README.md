# ChatAWS Slack

## Description

ChatAWS Slack is a GPT-backed chatbot that integrates with Slack. It's like having your own AWS expert available 24/7. Forget about Googling, reading AWS documentation or spelunking old Stack Overflow posts, just ask @ChatAWS!

## Features

- GPT-powered: Get intelligent, human-like responses thanks to GPT-4
- Serverless: Runs on AWS Fargate. This means it's always on and there's no infrastructure to manage
- Easy to use: Just type @ChatAWS in Slack

## Examples
![CLI commands](/images/s3-search.png)

## Prerequisites

- Slack
    - Slack workspace with administrator or owner permissions

- OpenAI
    - OpenAI account with API access
    - OpenAI API key

- AWS
    - AWS Account configured with a VPC and private subnet
    - AWS IAM user with administrator permissions (you'll need the API key)
    - AWS CLI installed and configured with your AWS API key

- Docker
    - Docker installed and running locally

- Python 3.10 or greater


## Installation & Configuration

There are three major parts to this application that need to be configured in the following order:

### 1. Slack app creation
- Login to your Slack workspace
- Follow Slack's [Basic app setup guide](https://api.slack.com/authentication/basics)
    - Click the Create a new Slack app button on the page above
- Specific configuration for this app:
    - App token:
        - Click, Generate Tokens and Scopes
            - Name: ChatAWSSocketToken
            - Scope: connections:write
        - Save the token. You'll need it later
    - Bot token:
        - Navigate to Oauth & Permissions. Add the following Scopes:
            - app_mentions:read
            - channels:history
            - channels:read
            - chat:write
            - groups:history
            - groups:read
            - im:history
            - im:read
            - links:read
            - mpim:history
            - mpim:read
            - mpim:write
        - Click Request to Install 
        - After the app has been approved by your workspace administrator, click the Install to Workspace button and click Allow 

            <img src="images/slack-app-install.png" alt="Allow" width="300"/>
        - You can now get your bot user access token under the Oauth & Perissions sidebar. Save it in a safe place (**do not put this in source control**)
- Next, you need to invite your app to a channel. Go to a channel of your choice and type `/invite`

    <img src="images/slack-app-dev.png" alt="Allow" width="400"/>
- Search for ChatAWS and click Add
- Verify you can call it by typing `@ChatAWS`. It won't do anything yet.

### 2. Code configuration
*Note these instructions are for a Mac. You may have to tweak if running on Windows or other systems*
- Download latest release or clone this repo into a local folder with a python virtual environment
    ```
    cd ~/code
    git clone https://gitlab.com/flagship-informatics/flagship-digital/aws/chataws-slack.git
    ```
- It's a good idea to try your application locally, which can be done using the handy localapp.py script provided:
    ```
    # Create virtual Python environment to isolate this project from your global Python
    cd chataws-slack
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

    ```

- Follow this step if you're comfortable with bash scripts, otherwise you can create these secrets in  AWS Secrets Manager using their GUI.
    - Make bash script executable 
        ```
        chmod +x scripts/create_secrets.sh
        ```

### 3. AWS Fargate configuration

## FAQ
- Does OpenAI use my input? Per [OpenAI's API Data Usage policy from May 2023](https://openai.com/policies/api-data-usage-policies) OpenAI will not use your conversations to train their models

## How I Built This
This project leverages the [Bolt-Python](https://slack.dev/bolt-python/tutorial/getting-started) framework for building Slack applications, and uses code from the [Slack GPT Bot](https://github.com/alex000kim/slack-gpt-bot) project and the deeplearning.ai course, [Building Systems with the ChatGPT API](https://learn.deeplearning.ai/chatgpt-building-system/lesson/1/introduction).