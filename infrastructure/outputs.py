import pulumi
import json

def export_outputs(vpc, bastion_instance, jenkins_instance, app1_instance, app2_instance, key_name, app_lb=None):
    """
    Export infrastructure outputs to a JSON file and as Pulumi stack outputs
    
    Args:
        vpc (pulumi.aws.ec2.Vpc): The VPC resource
        bastion_instance (pulumi.aws.ec2.Instance): Bastion host instance
        jenkins_instance (pulumi.aws.ec2.Instance): Jenkins instance
        app1_instance (pulumi.aws.ec2.Instance): First application instance
        app2_instance (pulumi.aws.ec2.Instance): Second application instance
        key_name (str): SSH key name
        app_lb (pulumi.aws.lb.LoadBalancer, optional): Application Load Balancer
    """
    # Function to safely convert Pulumi Output to string
    def safe_output_convert(output):
        try:
            return output.apply(str)
        except:
            return output

    # Export VPC details
    pulumi.export("vpc_id", vpc.id)
    pulumi.export("vpc_cidr", vpc.cidr_block)

    # Export instance details
    pulumi.export("bastion_public_ip", bastion_instance.public_ip)
    pulumi.export("bastion_private_ip", bastion_instance.private_ip)
    pulumi.export("jenkins_public_ip", jenkins_instance.public_ip)
    pulumi.export("jenkins_private_ip", jenkins_instance.private_ip)
    pulumi.export("app1_private_ip", app1_instance.private_ip)
    pulumi.export("app2_private_ip", app2_instance.private_ip)

    # Export load balancer details if provided
    if app_lb:
        pulumi.export("app_lb_dns_name", app_lb.dns_name)

    # Prepare outputs dictionary for JSON export
    def prepare_outputs():
        outputs = {
            "vpc_id": vpc.id,
            "vpc_cidr": vpc.cidr_block,
            "bastion_public_ip": bastion_instance.public_ip,
            "bastion_private_ip": bastion_instance.private_ip,
            "jenkins_public_ip": jenkins_instance.public_ip,
            "jenkins_private_ip": jenkins_instance.private_ip,
            "app1_private_ip": app1_instance.private_ip,
            "app2_private_ip": app2_instance.private_ip,
            "key_name": key_name
        }

        if app_lb:
            outputs["app_lb_dns_name"] = app_lb.dns_name

        return outputs

    # Use apply to resolve Pulumi Output values
    def write_outputs(resolved_outputs):
        with open('outputs.json', 'w') as f:
            json.dump(resolved_outputs, f, indent=4)

    # Combine the outputs resolution and file writing
    pulumi.Output.all(
        vpc.id, 
        bastion_instance.public_ip, 
        bastion_instance.private_ip,
        jenkins_instance.public_ip, 
        jenkins_instance.private_ip,
        app1_instance.private_ip, 
        app2_instance.private_ip
    ).apply(lambda _: write_outputs(prepare_outputs()))