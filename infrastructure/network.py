# infrastructure/network.py

import pulumi
import pulumi_aws as aws
from infrastructure.config import region, cidr_block

def create_network_infrastructure():
    # Create a VPC
    vpc = aws.ec2.Vpc("bastion-vpc",
        cidr_block=cidr_block,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={
            "Name": "bastion-vpc",
        })

    # Create an Internet Gateway
    igw = aws.ec2.InternetGateway("bastion-igw",
        vpc_id=vpc.id,
        tags={
            "Name": "bastion-igw",
        })

    # Create a public subnet for the bastion host
    public_subnet = aws.ec2.Subnet("bastion-public-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.1.0/24",
        availability_zone=f"{region}a",
        map_public_ip_on_launch=True,
        tags={
            "Name": "bastion-public-subnet",
        })

    # Create private subnets for the applications
    app1_subnet = aws.ec2.Subnet("app1-private-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.2.0/24",
        availability_zone=f"{region}a",
        tags={
            "Name": "app1-private-subnet",
        })

    app2_subnet = aws.ec2.Subnet("app2-private-subnet",
        vpc_id=vpc.id,
        cidr_block="10.0.3.0/24",
        availability_zone=f"{region}b",
        tags={
            "Name": "app2-private-subnet",
        })

    # Create a NAT Gateway for the private subnets
    eip = aws.ec2.Eip("nat-eip",
        vpc=True)

    nat_gateway = aws.ec2.NatGateway("bastion-nat",
        allocation_id=eip.id,
        subnet_id=public_subnet.id,
        tags={
            "Name": "bastion-nat",
        })

    # Create route tables
    public_route_table = aws.ec2.RouteTable("public-rt",
        vpc_id=vpc.id,
        routes=[{
            "cidr_block": "0.0.0.0/0",
            "gateway_id": igw.id,
        }],
        tags={
            "Name": "public-rt",
        })
        
    private_route_table = aws.ec2.RouteTable("private-rt",
        vpc_id=vpc.id,
        routes=[{
            "cidr_block": "0.0.0.0/0",
            "nat_gateway_id": nat_gateway.id,
        }],
        tags={
            "Name": "private-rt",
        })

    # Associate route tables with subnets
    public_rt_assoc = aws.ec2.RouteTableAssociation("public-rt-assoc",
        subnet_id=public_subnet.id,
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
        "app1_subnet": app1_subnet,
        "app2_subnet": app2_subnet
    }