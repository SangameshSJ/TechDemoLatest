import pulumi
import pulumi_aws as aws


# Configuration
config = pulumi.Config()
instance_type = config.get("instanceType") or "t2.micro"
key_name = config.get("keyName") or "bastion-key"
cidr_block = config.get("cidrBlock") or "10.0.0.0/16"
region = aws.config.region or "us-east-1"
jenkins_instance_type = config.get("jenkinsInstanceType") or "t3.medium"  # Upgraded for Docker agents


"""
Configuration variables for the Pulumi infrastructure stack.

Variables:
    instance_type (str): EC2 instance type to use, defaults to t2.micro
    key_name (str): SSH key pair name for EC2 instances, defaults to bastion-key
    cidr_block (str): VPC CIDR block, defaults to 10.0.0.0/16
    region (str): AWS region to deploy to, defaults to us-east-1
    jenkins_instance_type (str): EC2 instance type for Jenkins, defaults to t3.medium
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


# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose


# Create Jenkins home directory
mkdir -p /var/jenkins_home
chmod 777 /var/jenkins_home


# Install Jenkins plugins for Docker agents
cat > /var/jenkins_home/plugins.txt <<EOL
docker-plugin
docker-workflow
workflow-aggregator
git
pipeline-model-definition
credentials
ssh-credentials
EOL

# Set up Jenkins plugin installation script
cat > /home/ec2-user/install-plugins.sh <<EOL
#!/bin/bash
JENKINS_HOST="http://localhost:8080"
JENKINS_USER="admin"
ADMIN_PASSWORD=\$(cat /var/jenkins_home/secrets/initialAdminPassword)

# Wait for Jenkins to start
echo "Waiting for Jenkins to start..."
until curl -s \$JENKINS_HOST > /dev/null; do
  sleep 10
done

# Install Jenkins CLI
curl -L \$JENKINS_HOST/jnlpJars/jenkins-cli.jar -o /home/ec2-user/jenkins-cli.jar

# Install plugins
cat /var/jenkins_home/plugins.txt | while read plugin; do
  echo "Installing plugin: \$plugin"
  java -jar /home/ec2-user/jenkins-cli.jar -s \$JENKINS_HOST -auth \$JENKINS_USER:\$ADMIN_PASSWORD install-plugin \$plugin
done

# Restart Jenkins to apply plugin changes
java -jar /home/ec2-user/jenkins-cli.jar -s \$JENKINS_HOST -auth \$JENKINS_USER:\$ADMIN_PASSWORD safe-restart
EOL

chmod +x /home/ec2-user/install-plugins.sh

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
     - /home/ec2-user/install-plugins.sh:/var/jenkins_home/install-plugins.sh
   environment:
     - JENKINS_OPTS="--prefix=/jenkins"
   logging:
     driver: "json-file"
     options:
       max-size: "100m"
       max-file: "3"
EOL

# Install Docker agent configuration script
cat > /home/ec2-user/configure-docker-agent.groovy <<EOL
import jenkins.model.*
import hudson.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import hudson.plugins.sshslaves.*
import hudson.plugins.sshslaves.verifiers.*
import hudson.slaves.*
import hudson.slaves.EnvironmentVariablesNodeProperty.Entry
import hudson.plugins.docker.DockerTemplate
import hudson.plugins.docker.DockerTemplateBase
import hudson.plugins.docker.DockerCloud
import hudson.plugins.docker.launcher.DockerComputerLauncher
import hudson.plugins.docker.launcher.DockerComputerSSHLauncher
import jenkins.plugins.git.GitSCMSource

def instance = Jenkins.getInstance()

// Define Docker agent templates
def dockerTemplateBase = new DockerTemplateBase(
  'jenkins/agent',                // image
  'docker-agent-workspace',       // mountsString
  '',                             // volumesString
  '',                             // volumesFromString
  'entry',                        // environmentsString
  '',                             // hostname
  '',                             // user
  'docker',                       // extraGroupsString
  '10m',                          // memoryLimit
  '1',                            // memorySwap
  0,                              // cpuShares
  'jenkins',                      // dnsString
  '',                             // network
  '',                             // macAddress
  '',                             // privileged
  false,                          // tty
  '',                             // extraHostsString
  true                            // bindAllPorts
)

// SSH launcher config with basic settings
def launcher = new DockerComputerSSHLauncher(
  new NonVerifyingKeyVerificationStrategy(),
  null,                           // host
  null,                           // port
  'jenkins',                      // credentialsId - will be set up later
  null,                           // jvmOptions
  null,                           // javaPath
  null,                           // prefixStartSlaveCmd
  null,                           // suffixStartSlaveCmd
  60                              // launchTimeoutSeconds
)

// Create Docker template
def dockerTemplate = new DockerTemplate(
  dockerTemplateBase,             // dockerTemplateBase
  launcher,                       // launcher
  'docker-agent',                 // labelString
  'docker-agent',                 // remoteFs
  '5'                             // instanceCapStr
)

// Set retention strategy - keep agents running for up to 20 minutes
def retentionStrategy = new hudson.slaves.RetentionStrategy.Demand(5, 20)
dockerTemplate.setRetentionStrategy(retentionStrategy)

// Create Docker cloud
def dockerCloud = new DockerCloud(
  'docker',                       // name
  [dockerTemplate],               // templates
  'unix:///var/run/docker.sock',  // serverUrl
  5,                              // containerCap
  5,                              // connectTimeout
  5,                              // readTimeout
  null,                           // credentialsId
  null,                           // version
  null                            // dockerHostname
)

// Add cloud to Jenkins
def clouds = instance.clouds
clouds.add(dockerCloud)

// Save the configuration
instance.save()
println("Docker agent cloud configuration saved")
EOL

# Create a script to execute the Groovy configuration
cat > /home/ec2-user/setup-jenkins.sh <<EOL
#!/bin/bash
JENKINS_HOST="http://localhost:8080"
JENKINS_USER="admin"
ADMIN_PASSWORD=\$(cat /var/jenkins_home/secrets/initialAdminPassword)

# Wait for plugins to be installed
echo "Waiting for plugins to be installed..."
sleep 60

# Run the Docker agent configuration
echo "Configuring Docker agent..."
curl -v -XPOST \\
  -H "Content-Type: application/x-groovy" \\
  -d @/home/ec2-user/configure-docker-agent.groovy \\
  "\$JENKINS_HOST/scriptText" \\
  --user \$JENKINS_USER:\$ADMIN_PASSWORD
EOL

chmod +x /home/ec2-user/setup-jenkins.sh

# Start Jenkins and run setup scripts
cd /home/ec2-user && docker-compose up -d

# Wait for Jenkins to start and run the install plugins script
(sleep 120 && cd /home/ec2-user && ./install-plugins.sh && sleep 120 && ./setup-jenkins.sh) &
"""