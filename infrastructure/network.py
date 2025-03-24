import pulumi
import pulumi_aws as aws
from infrastructure.config import region, cidr_block


def create_network_infrastructure():
    """
    Creates the network infrastructure for the application.
    
    This function creates:
    - A VPC with DNS support
    - An Internet Gateway for public subnet access
    - A public subnet for bastion and Jenkins hosts
    - Two private subnets for application instances
    - A NAT Gateway for private subnet internet access
    - Route tables for both public and private subnets
    
    Returns:
        dict: Dictionary containing all created network resources
    """
    config = pulumi.Config()
    environment = config.get("environment")

    vpc = aws.ec2.Vpc("bastion-vpc",
        cidr_block=cidr_block,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={
            "Name": config.get("vpc_name") or f"{environment}-vpc",
        })


    igw = aws.ec2.InternetGateway("bastion-igw",
        vpc_id=vpc.id,
        tags={
            "Name": config.get("igw_name") or f"{environment}-igw",
        })


    public_subnet = aws.ec2.Subnet("bastion-public-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.1.0/24",
        availability_zone=f"{region}a",
        map_public_ip_on_launch=True,
        tags={
            "Name": config.get("public_subnet_name") or f"{environment}-public-subnet",
        })


    public_subnet2 = aws.ec2.Subnet("bastion-public-subnet2",
        vpc_id=vpc.id,
        cidr_block="10.0.4.0/24",
        availability_zone=f"{region}b",
        map_public_ip_on_launch=True,
        tags={
            "Name": config.get("public_subnet2_name") or f"{environment}-public-subnet-2",
        })
    
    
    app1_subnet = aws.ec2.Subnet("app1-private-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.2.0/24",
        availability_zone=f"{region}a",
        tags={
            "Name": config.get("app1_subnet_name") or f"{environment}-app1-private-subnet",
        })


    app2_subnet = aws.ec2.Subnet("app2-private-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.3.0/24",
        availability_zone=f"{region}b",
        tags={
            "Name": config.get("app2_subnet_name") or f"{environment}-app2-private-subnet",
        })


    eip = aws.ec2.Eip("nat-eip",
        vpc=True)


    nat_gateway = aws.ec2.NatGateway("bastion-nat",
        allocation_id=eip.id,
        subnet_id=public_subnet.id,
        tags={
            "Name": config.get("nat_name") or f"{environment}-nat",
        })


    public_route_table = aws.ec2.RouteTable("public-rt",
        vpc_id=vpc.id,
        routes=[{
            "cidr_block": "0.0.0.0/0",
            "gateway_id": igw.id,
        }],
        tags={
            "Name": config.get("public_rt_name") or f"{environment}-public-rt",
        })
      
    private_route_table = aws.ec2.RouteTable("private-rt",
        vpc_id=vpc.id,
        routes=[{
            "cidr_block": "0.0.0.0/0",
            "nat_gateway_id": nat_gateway.id,
        }],
        tags={
            "Name": config.get("private_rt_name") or f"{environment}-private-rt",
        })


    public_rt_assoc = aws.ec2.RouteTableAssociation("public-rt-assoc",
        subnet_id=public_subnet.id,
        route_table_id=public_route_table.id)


    public_rt_assoc2 = aws.ec2.RouteTableAssociation("public-rt-assoc2",
        subnet_id=public_subnet2.id,
        route_table_id=public_route_table.id)


    app1_rt_assoc = aws.ec2.RouteTableAssociation("app1-rt-assoc",
        subnet_id=app1_subnet.id,
        route_table_id=private_route_table.id)


    app2_rt_assoc = aws.ec2.RouteTableAssociation("app2-rt-assoc",
        subnet_id=app2_subnet.id,
        route_table_id=private_route_table.id)


    return {
        "vpc": vpc,
        "public_subnet": public_subnet,
        "public_subnet2": public_subnet2,
        "app1_subnet": app1_subnet,
        "app2_subnet": app2_subnet
    }