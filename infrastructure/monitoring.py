# infrastructure/monitoring.py

import pulumi
import pulumi_aws as aws
import json


def create_monitoring_resources(compute_resources):
    """
    Creates CloudWatch monitoring resources for the infrastructure.
    
    This function creates:
    - CloudWatch Log Groups for each instance type
    - A CloudWatch Dashboard to visualize metrics
    - Log metric filters to track errors
    - CloudWatch Alarms to alert on error conditions
    
    Returns:
        dict: Dictionary containing all created monitoring resources
    """
    # Get instance IDs from compute resources
    bastion_id = compute_resources["bastion_instance"].id
    jenkins_id = compute_resources["jenkins_instance"].id
    app1_id = compute_resources["app1_instance"].id
    app2_id = compute_resources["app2_instance"].id

    # First, create the CloudWatch Log Groups
    jenkins_log_group = aws.cloudwatch.LogGroup("jenkins-instance-logs",
        name="jenkins-instance-logs",
        retention_in_days=7
    )
    
    app_log_group = aws.cloudwatch.LogGroup("app-instance-logs",
        name="app-instance-logs",
        retention_in_days=7
    )
    
    bastion_log_group = aws.cloudwatch.LogGroup("bastion-host-logs",
        name="bastion-host-logs",
        retention_in_days=7
    )
    
    # Create CloudWatch dashboard for overall monitoring
    # We'll use pulumi.Output.all to wait for all instance IDs to be resolved
    pulumi.Output.all(
        bastion_id=bastion_id, 
        jenkins_id=jenkins_id, 
        app1_id=app1_id, 
        app2_id=app2_id
    ).apply(
        lambda ids: create_dashboard(ids, app_log_group.name)
    )
    
    # Create log metric filters for error monitoring - now depending on the log groups
    jenkins_error_metric = aws.cloudwatch.LogMetricFilter("jenkins-error-metric",
        log_group_name=jenkins_log_group.name,
        pattern="ERROR",
        metric_transformation={
            "name": "JenkinsErrorCount",
            "namespace": "CustomMetrics",
            "value": "1"
        }
    )
    
    app_error_metric = aws.cloudwatch.LogMetricFilter("app-error-metric",
        log_group_name=app_log_group.name,
        pattern="ERROR",
        metric_transformation={
            "name": "AppErrorCount",
            "namespace": "CustomMetrics",
            "value": "1"
        }
    )
    
    # Create alarms based on error metrics
    jenkins_alarm = aws.cloudwatch.MetricAlarm("jenkins-error-alarm",
        comparison_operator="GreaterThanOrEqualToThreshold",
        evaluation_periods=1,
        metric_name="JenkinsErrorCount",
        namespace="CustomMetrics",
        period=300,
        statistic="Sum",
        threshold=5,
        alarm_description="Alarm when Jenkins error count exceeds threshold",
        insufficient_data_actions=[],
        dimensions={
            "LogGroupName": jenkins_log_group.name
        }
    )
    
    return {
        "jenkins_error_metric": jenkins_error_metric,
        "app_error_metric": app_error_metric,
        "jenkins_alarm": jenkins_alarm,
        "jenkins_log_group": jenkins_log_group,
        "app_log_group": app_log_group,
        "bastion_log_group": bastion_log_group
    }


def create_dashboard(ids, app_log_group_name):
    # Now create the dashboard with the resolved IDs
    dashboard = aws.cloudwatch.Dashboard("infrastructure-dashboard",
        dashboard_name="infrastructure-dashboard",
        dashboard_body=json.dumps({
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "CPUUtilization", "InstanceId", ids["bastion_id"]],
                            ["AWS/EC2", "CPUUtilization", "InstanceId", ids["jenkins_id"]],
                            ["AWS/EC2", "CPUUtilization", "InstanceId", ids["app1_id"]],
                            ["AWS/EC2", "CPUUtilization", "InstanceId", ids["app2_id"]]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": aws.config.region,
                        "title": "CPU Utilization"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "NetworkIn", "InstanceId", ids["bastion_id"]],
                            ["AWS/EC2", "NetworkIn", "InstanceId", ids["jenkins_id"]],
                            ["AWS/EC2", "NetworkIn", "InstanceId", ids["app1_id"]],
                            ["AWS/EC2", "NetworkIn", "InstanceId", ids["app2_id"]]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": aws.config.region,
                        "title": "Network In"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "NetworkOut", "InstanceId", ids["bastion_id"]],
                            ["AWS/EC2", "NetworkOut", "InstanceId", ids["jenkins_id"]],
                            ["AWS/EC2", "NetworkOut", "InstanceId", ids["app1_id"]],
                            ["AWS/EC2", "NetworkOut", "InstanceId", ids["app2_id"]]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": aws.config.region,
                        "title": "Network Out"
                    }
                },
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/EC2", "CPUCreditUsage", "InstanceId", ids["bastion_id"]],
                            ["AWS/EC2", "CPUCreditUsage", "InstanceId", ids["jenkins_id"]],
                            ["AWS/EC2", "CPUCreditUsage", "InstanceId", ids["app1_id"]],
                            ["AWS/EC2", "CPUCreditUsage", "InstanceId", ids["app2_id"]]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": aws.config.region,
                        "title": "CPU Credit Usage"
                    }
                },
                {
                    "type": "log",
                    "x": 0, 
                    "y": 12,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": f"SOURCE '{app_log_group_name}' | fields @timestamp, @message\n| sort @timestamp desc\n| limit 20",
                        "region": aws.config.region,
                        "title": "Application Logs",
                        "view": "table"
                    }
                }
            ]
        })
    )
    
    return dashboard