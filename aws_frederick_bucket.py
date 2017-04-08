from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import GetAtt, Join, Output
from troposphere import Parameter, Ref, Template
from troposphere.cloudfront import Distribution, DistributionConfig
from troposphere.cloudfront import Origin, DefaultCacheBehavior
from troposphere.cloudfront import ForwardedValues
from troposphere.cloudfront import S3Origin

class AWSFrederickBucketTemplate(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick bucket resources
    """

    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickBucketTemplate, self).__init__('AWSFrederickBucket')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for AWS Frederick Bucket"

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
                if bucket.get('static_site'):
                    self.add_resource(Distribution(bucket.get('name').replace('.',''),
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
                                ViewerProtocolPolicy="allow-all"),
                            Enabled=True,
                            HttpVersion='http2')))
                    # todo: ipv6
                    # todo: ssl cert via acm
                    # todo: dns alias for cloudfront
                    # self.add_dns_alias(
                    #     name,
                    #     "s3-website-us-east-1.amazonaws.com",
                    #     "Z2FDTNDATAQYW2",
                    #     public_hosted_zone
                    # )
