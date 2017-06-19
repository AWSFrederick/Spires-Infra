from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import Ref, GetAtt, Base64, Join, Output, Template
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
import troposphere.elasticloadbalancing as elb
import troposphere.constants as tpc
import troposphere.autoscaling as autoscaling
import troposphere.cloudwatch as cloudwatch


class AWSFrederickEC2Template(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick EC2 resources
    """

    # Collect all the values we need to assemble our SuperBowlOnARoll stack
    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickEC2Template, self).__init__('AWSFrederickEC2')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for AWS Frederick EC2"

        hosted_zone_name = self.config.get('hosted_zone')
        ec2_config = self.config.get('ec2')
        if ec2_config is not None:
            self.add_ec2(
                ec2_config.get('ami_id'),
                ec2_config.get('instance_size'),
                ec2_config.get('asg_size'),
                self.cidr_range,
                hosted_zone_name
            )

    def add_ec2(self, ami_name, instance_type, asg_size, cidr, hosted_zone):
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
            [{"80": "80"}]
        )

        self.public_lb_security_group = self.add_sg_with_cidr_port_list(
            "ELBSG",
            "Security Group for accessing EC2 publicly",
            'vpcId',
            '0.0.0.0/0',
            [{"443": "443"}]
        )

        name = self.env_name.replace('-', '')

        ## Todo: add elb to dns for awsfred.patrickpierson.us
        public_elb = self.add_elb("ELB",
            [
              {
                'elb_port': 443,
                'elb_protocol': 'HTTPS',
                'instance_port': 80,
                'instance_protocol': 'HTTP'
              }
            ],
            health_check_protocol='HTTP',
            health_check_port=80,
            health_check_path='/',
            security_groups=[self.public_lb_security_group])

        public_elb.Listeners[0].SSLCertificateId = 'arn:aws:acm:us-east-1:422548007577:certificate/4d2f2450-7616-4daa-b7ed-c1fd2d53df90'

        public_dns = self.add_elb_dns_alias(public_elb, 'api', 'mapfrederick.city.')

        # Add policies
        policies = ['cloudwatchlogs']
        policies_for_profile = [self.get_policy(policy, 'EC2') for policy in policies]

        asg = self.add_asg(
            "EC2",
            min_size=asg_size,
            max_size=6,
            ami_name=ami_name,
            load_balancer=public_elb,
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
                'yum install python27-pip git nginx awslogs gcc python27-devel postgresql95-devel -y\n',
                'wget https://s3.amazonaws.com/files.mapfrederick.city/awslogs-append.conf\n',
                'cat awslogs-append.conf >> /etc/awslogs/awslogs.conf\n',
                'service awslogs start\n',
                'chkconfig awslogs on\n',
                'git clone https://github.com/AWSFrederick/Spires-backend.git app\n',
                'cd app\n',
                'mv awsfred.conf /etc/nginx/conf.d/awsfred.conf\n',
                'service nginx start\n'
                'virtualenv env\n',
                'source ./env/bin/activate\n',
                'pip install -r requirements.txt\n',
                'python manage.py migrate\n',
                'gunicorn spires.wsgi:application -b 0.0.0.0:5000 --keep-alive 60 &\n',
            ])))

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
                Dimensions=[cloudwatch.MetricDimension(Name='LoadBalancerName', Value=Ref(public_elb))],
                Threshold='6',
                AlarmActions=[
                  Ref(asg_scale_up_policy),
                  'arn:aws:sns:us-east-1:422548007577:notify-pat'
                ]
            )
        )
