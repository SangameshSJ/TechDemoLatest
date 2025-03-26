import pulumi
import pulumi_aws as aws


config = pulumi.Config()
environment = config.get("environment") or "staging"


instance_type = {
    "staging": "t2.micro",
    "production": "t2.micro"
}[environment]

key_name = config.get("keyName") or f"{environment}-bastion-key"
cidr_block = config.get("cidrBlock") or "10.0.0.0/16"
region = aws.config.region or "us-east-1"


default_tags = {
    "Environment": environment,
    "ManagedBy": "Pulumi"
}


name_prefix = f"{environment}-"


state_bucket = f"pulumi-state-{environment}"
jenkins_instance_type = config.get("jenkinsInstanceType") or "t3.small"

ami = aws.ec2.get_ami(most_recent=True,
    owners=["amazon"],
    filters=[{
        "name": "name",
        "values": ["amzn2-ami-hvm-*-x86_64-gp2"],
    }])

bastion_user_data = """#!/bin/bash
# Update system and install Docker
yum update -y
amazon-linux-extras install -y docker
systemctl start docker
systemctl enable docker

# Create Docker group and add ec2-user
groupadd docker || true
usermod -aG docker ec2-user

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Get instance ID
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/bin/config.json <<EOL
{
    "agent": {
        "metrics_collection_interval": 60,
        "run_as_user": "root",
        "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
    },
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/messages",
                        "log_group_name": "bastion-host-logs",
                        "log_stream_name": "${INSTANCE_ID}-messages",
                        "timestamp_format": "%b %d %H:%M:%S"
                    },
                    {
                        "file_path": "/var/log/secure",
                        "log_group_name": "bastion-host-logs",
                        "log_stream_name": "${INSTANCE_ID}-secure",
                        "timestamp_format": "%b %d %H:%M:%S"
                    },
                    {
                        "file_path": "/var/log/cloud-init.log",
                        "log_group_name": "bastion-host-logs",
                        "log_stream_name": "${INSTANCE_ID}-cloud-init"
                    },
                    {
                        "file_path": "/var/log/cloud-init-output.log",
                        "log_group_name": "bastion-host-logs",
                        "log_stream_name": "${INSTANCE_ID}-cloud-init-output"
                    }
                ]
            }
        },
        "log_stream_name": "${INSTANCE_ID}",
        "force_flush_interval": 15
    },
    "metrics": {
        "metrics_collected": {
            "cpu": {
                "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"],
                "metrics_collection_interval": 60,
                "totalcpu": true
            },
            "disk": {
                "measurement": ["disk_used_percent"],
                "resources": ["/"],
                "ignore_file_system_types": ["tmpfs", "devtmpfs"]
            },
            "mem": {
                "measurement": ["mem_used_percent"]
            },
            "swap": {
                "measurement": ["swap_used_percent"]
            },
            "netstat": {
                "measurement": ["tcp_established", "tcp_time_wait"]
            }
        },
        "append_dimensions": {
            "InstanceId": "${INSTANCE_ID}"
        },
        "aggregation_dimensions": [["InstanceId"]]
    }
}
EOL

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json

# Configure log rotation for critical logs
cat > /etc/logrotate.d/bastion-logs <<EOL
/var/log/messages {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    sharedscripts
    postrotate
        /bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
}

/var/log/secure {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    sharedscripts
    postrotate
        /bin/kill -HUP `cat /var/run/syslogd.pid 2> /dev/null` 2> /dev/null || true
    endscript
}
EOL

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


# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent


# Create CloudWatch agent configuration
cat > /opt/aws/amazon-cloudwatch-agent/bin/config.json <<EOL
{
 "agent": {
   "metrics_collection_interval": 60,
   "run_as_user": "root"
 },
 "logs": {
   "logs_collected": {
     "files": {
       "collect_list": [
         {
           "file_path": "/var/log/messages",
           "log_group_name": "app-instance-logs",
           "log_stream_name": "{instance_id}-system-logs"
         },
         {
           "file_path": "/var/log/docker",
           "log_group_name": "app-instance-logs",
           "log_stream_name": "{instance_id}-docker-logs"
         }
       ]
     }
   }
 },
 "metrics": {
   "metrics_collected": {
     "cpu": {
       "measurement": ["cpu_usage_idle", "cpu_usage_user", "cpu_usage_system"]
     },
     "mem": {
       "measurement": ["mem_used_percent"]
     },
     "disk": {
       "measurement": ["disk_used_percent"],
       "resources": ["/"]
     }
   }
 }
}
EOL


# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json


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


# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent


# Ensure Jenkins log directory exists
mkdir -p /var/jenkins_home/logs
chown -R jenkins:jenkins /var/jenkins_home/logs

# Enhanced CloudWatch agent config for Jenkins
cat > /opt/aws/amazon-cloudwatch-agent/etc/jenkins-log-config.json <<EOL
{
    "logs": {
        "logs_collected": {
            "files": {
                "collect_list": [
                    {
                        "file_path": "/var/log/jenkins/jenkins.log",
                        "log_group_name": "jenkins-instance-logs",
                        "log_stream_name": "{instance_id}-jenkins-main",
                        "timestamp_format": "%Y-%m-%d %H:%M:%S"
                    },
                    {
                        "file_path": "/var/jenkins_home/logs/*.log",
                        "log_group_name": "jenkins-instance-logs",
                        "log_stream_name": "{instance_id}-jenkins-logs",
                        "timestamp_format": "%Y-%m-%d %H:%M:%S"
                    },
                    {
                        "file_path": "/var/log/docker",
                        "log_group_name": "jenkins-instance-logs",
                        "log_stream_name": "{instance_id}-docker"
                    }
                ]
            }
        }
    }
}
EOL


# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json


# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose


# Create Jenkins home directory
mkdir -p /var/jenkins_home
chmod 777 /var/jenkins_home


# Run Jenkins with Docker support and monitoring
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
   logging:
     driver: "json-file"
     options:
       max-size: "100m"
       max-file: "3"
EOL


# Start Jenkins using Docker Compose
cd /home/ec2-user && docker-compose up -d
"""