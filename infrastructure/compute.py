import pulumi
import pulumi_aws as aws
from infrastructure.config import instance_type, key_name, ami, bastion_user_data, app_user_data, jenkins_user_data, jenkins_instance_type


def create_compute_resources(network, security_groups, instance_profile):
    """
    Creates EC2 instances for the application infrastructure.
    
    This function provisions four EC2 instances:
    - A bastion host in the public subnet for secure SSH access
    - Two application instances in private subnets
    - A Jenkins CI/CD server in the public subnet
    
    Args:
        network (dict): Dictionary containing network resources (subnets, VPC)
        security_groups (dict): Dictionary containing security group resources
        instance_profile (InstanceProfile): IAM instance profile for EC2 instances
        
    Returns:
        dict: Dictionary containing all created EC2 instance resources
    """
    
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


    jenkins_instance = aws.ec2.Instance("jenkins-instance",
        ami=ami.id,
        instance_type=jenkins_instance_type,
        key_name=key_name,
        vpc_security_group_ids=[security_groups["jenkins_sg"].id],
        subnet_id=network["public_subnet"].id,
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