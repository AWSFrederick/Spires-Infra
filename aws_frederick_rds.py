from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import Ref
import troposphere.cloudwatch as cloudwatch
from troposphere.rds import DBParameterGroup
import boto3
import base64
import pprint


class AWSFrederickRdsTemplate(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick RDS resources
    """

    # Collect all the values we need to assemble our RDS stack
    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickRdsTemplate, self).__init__('AWSFrederickRds')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for AWS Frederick Rds"

        hosted_zone_name = self.config.get('hosted_zone')

        for database in self.config.get('rds'):
            self.add_rds(
                database.get('name'),
                database.get('engine'),
                database.get('username'),
                database.get('password'),
                database.get('storage'),
                database.get('db_instance_type'),
                database.get('multiaz'),
                database.get('encrypt'),
                self.cidr_range,
                hosted_zone_name
            )

    def add_rds(self, name, engine, username, password, storage, db_instance_type, multiaz, encrypt, cidr, hosted_zone):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Sets name for the RDS instance
        @param engine [string] Tells RDS what database type is needed
        @param username [string] Sets the username for the database
        @param password [string] Sets the password for the database
        @param storage [int] Sets the size of the database
        @param db_instance_type [string] Instance for the application
        @param multiaz [Bool] Status of if MultiAZ or not
        @param cidr [string] Range of addresses for this vpc
        @param hosted_zone [string] Name of the hosted zone the elb will be
        mapped to
        """
        print "Creating RDS: %s" % name
        print 'MultiAZ' + str(multiaz)

        # Add cloudwatch policy
        policies_for_profile = [self.get_cfn_policy()]
        for policy in ('cloudwatch', 's3', 'createtags', 'route53'):
            policies_for_profile.append(self.get_policy(policy, name))

        private_subnets = [{"Ref": "privateAZ0"}, {"Ref": "privateAZ1"}, {"Ref": "privateAZ2"}]

        if engine == 'postgres':
            rds_port = 5432
            family = 'postgres9.5'
            group_parameters = {
                'rds.force_ssl': '1',
                'log_min_duration_statement': '100',
                'log_statement': 'all'
            }
        if engine == 'MySQL':
            rds_port = 3306
            family = 'mysql5.1'
            group_parameters = {}
        if engine == 'mariadb':
            rds_port = 3306
            family = 'mariadb10.1'
            group_parameters = {}

        rds_security_group = self.add_simple_sg_with_cidr(name, 'RDSSecurityGroup' + name, 'vpcId', cidr, rds_port, rds_port, 'tcp')

        rds_parameter_group = self.add_resource(
            DBParameterGroup(
                'RDSParameterGroup' + name,
                Description='%s DB Parameter Group' % name,
                Family=family,
                Parameters=group_parameters
            )
        )



        # rds_security_group = self.add_rds_security_group(name, self.vpc_id)
        rds_subnet_group = self.add_rds_db_subnet(name, private_subnets)

        client = boto3.client('kms')
        response = client.decrypt(CiphertextBlob=base64.b64decode(password))
        password = response['Plaintext']
        print('Master Password is: %s' % password)
        rds_database = self.add_rds_database(name, engine, username, password, storage,
                                             db_instance_type, rds_subnet_group, rds_security_group,
                                             multiaz, rds_parameter_group, encrypt)

        self.add_rds_dns_alias(rds_database, name, hosted_zone)
