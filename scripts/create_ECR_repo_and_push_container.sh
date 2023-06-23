#!/bin/bash

#!/bin/bash

# Check if the repository name argument is provided
if [ -z "$1" ]; then
    echo "Please provide the repository name as an argument."
    exit 1
fi

# Assign the repository name argument to a variable
repository_name="$1"

# Create ECR repository
aws ecr create-repository --repository-name "$repository_name"


# Authenticate Docker to ECR
aws ecr get-login-password --region region | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# Build, tag and push image to ECR (note, this is multi-arch because I'm building on my M1 Mac)
docker buildx build --platform linux/amd64,linux/arm64 --push -t <account-id>.dkr.ecr.<region>.amazonaws.com/chat-aws-slack-bot-dev:latest .

# Tag your image
docker tag my-image:latest <account-id>.dkr.ecr.<region>.amazonaws.com/my-repo:latest

# Push your image
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/my-repo:latest
