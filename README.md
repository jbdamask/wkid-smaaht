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

- AWS
    - AWS Account
    - AWS administrator permissions
    - AWS CLI

- OpenAI
    - OpenAI account with API access
    - OpenAI API key

- Slack
    - Slack workspace with administrator or owner permissions
    - Slack bot token
    - Slack app token


## Installation

1. Clone this repository.


## FAQ
- Does OpenAI use my input? Per [OpenAI's API Data Usage policy from May 2023](https://openai.com/policies/api-data-usage-policies) OpenAI will not use your conversations to train their models

## How I Built This
This project leverages the [Bolt-Python](https://slack.dev/bolt-python/tutorial/getting-started) framework for building Slack applications, and uses code from the [Slack GPT Bot](https://github.com/alex000kim/slack-gpt-bot) project and the deeplearning.ai course, [Building Systems with the ChatGPT API](https://learn.deeplearning.ai/chatgpt-building-system/lesson/1/introduction).