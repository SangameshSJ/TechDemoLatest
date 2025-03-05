import pulumi
from infrastructure.network import create_network_infrastructure
from infrastructure.security import create_security_groups
from infrastructure.iam import create_iam_resources
from infrastructure.compute import create_compute_resources
from infrastructure.outputs import export_outputs
from infrastructure.config import key_name

def main():
    # Create security groups first
    security_groups = create_security_groups(None)  # Pass None temporarily

    # Create network infrastructure 
    network = create_network_infrastructure(security_groups)
    
    # Update the VPC ID in security groups after network creation
    security_groups = create_security_groups(network["vpc"].id)

    # Create IAM resources
    iam_resources = create_iam_resources()

    # Create compute resources 
    compute_resources = create_compute_resources(
        network, 
        security_groups, 
        iam_resources["instance_profile"], 
        network.get("app_target_group")  # Use .get() to handle case where target group might not exist
    )

    # Export outputs
    export_outputs(
        network["vpc"], 
        compute_resources["bastion_instance"], 
        compute_resources["jenkins_instance"], 
        compute_resources["app1_instance"], 
        compute_resources["app2_instance"], 
        key_name,
        network.get("app_lb")  # Use .get() to handle case where load balancer might not exist
    )

# Ensure the program runs when the script is executed directly
if __name__ == "__main__":
    main()