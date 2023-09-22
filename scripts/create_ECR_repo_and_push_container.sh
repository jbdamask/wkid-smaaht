# Change values below to your own values

# Prompt user for values
# read -p "Enter your repository name: " my_repo
read -p "Enter your AWS account ID: " account_id
read -p "Enter your AWS region: " region
read -p "Enter your AWS account profile (default will be 'default' if left blank): " profile
profile=${profile:-default}

my_repo="wkid-smaaht-slack"

# Create ECR repository
aws ecr create-repository --repository-name $my_repo --profile $profile > /dev/null 2>&1

# Authenticate Docker to ECR
aws ecr get-login-password --region $region --profile $profile | docker login --username AWS --password-stdin $account_id.dkr.ecr.$region.amazonaws.com

# If you get a docker complaint about the driver not supporting multiple platforms, run this and re-execute this script
# docker buildx create --use

# Build, tag and push image to ECR (note, this is multi-arch because I'm building on my M1 Mac)
# docker buildx build --no-cache --platform linux/amd64,linux/arm64 --push -t $account_id.dkr.ecr.$region.amazonaws.com/$my_repo:latest .
docker buildx build --no-cache --platform linux/amd64 --push -t $account_id.dkr.ecr.$region.amazonaws.com/$my_repo:latest .
