from aws_frederick_common import AWSFrederickCommonTemplate


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
                if ".prod" in hosted_zone_name:
                    public_hosted_zone_name = bucket.get('name') + "."
                self.add_bucket(
                    bucket.get('name'),
                    bucket.get('access_control'),
                    bucket.get('static_site'),
                    bucket.get('route53'),
                    public_hosted_zone_name,
                )
