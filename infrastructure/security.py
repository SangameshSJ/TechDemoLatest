# infrastructure/security.py

import pulumi
import pulumi_aws as aws


def create_security_groups(vpc_id):
    """
    Creates security groups for the infrastructure.
    
    This function creates three security groups:
    - Bastion SG: Allows SSH access from the internet
    - Application SG: Allows SSH from bastion and HTTP/HTTPS from anywhere
    - Jenkins SG: Allows SSH from bastion and web access on port 8080
    
    Args:
        vpc_id (str): The ID of the VPC to create security groups in
        
    Returns:
        dict: Dictionary containing all created security group resources
    """
    # Create Security Groups
    bastion_sg = aws.ec2.SecurityGroup("bastion-sg",
        vpc_id=vpc_id,
        description="Allow SSH access to the bastion host",
        ingress=[{
            "protocol": "tcp",
            "from_port": 22,
            "to_port": 22,
            "cidr_blocks": ["0.0.0.0/0"],  # In production, restrict to your IP
        }],
        egress=[{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        tags={
            "Name": "bastion-sg",
        })


    app_sg = aws.ec2.SecurityGroup("app-sg",
        vpc_id=vpc_id,
        description="Allow access to application instances",
        ingress=[
            {
                "protocol": "tcp",
                "from_port": 22,
                "to_port": 22,
                "security_groups": [bastion_sg.id],  # Only allow SSH from bastion
            },
            {
                "protocol": "tcp",
                "from_port": 80,
                "to_port": 80,
                "cidr_blocks": ["0.0.0.0/0"],  # HTTP access
            },
            {
                "protocol": "tcp",
                "from_port": 443,
                "to_port": 443,
                "cidr_blocks": ["0.0.0.0/0"],  # HTTPS access
            }
        ],
        egress=[{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        tags={
            "Name": "app-sg",
        })


    jenkins_sg = aws.ec2.SecurityGroup("jenkins-sg",
        vpc_id=vpc_id,
        description="Allow access to Jenkins",
        ingress=[
            {
                "protocol": "tcp",
                "from_port": 22,
                "to_port": 22,
                "security_groups": [bastion_sg.id],  # SSH from bastion
            },
            {
                "protocol": "tcp",
                "from_port": 8080,
                "to_port": 8080,
                "cidr_blocks": ["0.0.0.0/0"],  # Jenkins web UI
            }
        ],
        egress=[{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        tags={
            "Name": "jenkins-sg",
        })


    return {
        "bastion_sg": bastion_sg,
        "app_sg": app_sg,
        "jenkins_sg": jenkins_sg
    }