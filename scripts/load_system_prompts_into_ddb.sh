#!/bin/bash
read -p "Enter your AWS account profile (default will be 'default' if left blank): " profile
profile=${profile:-default}
for file in gpt4_system_prompts/*.txt; do
    prompt_name=$(basename "$file" .txt | cut -d '-' -f1)
    system_prompt=$(cat "$file")
    json=$(jq -n \
                --arg pn "$prompt_name" \
                --arg sp "$system_prompt" \
                '{TableName: "GPTSystemPrompts", Item: {prompt_name: {S: $pn}, system_prompt: {S: $sp}}}')
    aws dynamodb put-item --profile "$profile" --cli-input-json "$json"
done
