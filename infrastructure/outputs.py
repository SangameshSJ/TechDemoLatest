# infrastructure/outputs.py
import pulumi
import json

def export_outputs(vpc, bastion_instance, jenkins_instance, app1_instance, app2_instance, key_name):
    outputs = {
        "vpc_id": vpc.id,
        "bastion_public_ip": bastion_instance.public_ip,
        "jenkins_public_ip": jenkins_instance.public_ip,
        "app1_private_ip": app1_instance.private_ip,
        "app2_private_ip": app2_instance.private_ip,
        "ssh_command": pulumi.Output.concat("ssh -i ", key_name, ".pem ec2-user@", bastion_instance.public_ip)
    }
    
    # Export outputs to a JSON file
    pulumi.export("outputs", outputs)
    with open("outputs.json", "w") as f:
        json.dump(outputs, f)