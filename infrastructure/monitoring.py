# infrastructure/monitoring.py

import pulumi
import pulumi_aws as aws
import json


def create_monitoring_resources():
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
                            ["AWS/EC2", "CPUUtilization", "InstanceId", "${bastion-host}"],
                            ["AWS/EC2", "CPUUtilization", "InstanceId", "${jenkins-instance}"],
                            ["AWS/EC2", "CPUUtilization", "InstanceId", "${app1-instance}"],
                            ["AWS/EC2", "CPUUtilization", "InstanceId", "${app2-instance}"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
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
                            ["AWS/EC2", "NetworkIn", "InstanceId", "${bastion-host}"],
                            ["AWS/EC2", "NetworkIn", "InstanceId", "${jenkins-instance}"],
                            ["AWS/EC2", "NetworkIn", "InstanceId", "${app1-instance}"],
                            ["AWS/EC2", "NetworkIn", "InstanceId", "${app2-instance}"]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "Network In"
                    }
                },
                {
                    "type": "log",
                    "x": 0,
                    "y": 6,
                    "width": 24,
                    "height": 6,
                    "properties": {
                        "query": "SOURCE 'app-instance-logs' | fields @timestamp, @message\n| sort @timestamp desc\n| limit 20",
                        "region": "us-east-1",
                        "title": "Application Logs",
                        "view": "table"
                    }
                }
            ]
        })
    )
    jenkins_error_metric = aws.cloudwatch.LogMetricFilter("jenkins-error-metric",
        log_group_name=jenkins_log_group.name,  # Use the reference to the log group
        pattern="ERROR",
        metric_transformation={
            "name": "JenkinsErrorCount",
            "namespace": "CustomMetrics",
            "value": "1"
        }
    )
    app_error_metric = aws.cloudwatch.LogMetricFilter("app-error-metric",
        log_group_name=app_log_group.name,  # Use the reference to the log group
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
            "LogGroupName": jenkins_log_group.name  # Use the reference to the log group
        }
    )
    return {
        "dashboard": dashboard,
        "jenkins_error_metric": jenkins_error_metric,
        "app_error_metric": app_error_metric,
        "jenkins_alarm": jenkins_alarm,
        "jenkins_log_group": jenkins_log_group,
        "app_log_group": app_log_group,
        "bastion_log_group": bastion_log_group
    }