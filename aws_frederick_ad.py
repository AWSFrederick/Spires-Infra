from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere import directoryservice
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

        self.add_resource(directoryservice.SimpleAD(
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
        ))

# class SimpleAD(AWSObject):
#     resource_type = "AWS::DirectoryService::SimpleAD"
#
#     props = {
#         'CreateAlias': (boolean, False),
#         'Description': (basestring, False),
#         'EnableSso': (boolean, False),
#         'Name': (basestring, True),
#         'Password': (basestring, True),
#         'ShortName': (basestring, False),
#         'Size': (basestring, True),
#         'VpcSettings': (VpcSettings, True),
#     }

# "myDirectory" : {
#   "Type" : "AWS::DirectoryService::SimpleAD",
#   "Properties" : {
#     "Name" : "corp.example.com",
#     "Password" : { "Ref" : "SimpleADPW" },
#     "Size" : "Small",
#     "VpcSettings" : {
#       "SubnetIds" : [ { "Ref" : "subnetID1" }, { "Ref" : "subnetID2" } ],
#       "VpcId" : { "Ref" : "vpcID" }
#     }
#   }
# }
