from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import Ref, GetAtt, Base64, Join, Output, Template
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
import troposphere.elasticloadbalancingv2 as alb
import troposphere.constants as tpc
import troposphere.autoscaling as autoscaling
import troposphere.cloudwatch as cloudwatch
import troposphere.route53 as r53


class AWSFrederickEC2Template(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick EC2 resources
    """

    # Collect all the values we need to assemble our SuperBowlOnARoll stack
    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickEC2Template, self).__init__(env_name + 'EC2')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for %s EC2" % self.env_name

        hosted_zone_name = self.config.get('hosted_zone')
        ec2_config = self.config.get('ec2')
        if ec2_config is not None:
            self.add_ec2(
                ec2_config.get('ami_id'),
                ec2_config.get('instance_size'),
                ec2_config.get('asg_size'),
                ec2_config.get('acm_cert'),
                self.cidr_range,
                hosted_zone_name
            )

    def add_ec2(self, ami_name, instance_type, asg_size, acm_cert, cidr, hosted_zone):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param ami_name [string] Name of the AMI for launching the app
        @param instance_type [string] Instance for the application
        @param asg_size [int] Sets the size of the asg
        @param cidr [string] Range of addresses for this vpc
        @param hosted_zone [string] Name of the hosted zone the elb will be
        mapped to
        """
        print "Creating EC2"

        self.internal_security_group = self.add_sg_with_cidr_port_list(
            "ASGSG",
            "Security Group for EC2",
            'vpcId',
            cidr,
            [{"443": "443"}, {"80": "80"}]
        )

        self.public_lb_security_group = self.add_sg_with_cidr_port_list(
            "ELBSG",
            "Security Group for accessing EC2 publicly",
            'vpcId',
            '0.0.0.0/0',
            [{"443": "443"}]
        )

        name = self.env_name.replace('-', '')

        public_subnet_count = len(self._subnets.get('public').get('public'))
        public_subnets = [{'Ref': x} for x in ["publicAZ%d" % n for n in range(0, public_subnet_count)]]
        public_alb = self.add_resource(alb.LoadBalancer(
            "PublicALB",
            Scheme='internet-facing',
            Subnets=public_subnets,
            SecurityGroups=[Ref(sg) for sg in [self.public_lb_security_group]]
        ))

        target_group = self.add_resource(alb.TargetGroup(
            "AppTargetGroup80",
            Port=80,
            Protocol="HTTP",
            VpcId=self.vpc_id,
            TargetGroupAttributes=[alb.TargetGroupAttribute(Key="stickiness.enabled", Value='true'),
                                   alb.TargetGroupAttribute(Key="stickiness.type", Value='lb_cookie'),
                                   alb.TargetGroupAttribute(Key="stickiness.lb_cookie.duration_seconds", Value='3600')]
        ))
        certificate = acm_cert
        alb_ssl_listener = self.add_resource(alb.Listener(
            "ALBListner",
            Port=443,
            Certificates=[alb.Certificate(CertificateArn=certificate)],
            Protocol="HTTPS",
            DefaultActions=[alb.Action(
                Type="forward",
                TargetGroupArn=Ref(target_group))],
            LoadBalancerArn=Ref(public_alb)
        ))

        self.add_elb_dns_alias(public_alb, '', hosted_zone)
        policies = ['cloudwatchlogs']
        policies_for_profile = [self.get_policy(policy, 'EC2') for policy in policies]

        asg = self.add_asg(
            "EC2",
            min_size=asg_size,
            max_size=6,
            ami_name=ami_name,
            # load_balancer=public_elb,
            instance_profile=self.add_instance_profile(name, policies_for_profile, name),
            instance_type=instance_type,
            security_groups=['commonSecurityGroup', Ref(self.internal_security_group)],
            subnet_layer='private',
            update_policy=UpdatePolicy(
                AutoScalingRollingUpdate=AutoScalingRollingUpdate(
                    PauseTime='PT5M',
                    MinInstancesInService=1,
                    # The maximum number of instances that are terminated at a given time, left at 1 to ease into updates.
                    # Can be increased at a later time
                    MaxBatchSize='1'
                )
            ),
            user_data=Base64(Join('', [
                '#!/bin/bash\n',
                'echo Good to go'
            ])))

        asg.resource['Properties']['TargetGroupARNs'] = [Ref(target_group)]

        # Cluster Memory Scaling policies
        asg_scale_up_policy = self.add_resource(
            autoscaling.ScalingPolicy(
                name + 'ScaleUpPolicy',
                AdjustmentType='ChangeInCapacity',
                AutoScalingGroupName=Ref(asg),
                Cooldown=300,
                ScalingAdjustment=1
            )
        )

        # ELB latency above a threshold
        self.add_resource(
            cloudwatch.Alarm(
                name + 'LatencyHigh',
                MetricName='Latency',
                ComparisonOperator='GreaterThanThreshold',
                Period=300,
                EvaluationPeriods=1,
                Statistic='Average',
                Namespace='AWS/ELB',
                AlarmDescription=name + 'LatencyHigh',
                Dimensions=[cloudwatch.MetricDimension(Name='LoadBalancerName', Value=Ref(public_alb))],
                Threshold='6',
                AlarmActions=[
                  Ref(asg_scale_up_policy),
                  'arn:aws:sns:us-east-1:422548007577:notify-pat'
                ]
            )
        )
