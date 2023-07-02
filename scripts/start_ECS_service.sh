#!/bin/bash
service_arn=$(aws ecs list-services --cluster WkidSmaahtCluster --query 'serviceArns[0]' --output text)
aws ecs update-service --cluster WkidSmaahtCluster --service $service_arn --desired-count 1 --force-new-deployment
