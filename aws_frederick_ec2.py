from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import Ref, GetAtt, Base64, Join, Output
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
import troposphere.ecs as ecs
import troposphere.elasticloadbalancing as elb
import troposphere.constants as tpc
import troposphere.autoscaling as autoscaling
import troposphere.cloudwatch as cloudwatch

class AWSFrederickEC2Template(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing ion channel EC2 resources
    """

    # Collect all the values we need to assemble our SuperBowlOnARoll stack
    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickEC2Template, self).__init__('AWSFrederickEC2')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for Ion Channel EC2"

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
            [{"5000": "5000"}]
        )

        self.public_lb_security_group = self.add_sg_with_cidr_port_list(
            "ELBSG",
            "Security Group for accessing EC2 publicly",
            'vpcId',
            '0.0.0.0/0',
            [{"80": "80"}]
        )

        name = self.env_name.replace('-', '')

        #
        ecs_cluster_asg = self.add_asg(
            "EC2",
            min_size=asg_size,
            max_size=6,
            ami_name=ami_name,
            #instance_profile=self.add_instance_profile(name + 'ECS', policies_for_profile, name + 'ECS'),
            instance_type=instance_type,
            security_groups=['commonSecurityGroup', Ref(self.internal_security_group)],
            subnet_layer='public',
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
                'yum install python27-pip -y\n',
                'wget https://raw.githubusercontent.com/AWSFrederick/Spires-Export/master/flask-app/requirements.txt\n',
                'wget https://raw.githubusercontent.com/AWSFrederick/Spires-Export/master/flask-app/app.py\n',
                'pip install -r requirements.txt\n',
                'export FLASK_APP=app.py\n',
                'flask run\n',
            ])),
            ebs_data_volumes=[{'name': '/dev/sds', 'size': '100', 'type': 'gp2', 'delete_on_termination': True, 'volume_type': 'gp2'}]
        )
