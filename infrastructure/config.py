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

# Create init.groovy.d directory for startup scripts
mkdir -p /var/jenkins_home/init.groovy.d

# Create a script to configure Docker agents
cat > /var/jenkins_home/init.groovy.d/configure-docker-agents.groovy <<EOL
import jenkins.model.*
import hudson.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.common.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.jenkins.plugins.sshcredentials.impl.*
import hudson.plugins.sshslaves.*
import hudson.plugins.sshslaves.verifiers.*
import hudson.slaves.*
import hudson.slaves.EnvironmentVariablesNodeProperty.Entry
import org.jenkinsci.plugins.docker.workflow.*
import io.jenkins.docker.client.*
import io.jenkins.docker.connector.*
import io.jenkins.docker.connector.DockerComputerAttachConnector.DockerComputerAttachConnectorDescriptor

// Configure Docker Cloud
def instance = Jenkins.getInstance()

// Wait for plugins to load
Thread.sleep(10000)

try {
    // Attempt to load Docker plugin classes
    def dockerClass = io.jenkins.docker.client.DockerAPI.class
    def dockerCloudClass = io.jenkins.docker.DockerCloud.class
    
    // Create Docker cloud configuration
    def dockerApi = new io.jenkins.docker.client.DockerAPI(new io.jenkins.docker.client.DockerServerEndpoint("unix:///var/run/docker.sock", null))
    
    // Create Docker template
    def template = new io.jenkins.docker.DockerTemplate(
        "jenkins/agent:latest",
        new io.jenkins.docker.connector.DockerComputerAttachConnector(),
        io.jenkins.docker.DockerTemplate.DescriptorImpl.DEFAULT_LABELS,
        "/home/jenkins/agent",
        "/usr/local/bin/jenkins-agent"
    )
    
    template.setLabelString("docker-agent")
    template.setPullTimeout(300)
    template.setRemoteFs("/home/jenkins/agent")
    template.setInstanceCapStr("5")
    template.setMode(Node.Mode.EXCLUSIVE)
    
    // Add volume mount for Docker socket
    def volumeList = new ArrayList<io.jenkins.docker.DockerTemplate.VolumeConfiguration>()
    volumeList.add(new io.jenkins.docker.DockerTemplate.VolumeConfiguration("/var/run/docker.sock", "/var/run/docker.sock"))
    template.setVolumes(volumeList)
    
    // Create Docker cloud with template
    def dockerCloud = new io.jenkins.docker.DockerCloud(
        "docker", 
        new ArrayList<io.jenkins.docker.DockerTemplate>(Arrays.asList(template)),
        10,
        dockerApi
    )
    
    // Add cloud to Jenkins
    def clouds = instance.clouds
    clouds.add(dockerCloud)
    instance.save()
    println("Docker agent cloud configured successfully")
} catch (Exception e) {
    println("Error configuring Docker cloud: " + e.message)
    e.printStackTrace()
}
EOL

# Create init script to install plugins
cat > /var/jenkins_home/init.groovy.d/install-plugins.groovy <<EOL
import jenkins.model.*
import hudson.util.*
import jenkins.install.*
import jenkins.security.s2m.*

def jenkins = Jenkins.getInstance()

// Skip initial setup wizard
jenkins.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)

// Set to LegacySecurityRealm to accept the initial admin user
def realm = jenkins.getSecurityRealm()
if (realm instanceof hudson.security.SecurityRealm) {
    // Skip the setup wizard entirely
    jenkins.setInstallState(InstallState.INITIAL_SETUP_COMPLETED)
}

// Disable CLI over Remoting
jenkins.getDescriptor("jenkins.CLI").get().setEnabled(false)

// Enable security warnings
AdminWhitelistRule.enabled = true

// Save the configurations
jenkins.save()
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
      - /usr/local/bin/docker-compose:/usr/local/bin/docker-compose
    environment:
      - JENKINS_OPTS="--prefix=/jenkins"
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
EOL

# Create script to install needed plugins
cat > /home/ec2-user/install-plugins.sh <<EOL
#!/bin/bash
# Wait for Jenkins to become available
echo "Waiting for Jenkins to start..."
until curl -s http://localhost:8080 > /dev/null; do
    sleep 10
done

# Get the Jenkins CLI jar
echo "Downloading Jenkins CLI..."
curl -s -o /tmp/jenkins-cli.jar http://localhost:8080/jnlpJars/jenkins-cli.jar

# Get initial admin password
ADMIN_PWD=\$(cat /var/jenkins_home/secrets/initialAdminPassword)

# Install necessary plugins
echo "Installing plugins..."
java -jar /tmp/jenkins-cli.jar -s http://localhost:8080/ -auth admin:\$ADMIN_PWD install-plugin \
    docker-plugin \
    docker-workflow \
    workflow-aggregator \
    git \
    ssh-agent \
    pipeline-utility-steps \
    credentials-binding

# Restart Jenkins to apply changes
echo "Restarting Jenkins..."
java -jar /tmp/jenkins-cli.jar -s http://localhost:8080/ -auth admin:\$ADMIN_PWD safe-restart
EOL

chmod +x /home/ec2-user/install-plugins.sh

# Start Jenkins using Docker Compose
cd /home/ec2-user && docker-compose up -d

# Start plugin installation in the background (after Jenkins has time to start)
(sleep 60 && /home/ec2-user/install-plugins.sh) &
"""