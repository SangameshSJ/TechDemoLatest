# infrastructure/compute.py

import pulumi
import pulumi_aws as aws
from infrastructure.config import instance_type, key_name, ami, bastion_user_data, app_user_data, jenkins_user_data

def create_compute_resources(network, security_groups, instance_profile):
    # Create the bastion host
    bastion_instance = aws.ec2.Instance("bastion-host",
        ami=ami.id,
        instance_type=instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["bastion_sg"].id],
        subnet_id=network["public_subnet"].id,
        iam_instance_profile=instance_profile.name,
        user_data=bastion_user_data,
        tags={
            "Name": "bastion-host",
        })

    # Create the application instances
    app1_instance = aws.ec2.Instance("app1-instance",
        ami=ami.id,
        instance_type=instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["app_sg"].id],
        subnet_id=network["app1_subnet"].id,
        iam_instance_profile=instance_profile.name,
        user_data=app_user_data,
        tags={
            "Name": "app1-instance",
        })

    app2_instance = aws.ec2.Instance("app2-instance",
        ami=ami.id,
        instance_type=instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["app_sg"].id],
        subnet_id=network["app2_subnet"].id,
        iam_instance_profile=instance_profile.name,
        user_data=app_user_data,
        tags={
            "Name": "app2-instance",
        })

    # Create the Jenkins instance
    jenkins_instance = aws.ec2.Instance("jenkins-instance",
        ami=ami.id,
        instance_type="t3.small",  # Jenkins needs more resources with Docker
        key_name=key_name,
        vpc_security_group_ids=[security_groups["jenkins_sg"].id],
        subnet_id=network["public_subnet"].id,  # Jenkins in public subnet for easy access
        iam_instance_profile=instance_profile.name,
        user_data=jenkins_user_data,
        tags={
            "Name": "jenkins-instance",
        })

    return {
        "bastion_instance": bastion_instance,
        "app1_instance": app1_instance,
        "app2_instance": app2_instance,
        "jenkins_instance": jenkins_instance
    }