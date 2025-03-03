import pulumi
import pulumi_aws as aws
import json

# Configuration
config = pulumi.Config()
instance_type = config.get("instanceType") or "t2.micro"  # Free tier eligible
key_name = config.get("keyName") or "bastion-key"  # Your SSH key name
cidr_block = config.get("cidrBlock") or "10.0.0.0/16"
region = aws.config.region or "us-east-1"

# Create a VPC
vpc = aws.ec2.Vpc("bastion-vpc",
    cidr_block=cidr_block,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": "bastion-vpc",
    })

# Create an Internet Gateway
igw = aws.ec2.InternetGateway("bastion-igw",
    vpc_id=vpc.id,
    tags={
        "Name": "bastion-igw",
    })

# Create a public subnet for the bastion host
public_subnet = aws.ec2.Subnet("bastion-public-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone=f"{region}a",
    map_public_ip_on_launch=True,  # Ensure this is True
    tags={
        "Name": "bastion-public-subnet",
    })

# Create private subnets for the applications
app1_subnet = aws.ec2.Subnet("app1-private-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone=f"{region}a",
    tags={
        "Name": "app1-private-subnet",
    })

app2_subnet = aws.ec2.Subnet("app2-private-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.3.0/24",
    availability_zone=f"{region}b",
    tags={
        "Name": "app2-private-subnet",
    })

# Create a NAT Gateway for the private subnets
eip = aws.ec2.Eip("nat-eip",
    vpc=True)

nat_gateway = aws.ec2.NatGateway("bastion-nat",
    allocation_id=eip.id,
    subnet_id=public_subnet.id,
    tags={
        "Name": "bastion-nat",
    })

# Create route tables
public_route_table = aws.ec2.RouteTable("public-rt",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": igw.id,
    }],
    tags={
        "Name": "public-rt",
    })
    
private_route_table = aws.ec2.RouteTable("private-rt",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "nat_gateway_id": nat_gateway.id,
    }],
    tags={
        "Name": "private-rt",
    })

# Associate route tables with subnets
public_rt_assoc = aws.ec2.RouteTableAssociation("public-rt-assoc",
    subnet_id=public_subnet.id,
    route_table_id=public_route_table.id)

app1_rt_assoc = aws.ec2.RouteTableAssociation("app1-rt-assoc",
    subnet_id=app1_subnet.id,
    route_table_id=private_route_table.id)

app2_rt_assoc = aws.ec2.RouteTableAssociation("app2-rt-assoc",
    subnet_id=app2_subnet.id,
    route_table_id=private_route_table.id)

# Create Security Groups
bastion_sg = aws.ec2.SecurityGroup("bastion-sg",
    vpc_id=vpc.id,
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
    vpc_id=vpc.id,
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
    vpc_id=vpc.id,
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

# Get the latest Amazon Linux 2 AMI
ami = aws.ec2.get_ami(most_recent=True,
    owners=["amazon"],
    filters=[{
        "name": "name",
        "values": ["amzn2-ami-hvm-*-x86_64-gp2"],
    }])

# User data for bastion host
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

# User data for app instances
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

# Updated user data for Jenkins instance with Docker
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

# Attach policies for EC2 to access S3, ECR, etc.
role_policy_attachment = aws.iam.RolePolicyAttachment("role-policy-attachment",
    role=instance_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess")

instance_profile = aws.iam.InstanceProfile("instance-profile",
    role=instance_role.name)

# Create the bastion host
bastion_instance = aws.ec2.Instance("bastion-host",
    ami=ami.id,
    instance_type=instance_type,
    key_name=key_name,
    vpc_security_group_ids=[bastion_sg.id],
    subnet_id=public_subnet.id,
    iam_instance_profile=instance_profile.name,
    user_data=bastion_user_data,
    tags={
        "Name": "bastion-host",
    })

# Create the application instances
app1_instance = aws.ec2.Instance("app1-instance",
    ami=ami.id,
    instance_type=instance_type,
    key_name=key_name,
    vpc_security_group_ids=[app_sg.id],
    subnet_id=app1_subnet.id,
    iam_instance_profile=instance_profile.name,
    user_data=app_user_data,
    tags={
        "Name": "app1-instance",
    })

app2_instance = aws.ec2.Instance("app2-instance",
    ami=ami.id,
    instance_type=instance_type,
    key_name=key_name,
    vpc_security_group_ids=[app_sg.id],
    subnet_id=app2_subnet.id,
    iam_instance_profile=instance_profile.name,
    user_data=app_user_data,
    tags={
        "Name": "app2-instance",
    })

# Create the Jenkins instance
jenkins_instance = aws.ec2.Instance("jenkins-instance",
    ami=ami.id,
    instance_type="t3.small",  # Jenkins needs more resources with Docker
    key_name=key_name,
    vpc_security_group_ids=[jenkins_sg.id],
    subnet_id=public_subnet.id,  # Jenkins in public subnet for easy access
    iam_instance_profile=instance_profile.name,
    user_data=jenkins_user_data,
    tags={
        "Name": "jenkins-instance",
    })

# Export the necessary details
pulumi.export("vpc_id", vpc.id)
pulumi.export("bastion_public_ip", bastion_instance.public_ip)
pulumi.export("jenkins_public_ip", jenkins_instance.public_ip)
pulumi.export("app1_private_ip", app1_instance.private_ip)
pulumi.export("app2_private_ip", app2_instance.private_ip)
pulumi.export("ssh_command", pulumi.Output.concat("ssh -i ", key_name, ".pem ec2-user@", bastion_instance.public_ip))