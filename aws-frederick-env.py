#!/usr/bin/env python
'''
Usage:
    aws-frederick-env.py (create|deploy) [--config-file <FILE_LOCATION>] [--debug]
    [--template-file=<TEMPLATE_FILE>]

Options:
  -h --help                            Show this screen.
  -v --version                         Show version.
  --debug                              Prints parent template to console out.
  --config-file <CONFIG_FILE>          Name of json configuration file.
  --template-file=<TEMPLATE_FILE>      Name of template to be either generated
                                       or deployed.
'''

from environmentbase.networkbase import NetworkBase
from aws_frederick_ec2 import AWSFrederickEC2Template
from aws_frederick_rds import AWSFrederickRdsTemplate
from aws_frederick_bucket import AWSFrederickBucketTemplate
from aws_frederick_ad import AWSFrederickADTemplate
import troposphere.ec2 as ec2
import boto.vpc
import boto


class AWSFrederickEnv(NetworkBase):
    """
    Coordinates AWS Frederick stack actions (create and deploy)
    """

    def __init__(self):
        super(AWSFrederickEnv, self).__init__()

    # When no config.json file exists a new one is created using the
    # 'factory default' file.  This function augments the factory default
    # before it is written to file with the config values required by an
    # AWSFrederickTemplate

    @staticmethod
    def get_factory_defaults_hook():
        return AWSFrederickCommonTemplate.DEFAULT_CONFIG

    # When the user request to 'create' a new AWSFrederick template the
    # config.json file is read in. This file is checked to ensure all required
    # values are present. Because AWSFrederick stack has additional requirements
    # beyond that of EnvironmentBase this function is used to add additional
    # validation checks.
    @staticmethod
    def get_config_schema_hook():
        return AWSFrederickCommonTemplate.CONFIG_SCHEMA

    # Override the default create action to construct an AWSFrederick stack
    def create_hook(self):
        super(AWSFrederickEnv, self).create_hook()

        # Attach the NetworkBase: VPN, routing tables, public/private subnets, NAT instances
        # self.construct_network()

        # Load some settings from the config file
        region = self.config.get('boto').get('region_name')
        cidr_range = self.config.get('network').get('network_cidr_base') + '/' + self.config.get('network').get('network_cidr_size')
        aws_frederick_config = self.config.get('aws_frederick')
        env_name = self.globals.get('environment_name', 'aws-frederick-env')

        security_group_rules = [
            ec2.SecurityGroupRule(
                FromPort='0',
                ToPort='65535',
                IpProtocol='tcp',
                CidrIp=cidr_range
            ),
            ec2.SecurityGroupRule(
                FromPort='0',
                ToPort='65535',
                IpProtocol='udp',
                CidrIp=cidr_range
            )
        ]

        self.template._common_security_group = self.template.add_resource(
            ec2.SecurityGroup('commonSecurityGroup',
                GroupDescription='Security Group allows ingress and egress for \
                common usage patterns throughout this deployed infrastructure.',
                VpcId=self.template.vpc_id,
                SecurityGroupEgress=security_group_rules,
                SecurityGroupIngress=[]
                )
        )

        if self.config.get('aws_frederick').get('simple_ads'):
            aws_frederick_ads_template = AWSFrederickADTemplate(
                env_name,
                region,
                cidr_range,
                aws_frederick_config
            )

            self.add_child_template(aws_frederick_ads_template)

        if self.config.get('aws_frederick').get('rds'):
            aws_frederick_rds_template = AWSFrederickRdsTemplate(
                env_name,
                region,
                cidr_range,
                aws_frederick_config
            )

            self.add_child_template(aws_frederick_rds_template)

        if self.config.get('aws_frederick').get('ec2'):
            aws_frederick_ec2_template = AWSFrederickEC2Template(
                env_name,
                region,
                cidr_range,
                aws_frederick_config
            )

            self.add_child_template(aws_frederick_ec2_template)

        if self.config.get('aws_frederick').get('buckets'):
            aws_frederick_bucket_template = AWSFrederickBucketTemplate(
                env_name,
                region,
                cidr_range,
                aws_frederick_config
            )

            self.add_child_template(aws_frederick_bucket_template)

if __name__ == '__main__':
    AWSFrederickEnv()
