# import pulumi
# import pulumi_aws as aws




# def create_security_groups(vpc_id):
#    """
#    Creates security groups for the infrastructure.
  
#    This function creates three security groups:
#    - Bastion SG: Allows SSH access from the internet
#    - Application SG: Allows SSH from bastion and HTTP/HTTPS from anywhere
#    - Jenkins SG: Allows SSH from bastion and web access on port 8080
  
#    Args:
#        vpc_id (str): The ID of the VPC to create security groups in
      
#    Returns:
#        dict: Dictionary containing all created security group resources
#    """
#    config = pulumi.Config()
#    environment = config.get("environment")
  
#    bastion_sg = aws.ec2.SecurityGroup("bastion-sg",
#        vpc_id=vpc_id,
#        description="Allow SSH access to the bastion host",
#        ingress=[{
#            "protocol": "tcp",
#            "from_port": 22,
#            "to_port": 22,
#            "cidr_blocks": ["0.0.0.0/0"],
#        }],
#        egress=[{
#            "protocol": "-1",
#            "from_port": 0,
#            "to_port": 0,
#            "cidr_blocks": ["0.0.0.0/0"],
#        }],
#        tags={
#            "Name": config.get("bastion_sg_name") or f"{environment}-bastion-sg",
#        })




#    app_sg = aws.ec2.SecurityGroup("app-sg",
#        vpc_id=vpc_id,
#        description="Allow access to application instances",
#        ingress=[
#            {
#                "protocol": "tcp",
#                "from_port": 22,
#                "to_port": 22,
#                "security_groups": [bastion_sg.id],
#            }
#        ],
#        egress=[{
#            "protocol": "-1",
#            "from_port": 0,
#            "to_port": 0,
#            "cidr_blocks": ["0.0.0.0/0"],
#        }],
#        tags={
#            "Name": config.get("app_sg_name") or f"{environment}-app-sg",
#        })




#    jenkins_sg = aws.ec2.SecurityGroup("jenkins-sg",
#        vpc_id=vpc_id,
#        description="Allow access to Jenkins",
#        ingress=[
#            {
#                "protocol": "tcp",
#                "from_port": 22,
#                "to_port": 22,
#                "security_groups": [bastion_sg.id],
#            },
#            {
#                "protocol": "tcp",
#                "from_port": 8080,
#                "to_port": 8080,
#                "cidr_blocks": ["0.0.0.0/0"],
#            }
#        ],
#        egress=[{
#            "protocol": "-1",
#            "from_port": 0,
#            "to_port": 0,
#            "cidr_blocks": ["0.0.0.0/0"],
#        }],
#        tags={
#            "Name": config.get("jenkins_sg_name") or f"{environment}-jenkins-sg",
#        })




#    alb_sg = aws.ec2.SecurityGroup("alb-sg",
#        vpc_id=vpc_id,
#        description="Allow HTTP/HTTPS traffic to the load balancer",
#        ingress=[
#            {
#                "protocol": "tcp",
#                "from_port": 80,
#                "to_port": 80,
#                "cidr_blocks": ["0.0.0.0/0"],
#            },
#            {
#                "protocol": "tcp",
#                "from_port": 443,
#                "to_port": 443,
#                "cidr_blocks": ["0.0.0.0/0"],
#            }
#        ],
#        egress=[{
#            "protocol": "-1",
#            "from_port": 0,
#            "to_port": 0,
#            "cidr_blocks": ["0.0.0.0/0"],
#        }],
#        tags={
#            "Name": config.get("alb_sg_name") or f"{environment}-alb-sg",
#        })




#    return {
#        "bastion_sg": bastion_sg,
#        "app_sg": app_sg,
#        "jenkins_sg": jenkins_sg,
#        "alb_sg": alb_sg
#    }





import pulumi
import pulumi_aws as aws


def create_security_groups(vpc_id):
    """
    Creates security groups for the infrastructure.
    
    This function creates three security groups:
    - Bastion SG: Allows SSH access from the internet
    - Application SG: Allows SSH from bastion and HTTP/HTTPS from anywhere
    - Jenkins SG: Allows SSH from bastion and web access on port 8080
    
    Args:
        vpc_id (str): The ID of the VPC to create security groups in
        
    Returns:
        dict: Dictionary containing all created security group resources
    """
    config = pulumi.Config()
    environment = config.get("environment")
    
    bastion_sg = aws.ec2.SecurityGroup("bastion-sg",
        vpc_id=vpc_id,
        description="Allow SSH access to the bastion host",
        ingress=[{
            "protocol": "tcp",
            "from_port": 22,
            "to_port": 22,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        egress=[{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        tags={
            "Name": config.get("bastion_sg_name") or f"{environment}-bastion-sg",
        })


    app_sg = aws.ec2.SecurityGroup("app-sg",
        vpc_id=vpc_id,
        description="Allow access to application instances",
        ingress=[
            {
                "protocol": "tcp",
                "from_port": 22,
                "to_port": 22,
                "security_groups": [bastion_sg.id],
            }
        ],
        egress=[{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        tags={
            "Name": config.get("app_sg_name") or f"{environment}-app-sg",
        })


    jenkins_sg = aws.ec2.SecurityGroup("jenkins-sg",
        vpc_id=vpc_id,
        description="Allow access to Jenkins",
        ingress=[
            {
                "protocol": "tcp",
                "from_port": 22,
                "to_port": 22,
                "security_groups": [bastion_sg.id],
            },
            {
                "protocol": "tcp",
                "from_port": 8080,
                "to_port": 8080,
                "cidr_blocks": ["0.0.0.0/0"],
            }
        ],
        egress=[{
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
        }],
        tags={
            "Name": config.get("jenkins_sg_name") or f"{environment}-jenkins-sg",
        })


    return {
        "bastion_sg": bastion_sg,
        "app_sg": app_sg,
        "jenkins_sg": jenkins_sg
    }