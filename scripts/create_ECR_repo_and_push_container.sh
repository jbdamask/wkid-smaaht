# Change values below to your own values

# # Create ECR repository
# aws ecr create-repository --repository-name my-repo

# Authenticate Docker to ECR
aws ecr get-login-password --region region | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# Build, tag and push image to ECR (note, this is multi-arch because I'm building on my M1 Mac)
docker buildx build --platform linux/amd64,linux/arm64 --push -t <account-id>.dkr.ecr.<region>.amazonaws.com/chat-aws-slack-bot-dev:latest .

# Tag your image
docker tag my-image:latest <account-id>.dkr.ecr.<region>.amazonaws.com/my-repo:latest

# Push your image
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/my-repo:latest
