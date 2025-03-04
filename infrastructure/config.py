# infrastructure/config.py

import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
instance_type = config.get("instanceType") or "t2.micro"
key_name = config.get("keyName") or "bastion-key"
cidr_block = config.get("cidrBlock") or "10.0.0.0/16"
region = aws.config.region or "us-east-1"

# Get the latest Amazon Linux 2 AMI
ami = aws.ec2.get_ami(most_recent=True,
    owners=["amazon"],
    filters=[{
        "name": "name",
        "values": ["amzn2-ami-hvm-*-x86_64-gp2"],
    }])

# User data scripts
bastion_user_data = """#!/bin/bash
yum update -y
amazon-linux-extras install -y docker
systemctl start docker
systemctl enable docker

# Create Docker group and add ec2-user
groupadd docker || true
usermod -aG docker ec2-user

# Ensure SSH forwarding for multi-hop SSH
echo "AllowAgentForwarding yes" >> /etc/ssh/sshd_config
systemctl restart sshd
"""

app_user_data = """#!/bin/bash
yum update -y
amazon-linux-extras install -y docker
systemctl start docker
systemctl enable docker

# Create Docker group and add ec2-user
groupadd docker || true
usermod -aG docker ec2-user

# Create directory for docker images
mkdir -p /tmp
chmod 777 /tmp
"""

jenkins_user_data = """#!/bin/bash
yum update -y
amazon-linux-extras install -y docker
systemctl start docker
systemctl enable docker

# Create Docker group
groupadd docker || true
usermod -aG docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create Jenkins home directory
mkdir -p /var/jenkins_home
chmod 777 /var/jenkins_home

# Run Jenkins with Docker support
cat > /home/ec2-user/docker-compose.yml <<EOL
version: '3'
services:
  jenkins:
    image: jenkins/jenkins:lts
    privileged: true
    user: root
    ports:
      - 8080:8080
      - 50000:50000
    volumes:
      - /var/jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker
    environment:
      - JENKINS_OPTS="--prefix=/jenkins"
EOL

# Start Jenkins using Docker Compose
cd /home/ec2-user && docker-compose up -d
"""