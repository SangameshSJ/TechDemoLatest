FROM jenkins/agent:latest
USER root

# Install required tools
RUN apt-get update && apt-get install -y \
    curl \
    git \
    docker.io \
    awscli \
    python3-pip

# Install Pulumi
RUN curl -fsSL https://get.pulumi.com | sh

# Install Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Add Jenkins user to Docker group
RUN usermod -aG docker jenkins

USER jenkins