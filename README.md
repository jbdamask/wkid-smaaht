# W'kid Smaaht <img src="images/wkid_smaaht_web.png" alt="Allow" width="100"/>

## Description

Wait...what?

"Wicked smart" is a phrase you'll hear a lot around Boston. It's our way of saying someone is extremely intelligent. It's like if Albert Einstein, Tom Brady, Ketanji Brown Jackson and HAL 9000 had a baby, that kid would be "wicked smaaht".

W'kid Smaaht Slack brings the power of GPT4 to Slack. It's like having an expert in any topic available 24/7. 

## Features

- GPT-powered: Get intelligent, human-like responses thanks to GPT-4
- Serverless: Runs on AWS Fargate. This means it's always on and there's no infrastructure to manage
- Easy to use: Just invite the app to any Slack channel and type @Wkid Smaaht.

    <img src="images/wkid-smaaht-hello.png" alt="Allow" width="500"/>

- You can also DM as you would any Slack user

    <img src="images/wkid-smaaht-hello-DM.png" alt="Allow" width="500"/>

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
    - Docker installed and running locally. [Docker Desktop](https://www.docker.com/products/docker-desktop/)

- Python 3.10 or greater

- Ability to execute bash shell scripts

- jq
    - See [this gist](https://gist.github.com/magnetikonline/58eb344e724d878345adc8622f72be13) if installing on an Mac M1 with ARM64 chip


## Installation & Configuration

There are three major components to this application: the code, the AWS environment to run it and the Slack app itself. Start by downloading the codebase:

*Note these instructions are for a Mac. You may have to tweak if running on Windows or other systems*
- Download latest release or clone this repo into a local folder with a python virtual environment
    ```
    git clone https://github.com/jbdamask/wkid-smaaht.git
    ```

- Set shell scripts to executable
    ```
    cd wkid_smaaht
    chmod +x scripts/*.sh
    ```

### Slack app creation
- Login to your Slack workspace online. You can create one for free if you don't have one.
- Follow Slack's [Basic app setup guide](https://api.slack.com/authentication/basics)
    - Click the Create a new Slack app button on the page above. 
    - This will take you to the https://api.slack.com site for configuring your app. 
        - Click "Create New App" button
        - Choose to create an app **from an app manifest**.
        - Choose a Slack workspace for your app
        - Select YAML and paste the contents of `slack-app-manifest.yml' in the input field. Click *Next*
        - In order to enable DM's to your app you'll need to check the box under App Home (Note: If Slack tells you that "Sending messages to this app has been turned off" after completing this full installation, restart Slack)

            <img src="images/enable-DM.png" alt="Allow" width="300"/>

        - To set the Slack App icon, look for the Add App Icon under Basic Information. Upload `images/wkid_smaaht_small.jpg`       
    
    - Click Install to Workspace (or Request to Install if you're not a Slack admin)    
 
    - Click Allow 

        <img src="images/slack-app-install.png" alt="Allow" width="300"/>

    - Get Slack App and Bot tokens
        - Under Basic Information, scroll down to App-Level Tokens and click Generate Token and Scopes
            - Token Name: WkidSmaahtAppToken
            - Permission: connections:write
            - Click the Generate button
            - Copy the token to a safe place; you'll need it later
        - Go to Oauth & Perissions sidebar and look for Bot User OAuth Token. Copy and store for later
- Next, you need to invite your app to a channel. Go to a channel of your choice and type `/invite`

    <img src="images/slack-app-dev.png" alt="Allow" width="400"/>
- Search for Wkid Smaaht and click Add

    <img src="images/slack-app-invite.png" alt="Allow" width="300"/>
- Verify you can call it by typing `@Wkid Smaaht`. It won't do anything yet.
- Verify the app can write to the channel. 
    - Get the Slack channel id for the channel you just invited the bot to (you can find this in Slack by clicking the drop down your channel name and scrolling to the bottom)
    - Open a Terminal window on your computer and post a message from Wkid Smaaht
        ```
        curl -X POST -F channel=<channel ID> -F text="Wkid Smaaht ready to go" \
        https://slack.com/api/chat.postMessage \
        -H "Authorization: Bearer <Slack bot token>"
        ```
    
        <img src="images/wkid_smaaht_ready2go.png" alt="Allow" width="250"/>

    If all looks good, move on to the next section.

### Code configuration

- It's a good idea to try your application locally. Go back to your computer terminal and make sure you're in the wkid_smaaht folder.

    ```
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

- Open .env_TEMPLATE and save as .env. Then set the values accordingly. ***IMPORTANT: The .gitignore file for this project specifies that the file ".env" be excluded from upload. But if you add your keys to the .env_TEMPLATE file and check in your code, your keys will be in your git repo!***

- Set an environment variable so that W'kid Smaaht runs locally.
    ```
    export ENV=development
    ```

- Now run the app

    ```
    python wkid_smaaht.py
    ```

- If everything went well, you'll now be able to call the app from Slack

    <img src="images/wkid_smaaht_hi.png" alt="Allow" width="500"/>

Did you make it here? Sweet. Go ahead and stop the app by hitting Ctrl c and read on...or just keep asking it things; some responses are pretty funny.

### Docker build and AWS configuration

A production Slack application shouldn't run on your laptop, but it can run in a container in your AWS account. This section will walk you through creating a Docker image, publishing it to an AWS Elastic Container Registry (ECR) repository and running it as a serverless application that's always on.

- Start Docker Desktop
- Create your AWS Elastic Container Repository (ECR), your Docker image and push the image to your new repo
    
    ``` 
    ./scripts/create_ECR_repo_and_push_container.sh
    Enter your AWS account ID: <your account id>
    Enter your AWS region: \<your AWS region\>
    ```

    This will:

        1. Create an Elastic Container Registry repo called "wkid-smaaht-slack"
        2. Build an image from the dockerfile
        3. Push the image to the ECR repo
    Be patient, this takes 10-20 mins to build. When finished, note the URI for the repo and save it for later

    ```
    aws ecr describe-repositories --repository-names wkid-smaaht-slack --query 'repositories[0].repositoryUri' --output text
    ```

- Write your OpenAI API key and Slack bot and app tokens to AWS Secrets Manager. Use the same values you put into your .env (that file is only used for local testing)
    ```
    ./scripts/create_secrets.sh
    ```
    Copy the ARNs for each secret, you'll need them later

You're now ready to create an AWS Elastic Container Service that will pull your image from ECR and run it. We use AWS Fargate so there's no need to manage EC2s. 

- Open the AWS Management Console and login
- Navigate to CloudFormation and create a stack with new resources using the file `cloudformation/wkid_smaaht_fargate.yml`
    - Stack name: chat-aws-slack
    - Paste in values from what you created earlier for
        - EcrRepositoryUri
        - OpenAIAPISecretArn (NOTE: THIS IS THE SECRETS MANAGER RECORD ARN, NOT THE TOKEN)
        - SlackAppSecretArn (NOTE: THIS IS THE SECRETS MANAGER RECORD ARN, NOT THE TOKEN)
        - SlackBotSecretArn (NOTE: THIS IS THE SECRETS MANAGER RECORD ARN, NOT THE TOKEN)
    - Choose your vpc and private subnet IDs
    - Follow through the rest of the CloudFormation wizard. Add the Tag `AppName:Wkid Smaaht Slack`, otherwise just leave the defaults and keep clicking Next
    - Check the box acknowledging that the script creates IAM resources and slick Submit
- Monitor Events in the CloudFormation console. After a few minutes, the status should read CREATE_COMPLETE. If you see errors, go through the Events that caused them and ensure you didn't have any missteps. One common error is that the ARN for your secrets was wrong.

- Write the provided system prompts to DynamoDB
    ```
    ./scripts/load_system_prompts_into_ddb.sh
    ```
- It's time to start the service
    ```
    ./scripts/start_ECS_service.sh
    ```

- You can monitor the startup from your AWS Console under Elastic Container Service. 

    <img src="images/ECS-startup-running.png" alt="Allow" width="500"/>

- When the ECS Task is Running, you're read to use the app.

    <img src="images/wkid_smaaht_who_are_u.png" alt="Allow" width="500"/>

## Uses

You can use Wkid Smaaht for almost anything you'd use ChatGPT for, as well as some things that ChatGPT doesn't currently offer (see below).

### Practical

<img src="images/wkid-smaaht-smart-goal-ex1.png" alt="Allow" width="500"/>

### Accelerated comprehension

If you've been part of a long Slack thread that you want to summarize, just ask Wkid Smaaht:

<img src="images/summarize-thread.png" alt="Allow" width="500"/>

Or if the thread is really long, and you're feeling lazy, just say tl;dr.

<img src="images/tldr.png" alt="Allow" width="500"/>

Or let's say you've jumped into a fascinating Slack thread where colleagues are talking about things out of your comfort zone. You can hit it with something like this:

<img src="images/tldr-noob.png" alt="Allow" width="500"/>

### Code help
Sometimes you just want an expert at your fingertips. You can DM W'kid Smaaht just like any other Slack user and get immediate help

<img src="images/regex-help.png" alt="Allow" width="500">

### Creativity

<img src="images/creative.png" alt="Allow" width="500"/>

You can even use it to create images using OpenAI's DALL E 2:

<img src="images/chat-and-pix.png" alt="Allow" width="500">


## Commands
W'kid Smaaht comes with several commands. You can see the list by typing :help

<img src="images/wkid_smaaht_help.png" alt="Allow" width="500">

### :pix
As shown above, this command calls the Dall E 2 image generation API from OpenAI (hopefully, we'll update to Dall E 3 soon).

### :search
This uses an AI Agent so search the web based on your input. TBH, it has potential but ain't great yet. Stick with Google or Bing for now.

Eventually this may be upgraded to a research agent. 

<img src="images/wkid_smaaht_search.png" alt="Allow" width="500">

### :webchat
Use this when you want to summarize a long web page and make it available in your Slack thread for Q&A

<img src="images/wkid_smaaht_webchat.png" alt="Allow" width="500">

### :summarize
To use this command in a DM, simply upload a file. If using in a Channel or Thread, you'll need to specifiy @W'kid Smaaht when uploading the file.

W'kid Smaaht will register the file internally and this command will create an abstract and some options for follow-up questions. Note that large documents can take several minutes to summarize.

<img src="images/wkid_smaaht_doc_summary.png" alt="Allow" width="500">

### :qa
This feature lets you chat with your document (uploaded into Slack) or URL (by first running :webchat). It is especially useful if you know what you want.

Experience shows this feature has a ways to go. It's great for certain things but lacking in others. For example, it isn't aware of document structure and doesn't handle tables well. This makes it so-so for Q&A against scientific articles. We expect this feature to improve over time. 

<img src="images/wkid_smaaht_qa.png" alt="Allow" width="500">

## Using commands together
When used together, these commands can be a real time saver.

<img src="images/wkid_smaaht_all-together-now.png" alt="Allow" width="500">


## Advanced

This bot can change! When using GPT4 you can steer how it thinks and responds using something called "System messages". System messages are meant to provide additional context or instructions for the AI model. They can be used to specify certain behaviors or to provide additional context that may not be clear from the user's input alone.

It's important to note that while system messages can provide useful context and direction, they may not always perfectly control the AI's behavior. The AI doesn't understand these instructions in the way a human would, but instead treats them as part of the overall pattern of input it uses to generate a response. It's also worth noting that very specific or complex instructions might be more difficult for the AI to follow accurately.

Wkid Smaaht is a good testing ground for creating and refining System messages to see what works.  This app stores several System messages in DynamoDB and exposes them to Slack via slash commands. 

<img src="images/prompts.png" alt="Allow" width="500"/>

When changed, the personality of the new bot will be specific to your user and channel and persist until you change it again. 

<img src="images/problem-coach.png" alt="Allow" width="500"/>

You can add your own system prompts to the DynamoDB table and they'll automatically appear in Slack.

Resources to learn more about "prompt engineering" and system messages.

- [Best practices for prompt engineering with OpenAI API](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api)
- [ChatGPT Prompt Engineering for Developers](https://www.deeplearning.ai/short-courses/chatgpt-prompt-engineering-for-developers/)

## FAQ
- Does OpenAI use my input? 
    - Per [OpenAI's API Data Usage policy from May 2023](https://openai.com/policies/api-data-usage-policies) OpenAI will not use your conversations to train their models. Still, it's up to you to abide by any constraints or policies set by your organization.
- Does Slack use my input?
    - Slack chats are considered Customer Data, which Slack's policies state are [owned by the Customer](https://slack.com/trust/data-management). 
- Does W'kid Smaaht remember my chats? 
    - By default, W'kid Smaaht logs chats into AWS CloudTrail but this can be turned off in the code.
- Can my team have different chats going on simultaneously?
    - Yep. Chats from different threads don't bleed into one another.
- Does it hallucinate?
    - Yes. But since this is GPT4, it's somewhat [better than GPT3](https://openai.com/research/gpt-4)
- How much can I use it?
    - You can use it until you hit API call limits for [GPT-4](https://platform.openai.com/docs/guides/rate-limits/overview), then you'll have to cool your jets for a while. This could become a real pain if the app is being used by multiple people in your organization (which is likely considering it's a Slack bot).
- How do I redeploy the Docker image if I want to change something?
    - Re-run `scripts/create_ECR_repo_and_push_container.sh`
- How can I add a System message?
    - The easiest way to do this is to create a new text file in the `gpt4_system_prompts` folder and re-run `./scripts/load_system_prompts_into_dbb.sh`. See the Advanced section of this README for more info.
- Why not just use ChatGPT?
    - You certainly can, I do. But here are a few reasons why you may want to use W'kid Smaaht:
        - If you spend much of your day in Slack, it's helpful to have GPT in the same tool. 
        - Maybe not everyone on your team or company has subscribed to ChatGPT Plus. W'kid Smaaht gives them direct access to GPT4.
        - Sharing chats in ChatGPT is cumbersome but it's natural in Slack. 
        - Since OpenAI doesn't train their models on chats via API, W'kid Smaaht can be a better option when dealing with sensitive topics.
- Is there anything not to love?
    - Yep. A bunch of stuff starting with:
        - You may hit GPT4 API limits
        - You may need to restart the service using `./scripts/start_ECS_service.sh` if the bot stops responding in Slack
        - This bot hasn't been stress-tested so if you have many users in Slack, things may bonk out.
        - It doesn't handle large inputs well
        - Most likely, this will be superceded by Slack's own ChatGPT integration.
        - Standard rules of using LLMs apply, namely that you should always review responses for accuracy, completeness and bias.


## What's next?
Keep an eye on the Issues section of this repo


## How it's Built
This project leverages the [Bolt-Python](https://slack.dev/bolt-python/tutorial/getting-started) framework for building Slack applications, and uses code from the [Slack GPT Bot](https://github.com/alex000kim/slack-gpt-bot) project and the deeplearning.ai course, [Building Systems with the ChatGPT API](https://learn.deeplearning.ai/chatgpt-building-system/lesson/1/introduction).

[LangChain](https://www.langchain.com/) is responsible for taking W'kid Smaaht to the next level. The learning curve may be steep but it's worth it! 

### Architecture

<img src="images/Wkid%20Smaaht%20Architecture.png" alt="Allow" width="500"/>

---
<!-- CONTRIBUTING -->
## Contributing to this project
Glad to see you want to make this project better! 

Please follow (GitHub guidelines)[https://docs.github.com/en/get-started/quickstart/contributing-to-projects]. 

When contributing, make sure you run the following user tests:
1. Chat in DM - Should receive wait message, then response
2. Chat in DM thread - Should receive wait message, then response
3. Chat in DM with App mention - Should receive wait message, then response
4. Chat in DM thread with App mention - Should receive wait message, then response
5. Chat in Channel with App mention - Should receive wait message, then response
6. Chat in Channel thread with App mention - Should receive wait message, then response
7. Chat in Channel with no App mention - Should not respond
8. Create pic in channel - Should receive wait message, then image
9. Create pic in channel thread - Should receive wait message, then image
10. Test all commands in DM
11. Test all commands in Channel
12. Slash command in channel - Should receive info about command
13. Slash comand in DM - Should receive info about command
