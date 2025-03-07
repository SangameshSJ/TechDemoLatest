
import pulumi
import pulumi_aws as aws
import json

def create_iam_resources():
    # Create IAM role for instances
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
        }))

    # Attach S3 read access policy
    role_policy_attachment_s3 = aws.iam.RolePolicyAttachment("role-policy-attachment-s3",
        role=instance_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")
    
    # Add CloudWatch Logs access
    role_policy_attachment_cw = aws.iam.RolePolicyAttachment("role-policy-attachment-cw",
        role=instance_role.name,
        policy_arn="arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy")

    instance_profile = aws.iam.InstanceProfile("instance-profile",
        role=instance_role.name)

    return {
        "instance_profile": instance_profile
    }