#!/bin/bash
read -p "Enter your AWS account profile (default will be 'default' if left blank): " profile
profile=${profile:-default}

service_arn=$(aws ecs list-services --cluster WkidSmaahtCluster --query 'serviceArns[0]' --output text --profile "$profile")
aws ecs update-service --cluster WkidSmaahtCluster --service $service_arn --desired-count 1 --force-new-deployment --profile "$profile"
