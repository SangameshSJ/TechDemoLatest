import pulumi
import pulumi_aws as aws
import json


def create_iam_resources():
    """
    Creates IAM resources required for the infrastructure.
    
    This function creates:
    - An IAM role for EC2 instances
    - Policy attachments for S3 read access and CloudWatch metrics
    - An instance profile to attach the role to EC2 instances
    
    Returns:
        dict: Dictionary containing the created IAM resources
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
        }))   

    role_policy_attachment_cw = aws.iam.RolePolicyAttachment("role-policy-attachment-cw",
        role=instance_role.name,
        policy_arn="arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy")


    instance_profile = aws.iam.InstanceProfile("instance-profile",
        role=instance_role.name)


    return {
        "instance_profile": instance_profile
    }