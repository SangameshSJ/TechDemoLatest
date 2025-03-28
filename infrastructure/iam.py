import pulumi
import pulumi_aws as aws
import json

def create_iam_resources():
    """
    Creates IAM resources with properly formatted policies for logging
    """
    
    instance_role = aws.iam.Role("instance-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com",
                },
            }],
        }),
        description="Role for EC2 instances with CloudWatch logging permissions",
        tags={
            "Environment": pulumi.Config().get("environment") or "staging",
            "ManagedBy": "Pulumi"
        })

    
    aws.iam.RolePolicyAttachment("cloudwatch-agent-policy",
        role=instance_role.name,
        policy_arn="arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy")

    
    logging_policy = aws.iam.Policy("enhanced-logging-policy",
        description="Policy for CloudWatch logging",
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Resource": [
                        "arn:aws:logs:*:*:log-group:bastion-host-logs*",
                        "arn:aws:logs:*:*:log-group:jenkins-instance-logs*",
                        "arn:aws:logs:*:*:log-group:app-instance-logs*",
                        "arn:aws:logs:*:*:log-group:*:log-stream:*"
                    ]
                }
            ]
        }))

    aws.iam.RolePolicyAttachment("enhanced-logging-attachment",
        role=instance_role.name,
        policy_arn=logging_policy.arn)

    
    aws.iam.RolePolicyAttachment("jenkins-policy-attachment",
        role=instance_role.name,
        policy_arn=jenkins_policy.arn)

    
    instance_profile = aws.iam.InstanceProfile("instance-profile",
        role=instance_role.name,
        tags={
            "Environment": pulumi.Config().get("environment") or "staging",
            "ManagedBy": "Pulumi"
        })

    return {
        "instance_profile": instance_profile,
        "instance_role": instance_role,
        "logging_policy": logging_policy,
        "jenkins_policy": jenkins_policy
    }