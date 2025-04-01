# import pulumi
# import pulumi_aws as aws


# def create_load_balancer(vpc_id, public_subnet_ids, app_instance_ids, security_groups):
#     config = pulumi.Config()
#     environment = config.get("environment")
#     domain_name = config.get("domain_name")
#     hosted_zone_id = config.get("hosted_zone_id")
    
#     # 1. Create Certificate
#     certificate = aws.acm.Certificate("app-cert",
#         domain_name=domain_name,
#         validation_method="DNS",
#         tags={"Name": f"{environment}-app-cert"},
#         opts=pulumi.ResourceOptions(protect=False))
    
#     # 2. Create Validation Record - PROPERLY HANDLED OUTPUTS
#     cert_dvo = certificate.domain_validation_options[0]
    
#     cert_validation_record = aws.route53.Record("cert-validation",
#         zone_id=hosted_zone_id,
#         name=cert_dvo.resource_record_name,
#         type=cert_dvo.resource_record_type,
#         records=[cert_dvo.resource_record_value],
#         ttl=300,
#         opts=pulumi.ResourceOptions(depends_on=[certificate]))
    
#     # 3. Wait for Validation
#     cert_validation = aws.acm.CertificateValidation("cert-validation",
#         certificate_arn=certificate.arn,
#         validation_record_fqdns=[cert_validation_record.fqdn],
#         opts=pulumi.ResourceOptions(
#             custom_timeouts=pulumi.CustomTimeouts(create="15m"),
#             depends_on=[cert_validation_record]))

#     # Application Load Balancer
#     app_lb = aws.lb.LoadBalancer("app-lb",
#         internal=False,
#         load_balancer_type="application",
#         security_groups=[security_groups["alb_sg"].id],
#         subnets=public_subnet_ids,
#         enable_deletion_protection=False,
#         tags={
#             "Name": config.get("alb_name") or f"{environment}-app-lb",
#         })

#     # Target Group
#     target_group = aws.lb.TargetGroup("app-tg",
#         port=80,
#         protocol="HTTP",
#         vpc_id=vpc_id,
#         target_type="instance",
#         health_check={
#             "enabled": True,
#             "path": "/",
#             "port": "traffic-port",
#             "protocol": "HTTP",
#             "healthy_threshold": 3,
#             "unhealthy_threshold": 3,
#             "timeout": 5,
#             "interval": 30,
#         },
#         tags={
#             "Name": config.get("target_group_name") or f"{environment}-app-tg",
#         })

#     # Attach instances to target group
#     for i, instance_id in enumerate(app_instance_ids):
#         target_attachment = aws.lb.TargetGroupAttachment(f"app-tg-attachment-{i}",
#             target_group_arn=target_group.arn,
#             target_id=instance_id,
#             port=80)

#     # HTTP Listener (Redirect to HTTPS)
#     http_listener = aws.lb.Listener("http-listener",
#         load_balancer_arn=app_lb.arn,
#         port=80,
#         default_actions=[{
#             "type": "redirect",
#             "redirect": {
#                 "port": "443",
#                 "protocol": "HTTPS",
#                 "status_code": "HTTP_301"
#             }
#         }])

#     # HTTPS Listener
#     https_listener = aws.lb.Listener("https-listener",
#         load_balancer_arn=app_lb.arn,
#         port=443,
#         protocol="HTTPS",
#         ssl_policy="ELBSecurityPolicy-2016-08",
#         certificate_arn=cert_validation.certificate_arn,
#         default_actions=[{"type": "forward", "target_group_arn": target_group.arn}],
#         opts=pulumi.ResourceOptions(depends_on=[cert_validation]))

#     # Security Group Rule for Application Instances
#     app_sg_ingress_rule = aws.ec2.SecurityGroupRule("app-sg-alb-ingress",
#         type="ingress",
#         from_port=80,
#         to_port=80,
#         protocol="tcp",
#         security_group_id=security_groups["app_sg"].id,
#         source_security_group_id=security_groups["alb_sg"].id)

#     return {
#         "app_lb": app_lb,
#         "target_group": target_group,
#         "http_listener": http_listener,
#         "https_listener": https_listener,
#         "certificate": certificate
#     }


import pulumi
import pulumi_aws as aws

def create_load_balancer(vpc_id, public_subnet_ids, app_instance_ids, security_groups):
    """
    Creates an Application Load Balancer and related resources.
    
    This function creates:
    - An Application Load Balancer in public subnets
    - Target groups for the application instances
    - Listeners for HTTP and HTTPS traffic
    - Proper health checks for the applications
    
    Args:
        vpc_id (str): The VPC ID where the load balancer will be created
        public_subnet_ids (list): List of public subnet IDs for the load balancer
        app_instance_ids (list): List of application instance IDs to add to target groups
        security_groups (dict): Security groups to reference
        
    Returns:
        dict: Dictionary containing all created load balancer resources
    """

    alb_sg = aws.ec2.SecurityGroup("alb-sg",
        vpc_id=vpc_id,
        description="Allow HTTP/HTTPS traffic to the load balancer",
        ingress=[
            {
                "protocol": "tcp",
                "from_port": 80,
                "to_port": 80,
                "cidr_blocks": ["0.0.0.0/0"],
            },
            {
                "protocol": "tcp",
                "from_port": 443,
                "to_port": 443,
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
            "Name": config.get("alb_sg_name") or f"{environment}-alb-sg",
        })
    

    app_lb = aws.lb.LoadBalancer("app-lb",
        internal=False,
        load_balancer_type="application",
        security_groups=[alb_sg.id],
        subnets=public_subnet_ids,
        enable_deletion_protection=False,
        tags={
            "Name": config.get("alb_name") or f"{environment}-app-lb",
        })
    

    target_group = aws.lb.TargetGroup("app-tg",
        port=80,
        protocol="HTTP",
        vpc_id=vpc_id,
        target_type="instance",
        health_check={
            "enabled": True,
            "path": "/",
            "port": "traffic-port",
            "protocol": "HTTP",
            "healthy_threshold": 3,
            "unhealthy_threshold": 3,
            "timeout": 5,
            "interval": 30,
        },
        tags={
            "Name": config.get("target_group_name") or f"{environment}-app-tg",
        })
    

    for i, instance_id in enumerate(app_instance_ids):
        target_attachment = aws.lb.TargetGroupAttachment(f"app-tg-attachment-{i}",
            target_group_arn=target_group.arn,
            target_id=instance_id,
            port=80)
    

    http_listener = aws.lb.Listener("http-listener",
        load_balancer_arn=app_lb.arn,
        port=80,
        default_actions=[{
            "type": "forward",
            "target_group_arn": target_group.arn,
        }])
    

    app_sg_ingress_rule = aws.ec2.SecurityGroupRule("app-sg-alb-ingress",
        type="ingress",
        from_port=80,
        to_port=80,
        protocol="tcp",
        security_group_id=security_groups["app_sg"].id,
        source_security_group_id=alb_sg.id)
    
    return {
        "app_lb": app_lb,
        "target_group": target_group,
        "http_listener": http_listener,
        "alb_sg": alb_sg
    }