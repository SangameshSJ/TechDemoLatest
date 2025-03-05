import pulumi
import pulumi_aws as aws
from infrastructure.config import region, cidr_block

def create_network_infrastructure(security_groups, bastion_instance=None):
    # Create a VPC with a unique name
    vpc = aws.ec2.Vpc("tech-project-main-vpc",  # More specific name
        cidr_block=cidr_block,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={
            "Name": "tech-project-main-vpc",
        })

    # Create an Internet Gateway
    igw = aws.ec2.InternetGateway("tech-project-igw",  # Changed name
        vpc_id=vpc.id,
        tags={
            "Name": "tech-project-igw",
        })

    # Create a public subnet for the bastion host
    public_subnet = aws.ec2.Subnet("tech-project-public-subnet",  # Changed name
        vpc_id=vpc.id,
        cidr_block="10.0.1.0/24",
        availability_zone=f"{region}a",
        map_public_ip_on_launch=True,
        tags={
            "Name": "tech-project-public-subnet",
        })

    # Create private subnets for the applications
    app1_subnet = aws.ec2.Subnet("tech-project-app1-private-subnet",  # Changed name
        vpc_id=vpc.id,
        cidr_block="10.0.2.0/24",
        availability_zone=f"{region}a",
        tags={
            "Name": "tech-project-app1-private-subnet",
        })

    app2_subnet = aws.ec2.Subnet("tech-project-app2-private-subnet",  # Changed name
        vpc_id=vpc.id,
        cidr_block="10.0.3.0/24",
        availability_zone=f"{region}b",
        tags={
            "Name": "tech-project-app2-private-subnet",
        })

    # Create a NAT Gateway for the private subnets
    nat_eip = aws.ec2.Eip("tech-project-nat-eip",
        tags={
            "Name": "Tech Project NAT Gateway EIP"
        })

    nat_gateway = aws.ec2.NatGateway("tech-project-nat",  # Changed name
        allocation_id=nat_eip.id,
        subnet_id=public_subnet.id,
        tags={
            "Name": "tech-project-nat",
        })

    # Create Elastic IP for bastion host (only if instance is provided)
    bastion_eip = None
    if bastion_instance:
        bastion_eip = aws.ec2.Eip("tech-project-bastion-eip",
            instance=bastion_instance.id,
            tags={
                "Name": "Tech Project Bastion Host EIP"
            })

    # Create route tables
    public_route_table = aws.ec2.RouteTable("tech-project-public-rt",  # Changed name
        vpc_id=vpc.id,
        routes=[{
            "cidr_block": "0.0.0.0/0",
            "gateway_id": igw.id,
        }],
        tags={
            "Name": "tech-project-public-rt",
        })
        
    private_route_table = aws.ec2.RouteTable("tech-project-private-rt",  # Changed name
        vpc_id=vpc.id,
        routes=[{
            "cidr_block": "0.0.0.0/0",
            "nat_gateway_id": nat_gateway.id,
        }],
        tags={
            "Name": "tech-project-private-rt",
        })

    # Associate route tables with subnets
    public_rt_assoc = aws.ec2.RouteTableAssociation("tech-project-public-rt-assoc",  # Changed name
        subnet_id=public_subnet.id,
        route_table_id=public_route_table.id)

    app1_rt_assoc = aws.ec2.RouteTableAssociation("tech-project-app1-rt-assoc",  # Changed name
        subnet_id=app1_subnet.id,
        route_table_id=private_route_table.id)

    app2_rt_assoc = aws.ec2.RouteTableAssociation("tech-project-app2-rt-assoc",  # Changed name
        subnet_id=app2_subnet.id,
        route_table_id=private_route_table.id)

    # Create Target Group for App Instances (shortened name)
    app_target_group = aws.lb.TargetGroup("app-tg",  # Significantly shortened name
        vpc_id=vpc.id,
        port=80,
        protocol="HTTP",
        target_type="instance",
        health_check={
            "enabled": True,
            "path": "/",
            "healthy_threshold": 3,
            "unhealthy_threshold": 3,
            "timeout": 5,
            "interval": 30,
            "matcher": "200-399"
        })

    # Create Application Load Balancer (using security group if provided)
    lb_security_group_id = security_groups.get("app_lb_sg").id if security_groups else None
    
    app_lb = aws.lb.LoadBalancer("tech-project-app-lb",  # Shortened load balancer name
        internal=False,  # Public-facing
        load_balancer_type="application",
        security_groups=[lb_security_group_id] if lb_security_group_id else [],
        subnets=[public_subnet.id, app2_subnet.id],
        tags={
            "Name": "tech-project-application-load-balancer"
        })

    # Create ALB Listener
    app_listener = aws.lb.Listener("tech-project-app-listener",  # Changed name
        load_balancer_arn=app_lb.arn,
        port=80,
        default_actions=[{
            "type": "forward",
            "target_group_arn": app_target_group.arn
        }])

    return {
        "vpc": vpc,
        "public_subnet": public_subnet,
        "app1_subnet": app1_subnet,
        "app2_subnet": app2_subnet,
        "app_target_group": app_target_group,
        "app_lb": app_lb,
        "nat_eip": nat_eip,
        "bastion_eip": bastion_eip
    }