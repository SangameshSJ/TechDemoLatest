import pulumi
import json

def export_outputs(vpc, bastion_instance, jenkins_instance, app1_instance, app2_instance, key_name, app_lb=None):
    # Determine whether to use app_lb's DNS name or None
    lb_dns = app_lb.dns_name if app_lb else None

    # Use `pulumi.Output.all` to resolve multiple outputs at once
    resolved_outputs = pulumi.Output.all(
        vpc_id=vpc.id,
        bastion_public_ip=bastion_instance.public_ip,
        jenkins_public_ip=jenkins_instance.public_ip,
        app1_private_ip=app1_instance.private_ip,
        app2_private_ip=app2_instance.private_ip,
        ssh_command=pulumi.Output.concat("ssh -i ", key_name, ".pem ec2-user@", bastion_instance.public_ip),
        app_lb_dns=lb_dns
    )

    # Export the resolved outputs
    resolved_outputs.apply(lambda outputs: pulumi.export("outputs", outputs))

    # Write the resolved outputs to a JSON file
    resolved_outputs.apply(lambda outputs: write_outputs_to_file(outputs))

def write_outputs_to_file(outputs):
    with open("outputs.json", "w") as f:
        json.dump(outputs, f)