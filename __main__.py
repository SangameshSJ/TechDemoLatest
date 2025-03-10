# infrastructure/__main__.py

import pulumi
import pulumi_aws as aws


from infrastructure.config import key_name
from infrastructure.network import create_network_infrastructure
from infrastructure.security import create_security_groups
from infrastructure.iam import create_iam_resources
from infrastructure.compute import create_compute_resources
from infrastructure.monitoring import create_monitoring_resources
from infrastructure.outputs import export_outputs


"""
Main Pulumi program file that orchestrates the creation of all infrastructure components.

This program implements a secure multi-tier architecture with:
- A bastion host for secure SSH access
- Private application servers in multiple availability zones
- A Jenkins CI/CD server for deployment automation
- Complete monitoring and logging via CloudWatch
- Proper IAM permissions for all components

The architecture follows AWS best practices for security, scalability, and resilience.
"""

network = create_network_infrastructure()

security_groups = create_security_groups(network["vpc"].id)

iam_resources = create_iam_resources()

compute = create_compute_resources(
    network=network,
    security_groups=security_groups,
    instance_profile=iam_resources["instance_profile"]
)

monitoring = create_monitoring_resources(compute)

export_outputs(
    vpc=network["vpc"],
    bastion_instance=compute["bastion_instance"],
    jenkins_instance=compute["jenkins_instance"],
    app1_instance=compute["app1_instance"],
    app2_instance=compute["app2_instance"],
    key_name=key_name
)