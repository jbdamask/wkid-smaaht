# Change values below to your own values

# Prompt user for values
# read -p "Enter your repository name: " my_repo
read -p "Enter your AWS account ID: " account_id
read -p "Enter your AWS region: " region

my_repo="wkid-smaaht-slack"

# Create ECR repository
aws ecr create-repository --repository-name $my_repo > /dev/null 2>&1

# Authenticate Docker to ECR
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $account_id.dkr.ecr.$region.amazonaws.com

# Build, tag and push image to ECR (note, this is multi-arch because I'm building on my M1 Mac)
docker buildx build --no-cache --platform linux/amd64,linux/arm64 --push -t $account_id.dkr.ecr.$region.amazonaws.com/$my_repo:latest .
