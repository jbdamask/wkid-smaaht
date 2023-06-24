# Change values below to your own values

# Prompt user for values
read -p "Enter your repository name: " my_repo
read -p "Enter your region: " region
read -p "Enter your account ID: " account_id

# Create ECR repository
aws ecr create-repository --repository-name $my_repo

# Authenticate Docker to ECR
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $account_id.dkr.ecr.$region.amazonaws.com

# Build, tag and push image to ECR (note, this is multi-arch because I'm building on my M1 Mac)
docker buildx build --platform linux/amd64,linux/arm64 --push -t $account_id.dkr.ecr.$region.amazonaws.com/$my_repo:latest .
