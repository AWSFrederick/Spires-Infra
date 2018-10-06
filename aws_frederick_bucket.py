from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.cloudfront import Distribution, DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior
from troposphere.cloudfront import ForwardedValues
from troposphere.cloudfront import S3Origin
from troposphere.cloudfront import ViewerCertificate
from troposphere.route53 import AliasTarget, RecordSetGroup, RecordSet


class AWSFrederickBucketTemplate(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick bucket resources
    """

    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickBucketTemplate, self).__init__(env_name + 'Bucket')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for %s Bucket" % self.env_name

        public_hosted_zone_name = self.config.get('public_hosted_zone')
        hosted_zone_name = self.config.get('hosted_zone')
        buckets = self.config.get('buckets')

        if buckets is not None:
            for bucket in buckets:
                self.add_bucket(
                    bucket.get('name'),
                    bucket.get('access_control'),
                    bucket.get('static_site'),
                    bucket.get('route53'),
                    public_hosted_zone_name,
                )
                if bucket.get('cloudfront'):
                    cloudfront = self.add_resource(Distribution(bucket.get('name').replace('.',''),
                        DistributionConfig=DistributionConfig(
                            Aliases=[bucket.get('name')],
                            DefaultRootObject='index.html',
                            Origins=[Origin(Id="Origin 1",
                            DomainName=bucket.get('name') + '.s3.amazonaws.com',
                            S3OriginConfig=S3Origin())],
                            DefaultCacheBehavior=DefaultCacheBehavior(
                                TargetOriginId="Origin 1",
                                ForwardedValues=ForwardedValues(
                                    QueryString=False),
                                    ViewerProtocolPolicy="redirect-to-https"),
                            Enabled=True,
                            HttpVersion='http2',
                            ViewerCertificate=ViewerCertificate(
                                AcmCertificateArn='arn:aws:acm:us-east-1:422548007577:certificate/4d2f2450-7616-4daa-b7ed-c1fd2d53df90',
                                SslSupportMethod='sni-only'
                            ))))
                    # todo: ipv6 - cloudformation not supported
                    # todo: ssl cert via acm
                    # todo: dns alias for cloudfront
                    #"Z2FDTNDATAQYW2"
                #     self.add_resource(RecordSetGroup(
                #         "cloudfrontroute53",
                #         HostedZoneName=public_hosted_zone_name,
                #         RecordSets=[
                #             RecordSet(
                #                 Name=bucket.get('name'),
                #                 Type="A",
                #                 AliasTarget=AliasTarget(
                #                     "Z2FDTNDATAQYW2",
                #                     Ref(cloudfront)
                #                 ),
                #             ),
                #         ],
                #     )
                # )
