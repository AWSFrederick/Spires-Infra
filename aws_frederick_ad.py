from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere import directoryservice
from troposphere.ec2 import DHCPOptions
from troposphere.ec2 import VPCDHCPOptionsAssociation
import boto3
import base64


class AWSFrederickADTemplate(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick bucket resources
    """

    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickADTemplate, self).__init__('AWSFrederickAD')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for AWS Frederick AD"

        public_hosted_zone_name = self.config.get('public_hosted_zone')
        hosted_zone_name = self.config.get('hosted_zone')
        ads = self.config.get('simple_ads')

        if ads is not None:
            for ad in ads:
                client = boto3.client('kms')
                response = client.decrypt(CiphertextBlob=base64.b64decode(ad.get('password')))
                password = response['Plaintext']
                # password = ad.get('password')
                print('AD Password is: %s' % password)
                self.add_simple_ads(
                    ad.get('name'),
                    password,
                    ad.get('shortname'),
                    ad.get('size'),
                    hosted_zone_name
                )

    def add_simple_ads(self, name, password, shortname, size, hosted_zone):
        """
        Helper method creates a Directory Service Instance in AWS
        @param name [string] Sets name for Directory Service Instance
        @param
        """
        print "Creating Simple AD: %s" % name

        simple_ad = directoryservice.SimpleAD(
            name,
            CreateAlias=True,
            Name=hosted_zone[:-1],
            Password=password,
            ShortName=shortname,
            Size=size,
            VpcSettings=directoryservice.VpcSettings(
                SubnetIds=[
                    Ref(self.parameters.get('privateAZ0')),
                    Ref(self.parameters.get('privateAZ1'))
                ],
                VpcId=Ref(self.parameters.get('vpcId'))
            )
        )
        self.add_resource(simple_ad)

        dhcp_opts = DHCPOptions(name + 'dhcpopts',
                                DomainName=hosted_zone[:-1],
                                DomainNameServers=GetAtt(simple_ad, 'DnsIpAddresses'),
                                NetbiosNameServers=GetAtt(simple_ad, 'DnsIpAddresses'))

        self.add_resource(dhcp_opts)

        self.add_resource(VPCDHCPOptionsAssociation(name + 'dhcpoptsassociation',
                                                    DhcpOptionsId=Ref(dhcp_opts),
                                                    VpcId=Ref(self.parameters.get('vpcId'))))
