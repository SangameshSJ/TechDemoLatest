import pulumi
import json

def export_outputs(vpc, bastion_instance, jenkins_instance, app1_instance, app2_instance, load_balancer, key_name, environment):
    """
    Exports the outputs of the Pulumi stack.
    
    This function:
    - Exports key infrastructure information as Pulumi stack outputs
    - Saves the outputs to an environment-specific JSON file for reference
    
    Args:
        vpc (Vpc): The VPC resource
        bastion_instance (Instance): The bastion host EC2 instance
        jenkins_instance (Instance): The Jenkins EC2 instance
        app1_instance (Instance): The first application EC2 instance
        app2_instance (Instance): The second application EC2 instance
        load_balancer (LoadBalancer): The Application Load Balancer
        key_name (str): The SSH key name used for the instances
        environment (str): The environment name (staging/production)
    """
    resolved_outputs = pulumi.Output.all(
        vpc_id=vpc.id,
        bastion_public_ip=bastion_instance.public_ip,
        jenkins_public_ip=jenkins_instance.public_ip,
        app1_private_ip=app1_instance.private_ip,
        app2_private_ip=app2_instance.private_ip,
        app_endpoint=load_balancer.dns_name,
        ssh_command=pulumi.Output.concat("ssh -i ", key_name, ".pem ec2-user@", bastion_instance.public_ip),
        environment=environment
    )

    resolved_outputs.apply(lambda outputs: pulumi.export("outputs", outputs))

    # Write to environment-specific file
    resolved_outputs.apply(lambda outputs: write_outputs_to_file(outputs, environment))

def write_outputs_to_file(outputs, environment):
    """
    Writes infrastructure outputs to an environment-specific JSON file.
    
    Args:
        outputs (dict): Dictionary of output values to write to file
        environment (str): The environment name for the filename
    """
    with open(f"{environment}-outputs.json", "w") as f:
        json.dump(outputs, f)