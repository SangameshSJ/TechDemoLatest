import pulumi
import pulumi_aws as aws


config = pulumi.Config()
instance_type = config.get("instanceType") or "t2.micro"
key_name = config.get("keyName") or "bastion-key"
cidr_block = config.get("cidrBlock") or "10.0.0.0/16"
region = aws.config.region or "us-east-1"


"""
Configuration variables for the Pulumi infrastructure stack.

Variables:
    instance_type (str): EC2 instance type to use, defaults to t2.micro
    key_name (str): SSH key pair name for EC2 instances, defaults to bastion-key
    cidr_block (str): VPC CIDR block, defaults to 10.0.0.0/16
    region (str): AWS region to deploy to, defaults to us-east-1
"""

ami = aws.ec2.get_ami(most_recent=True,
    owners=["amazon"],
    filters=[{
        "name": "name",
        "values": ["amzn2-ami-hvm-*-x86_64-gp2"],
    }])

bastion_user_data = """#!/bin/bash
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
           "log_group_name": "bastion-host-logs",
           "log_stream_name": "{instance_id}-system-logs"
         },
         {
           "file_path": "/var/log/secure",
           "log_group_name": "bastion-host-logs",
           "log_stream_name": "{instance_id}-ssh-logs"
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
          "log_group_name": "jenkins-instance-logs",
          "log_stream_name": "{instance_id}-system-logs"
        },
        {
          "file_path": "/var/jenkins_home/logs/jenkins.log",
          "log_group_name": "jenkins-instance-logs",
          "log_stream_name": "{instance_id}-jenkins-logs"
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


# Create script to install required plugins
cat > /var/jenkins_home/install-plugins.sh <<EOL
#!/bin/bash

# Wait for Jenkins to start
until curl -s -f http://localhost:8080/login > /dev/null; do
  sleep 10
  echo "Waiting for Jenkins to start..."
done

# Get the initial admin password
ADMIN_PASSWORD=\$(cat /var/jenkins_home/secrets/initialAdminPassword)

# Install required plugins
jenkins-plugin-cli --plugins docker-plugin docker-workflow configuration-as-code job-dsl workflow-aggregator git matrix-auth credentials-binding pipeline-utility-steps ssh-agent

# Restart Jenkins to apply plugin changes
curl -X POST -u admin:\$ADMIN_PASSWORD http://localhost:8080/restart
EOL

chmod +x /var/jenkins_home/install-plugins.sh

# Execute the script in the background after Jenkins starts
(sleep 30 && /var/jenkins_home/install-plugins.sh) &

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose


# Create Jenkins home directory
mkdir -p /var/jenkins_home
chmod 777 /var/jenkins_home

# Create a Jenkins casc (Configuration as Code) file
mkdir -p /var/jenkins_casc
cat > /var/jenkins_casc/jenkins.yaml <<EOL
jenkins:
  systemMessage: "Jenkins configured automatically with Docker agents"
  numExecutors: 0  # Set master node executors to 0
  clouds:
    - docker:
        name: "docker"
        dockerHost: "unix:///var/run/docker.sock"
        containerCap: 10
        templates:
          - name: "docker-agent"
            image: "jenkins/agent:latest"
            pullTimeout: 300
            connectTimeout: 300
            remoteFs: "/home/jenkins/agent"
            instanceCap: 5
            mode: EXCLUSIVE
            labelString: "docker-agent"
            volumes:
              - "/var/run/docker.sock:/var/run/docker.sock"
            environment:
              - "JENKINS_AGENT_WORKDIR=/home/jenkins/agent"
            connector:
              attach:
                user: "jenkins"
EOL

# Run Jenkins using Docker Compose
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
      - /var/jenkins_casc:/var/jenkins_casc
    environment:
      - JENKINS_OPTS="--prefix=/jenkins"
      - CASC_JENKINS_CONFIG=/var/jenkins_casc/jenkins.yaml
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
EOL


# Create script to install required plugins
cat > /var/jenkins_home/install-plugins.sh <<EOL
#!/bin/bash

# Wait for Jenkins to start
until curl -s -f http://localhost:8080/login > /dev/null; do
  sleep 10
  echo "Waiting for Jenkins to start..."
done

# Get the initial admin password
ADMIN_PASSWORD=\$(cat /var/jenkins_home/secrets/initialAdminPassword)

# Install required plugins
jenkins-plugin-cli --plugins docker-plugin docker-workflow configuration-as-code job-dsl workflow-aggregator git matrix-auth credentials-binding pipeline-utility-steps ssh-agent

# Restart Jenkins to apply plugin changes
curl -X POST -u admin:\$ADMIN_PASSWORD http://localhost:8080/restart
EOL

chmod +x /var/jenkins_home/install-plugins.sh

# Execute the script in the background after Jenkins starts
(sleep 30 && /var/jenkins_home/install-plugins.sh) &


# Start Jenkins using Docker Compose
cd /home/ec2-user && docker-compose up -d
"""