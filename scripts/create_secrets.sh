# Replace --secret-string and --region with your own values

aws secretsmanager create-secret --name "SLACK_BOT_TOKEN" --secret-string "your-secret-value" --region "your-region"

aws secretsmanager create-secret --name "SLACK_APP_TOKEN" --secret-string "your-secret-value" --region "your-region"

aws secretsmanager create-secret --name "OPENAI_API_KEY" --secret-string "your-secret-value" --region "your-region"
