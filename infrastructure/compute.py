import pulumi
import pulumi_aws as aws
from infrastructure.config import instance_type, key_name, ami, app_user_data

def create_compute_resources(network, security_groups, instance_profile, target_group=None):
    # Create the application instances
    app1_instance = aws.ec2.Instance("app1-instance",
        ami=ami.id,
        instance_type=instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["app_sg"].id],
        subnet_id=network["app1_subnet"].id,
        iam_instance_profile=instance_profile.name,
        user_data=app_user_data,
        tags={
            "Name": "app1-instance",
        })

    app2_instance = aws.ec2.Instance("app2-instance",
        ami=ami.id,
        instance_type=instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["app_sg"].id],
        subnet_id=network["app2_subnet"].id,
        iam_instance_profile=instance_profile.name,
        user_data=app_user_data,
        tags={
            "Name": "app2-instance",
        })

    # If target group is provided, register instances
    if target_group:
        app1_target_group_attachment = aws.lb.TargetGroupAttachment("app1-tg-attachment",
            target_group_arn=target_group.arn,
            target_id=app1_instance.id,
            port=80)

        app2_target_group_attachment = aws.lb.TargetGroupAttachment("app2-tg-attachment",
            target_group_arn=target_group.arn,
            target_id=app2_instance.id,
            port=80)

    # Create the bastion host
    bastion_instance = aws.ec2.Instance("bastion-host",
        ami=ami.id,
        instance_type=instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["bastion_sg"].id],
        subnet_id=network["public_subnet"].id,
        iam_instance_profile=instance_profile.name,
        user_data="""#!/bin/bash
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
""",
        tags={
            "Name": "bastion-host",
        })

    # Create the Jenkins instance
    jenkins_instance = aws.ec2.Instance("jenkins-instance",
        ami=ami.id,
        instance_type="t3.small",  # Jenkins needs more resources with Docker
        key_name=key_name,
        vpc_security_group_ids=[security_groups["jenkins_sg"].id],
        subnet_id=network["public_subnet"].id,  # Jenkins in public subnet for easy access
        iam_instance_profile=instance_profile.name,
        user_data="""#!/bin/bash
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
""",
        tags={
            "Name": "jenkins-instance",
        })

    return {
        "bastion_instance": bastion_instance,
        "app1_instance": app1_instance,
        "app2_instance": app2_instance,
        "jenkins_instance": jenkins_instance
    }