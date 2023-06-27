#!/bin/bash
for file in gpt4_system_prompts/*.txt; do
    prompt_name=$(basename "$file" .txt | cut -d '-' -f1)
    system_prompt=$(cat "$file")
    json=$(jq -n \
                --arg pn "$prompt_name" \
                --arg sp "$system_prompt" \
                '{TableName: "GPTSystemPrompts", Item: {prompt_name: {S: $pn}, system_prompt: {S: $sp}}}')
    aws dynamodb put-item --cli-input-json "$json"
done
