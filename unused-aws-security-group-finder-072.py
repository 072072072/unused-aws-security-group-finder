# AWS 환경의 보안그룹(Security Group) 최적화 도구
# 본 스크립트는 AWS 인프라에서 미사용 중인 보안그룹을 효율적으로 식별하여 리소스 관리 최적화 및 보안 강화에 기여합니다.
# 문의: https://www.linkedin.com/in/072072072yc/

import boto3


ec2 = boto3.client('ec2')
elb = boto3.client('elbv2')
elb_classic = boto3.client('elb')
rds = boto3.client('rds')
lambda_client = boto3.client('lambda')
autoscaling = boto3.client('autoscaling')


def get_attached_security_group_ids():
    attached_sg_ids = set()
    for interface in ec2.describe_network_interfaces()['NetworkInterfaces']:
        for group in interface['Groups']:
            attached_sg_ids.add(group['GroupId'])
    for lb in elb.describe_load_balancers()['LoadBalancers']:
        for sg in lb.get('SecurityGroups', []):
            attached_sg_ids.add(sg)
    for lb in elb_classic.describe_load_balancers()['LoadBalancerDescriptions']:
        for sg in lb.get('SecurityGroups', []):
            attached_sg_ids.add(sg)
    
    for instance in rds.describe_db_instances()['DBInstances']:
        for sg in instance.get('VpcSecurityGroups', []):
            attached_sg_ids.add(sg['VpcSecurityGroupId'])
    for function in lambda_client.list_functions()['Functions']:
        for sg in function.get('VpcConfig', {}).get('SecurityGroupIds', []):
            attached_sg_ids.add(sg)
    paginator = autoscaling.get_paginator('describe_auto_scaling_groups')
    pages = paginator.paginate()
    for page in pages:
        for asg in page['AutoScalingGroups']:
            if 'LaunchConfigurationName' in asg:
                response = autoscaling.describe_launch_configurations(LaunchConfigurationNames=[asg['LaunchConfigurationName']])
                for sg in response['LaunchConfigurations'][0].get('SecurityGroups', []):
                    attached_sg_ids.add(sg)
            elif 'MixedInstancesPolicy' in asg and 'LaunchTemplate' in asg['MixedInstancesPolicy']['LaunchTemplate']:
                launch_template = asg['MixedInstancesPolicy']['LaunchTemplate']['LaunchTemplateSpecification']
                lt_response = ec2.describe_launch_template_versions(LaunchTemplateId=launch_template['LaunchTemplateId'], Versions=[launch_template['Version']])
                for sg in lt_response['LaunchTemplateVersions'][0]['LaunchTemplateData'].get('SecurityGroupIds', []):
                    attached_sg_ids.add(sg)
            elif 'LaunchTemplate' in asg:
                launch_template = asg['LaunchTemplate']
                lt_response = ec2.describe_launch_template_versions(LaunchTemplateId=launch_template['LaunchTemplateId'], Versions=[launch_template['Version']])
                for sg in lt_response['LaunchTemplateVersions'][0]['LaunchTemplateData'].get('SecurityGroupIds', []):
                    attached_sg_ids.add(sg)
    return attached_sg_ids

if __name__ == '__main__':
    all_sg_ids = set(sg['GroupId'] for sg in ec2.describe_security_groups()['SecurityGroups'])
    attached_sg_ids = get_attached_security_group_ids()
    unattached_sg_ids = all_sg_ids - attached_sg_ids
    for sg_id in unattached_sg_ids:
        try:
            response = ec2.describe_security_groups(GroupIds=[sg_id])
            group_name = response['SecurityGroups'][0]['GroupName']
            print(f"GroupId: {sg_id}, GroupName: {group_name}")
        except Exception as e:
            print(f"Error getting information for {sg_id}: {e}")
