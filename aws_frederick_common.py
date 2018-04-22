import troposphere.autoscaling as autoscaling
import troposphere.sqs as sqs
import troposphere.ec2 as ec2
import troposphere.iam as iam
import troposphere.s3 as s3
import troposphere.route53 as route53
import troposphere.kms as kms
from troposphere import elasticache
import troposphere.cloudwatch as cloudwatch
from troposphere.rds import DBInstance, DBSubnetGroup
from troposphere import Ref, GetAtt, Join
from environmentbase.template import Template
import awacs.iam
from troposphere.ecr import Repository
from awacs.aws import Allow, Policy, AWSPrincipal, Statement
import awacs.ecr as ecr
import troposphere.ecs as ecs
import sys


class AWSFrederickCommonTemplate(Template):
    """
    Enhances basic template by providing AWS Frederick common resources
    """

    # default configuration values
    DEFAULT_CONFIG = {
        'ion_channel': {

        }
    }

    # schema of expected types for config values
    CONFIG_SCHEMA = {
        'ion_channel': {

        }
    }

    POLICY_MAP = {}

    # Collect all the values we need to assemble our SuperBowlOnARoll stack
    def __init__(self, name):
        super(AWSFrederickCommonTemplate, self).__init__(name)
        self.load_policy_map()

    def add_alarm(self, name, dimensions, alarm, description, namespace, threshold, comparison_operator, statistic, metric_name):
        return self.add_resource(
            cloudwatch.Alarm(
                name,
                MetricName=metric_name,
                ComparisonOperator=comparison_operator,
                Period=300,
                EvaluationPeriods=1,
                Statistic=statistic,
                Namespace=namespace,
                AlarmDescription=description,
                Dimensions=dimensions,
                Threshold=threshold,
                AlarmActions=[alarm]
            )
        )

    def add_bucket(self, name, access_control, static_site, route53, public_hosted_zone):
        """
        Helper method creates a directory service resource
        @param name [string] Fully qualified name for the bucket
        (corp.example.com)
        @param access_control [string] type of access control for the bucket
        @param static_site [boolean] should the bucket host a static site
        @param route53 [boolean] create a route53 entry?
        """

        if route53:
            self.add_dns_alias(
                name,
                "s3-website-us-east-1.amazonaws.com",
                "Z3AQBSTGFYJSTF",
                public_hosted_zone
            )

        if access_control == "PublicRead":
            policy = s3.BucketPolicy(
                name.replace('.', '') + "BucketPolicy",
                Bucket=name,
                PolicyDocument={
                    "Statement": [
                        {
                            "Sid": "PublicReadForGetBucketObjects",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": "arn:aws:s3:::%s/*" % name
                        }
                    ]
                }
            )
            self.add_resource(policy)

        bucket = s3.Bucket(
            name.replace('.', '') + "Bucket",
            BucketName=name,
            AccessControl=access_control,
        )

        if static_site:
            web_config = s3.WebsiteConfiguration(IndexDocument='index.html')
            bucket.properties['WebsiteConfiguration'] = web_config

        return self.add_resource(bucket)

    def add_role(self, name, principal_services, policies, path='/'):
        """
        Helper method for creating roles with pre defined policies
        """
        policies_for_role = [self.get_policy(policy, name) for policy in policies]

        return self.add_resource(iam.Role(
            name + "Role",
            AssumeRolePolicyDocument={
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "Service": principal_services
                    },
                    "Action": ["sts:AssumeRole"]
                }]
            },
            Path=path,
            Policies=policies_for_role
        ))

    def load_policy_map(self):
        # TODO: move these to a flat config file & load from that
        self.POLICY_MAP = {
            'kms': iam.Policy(
                PolicyName='kmsInteract',
                PolicyDocument={
                    "Statement": [{
                        "Sid": "Stmt1457395497000",
                        "Effect": "Allow",
                        "Action": [
                            "kms:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'autoscaling': iam.Policy(
                PolicyName='asgInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "autoscaling:*",
                            "ec2:*",
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'cloudwatch': iam.Policy(
                PolicyName='cwInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "sns:*",
                            "autoscaling:Describe*",
                            "cloudwatch:*",
                            "logs:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'cloudwatchlogs': iam.Policy(
                PolicyName='cloudwatchlogs',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                            "logs:DescribeLogStreams"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'autoscaling_ecs': iam.Policy(
                PolicyName='service-autoscaling',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "application-autoscaling:*",
                            "cloudwatch:DescribeAlarms",
                            "cloudwatch:PutMetricAlarm",
                            "ecs:DescribeServices",
                            "ecs:UpdateService"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'sns': iam.Policy(
                PolicyName='snsInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "sns:*",
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            's3': iam.Policy(
                PolicyName='s3Interact',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "s3:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'ecr': iam.Policy(
                PolicyName='ecrInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "ecr:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'ecs': iam.Policy(
                PolicyName='ecsInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "elasticloadbalancing:Describe*",
                            "elasticloadbalancing:DeregisterInstancesFromLoadBalancer",
                            "elasticloadbalancing:RegisterInstancesWithLoadBalancer",
                            "ec2:Describe*",
                            "ec2:AuthorizeSecurityGroupIngress",
                            "ecs:RegisterContainerInstance",
                            "ecs:DeregisterContainerInstance",
                            "ecs:DiscoverPollEndpoint",
                            "ecs:Submit*",
                            "ecs:Poll",
                            "ecs:StartTelemetrySession",
                            "application-autoscaling:*",
                            "cloudwatch:DescribeAlarms",
                            "cloudwatch:PutMetricAlarm",
                            "ecs:DescribeServices",
                            "ecs:UpdateService"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'ses': iam.Policy(
                PolicyName='sesInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "ses:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'sqs': iam.Policy(
                PolicyName='sqsInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "sqs:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'route53': iam.Policy(
                PolicyName='route53Interact',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "route53:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'createtags': iam.Policy(
                PolicyName='createtags',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "ec2:CreateTags",
                            "ec2:DescribeInstances",
                            "ec2:DescribeTags",
                            "ec2:DescribeVolumes"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'es': iam.Policy(
                PolicyName='esInteract',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "es:*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'lambda': iam.Policy(
                PolicyName='lambda',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "cloudwatch:*",
                            "cognito-identity:ListIdentityPools",
                            "cognito-sync:GetCognitoEvents",
                            "cognito-sync:SetCognitoEvents",
                            "dynamodb:*",
                            "events:*",
                            "iam:ListAttachedRolePolicies",
                            "iam:ListRolePolicies",
                            "iam:ListRoles",
                            "iam:PassRole",
                            "kinesis:DescribeStream",
                            "kinesis:ListStreams",
                            "kinesis:PutRecord",
                            "lambda:*",
                            "logs:*",
                            "s3:*",
                            "sns:ListSubscriptions",
                            "sns:ListSubscriptionsByTopic",
                            "sns:ListTopics",
                            "sns:Subscribe",
                            "sns:Unsubscribe"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'readall': iam.Policy(
                PolicyName='readall',
                PolicyDocument={
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "appstream:Get*",
                            "autoscaling:Describe*",
                            "cloudformation:DescribeStackEvents",
                            "cloudformation:DescribeStackResource",
                            "cloudformation:DescribeStackResources",
                            "cloudformation:DescribeStacks",
                            "cloudformation:GetTemplate",
                            "cloudformation:List*",
                            "cloudfront:Get*",
                            "cloudfront:List*",
                            "cloudsearch:Describe*",
                            "cloudsearch:List*",
                            "cloudtrail:DescribeTrails",
                            "cloudtrail:GetTrailStatus",
                            "cloudwatch:Describe*",
                            "cloudwatch:Get*",
                            "cloudwatch:List*",
                            "codecommit:BatchGetRepositories",
                            "codecommit:Get*",
                            "codecommit:GitPull",
                            "codecommit:List*",
                            "codedeploy:Batch*",
                            "codedeploy:Get*",
                            "codedeploy:List*",
                            "config:Deliver*",
                            "config:Describe*",
                            "config:Get*",
                            "datapipeline:DescribeObjects",
                            "datapipeline:DescribePipelines",
                            "datapipeline:EvaluateExpression",
                            "datapipeline:GetPipelineDefinition",
                            "datapipeline:ListPipelines",
                            "datapipeline:QueryObjects",
                            "datapipeline:ValidatePipelineDefinition",
                            "directconnect:Describe*",
                            "dynamodb:BatchGetItem",
                            "dynamodb:DescribeTable",
                            "dynamodb:GetItem",
                            "dynamodb:ListTables",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                            "ec2:Describe*",
                            "ec2:GetConsoleOutput",
                            "ecr:GetAuthorizationToken",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:GetManifest",
                            "ecr:DescribeRepositories",
                            "ecr:ListImages",
                            "ecr:BatchGetImage",
                            "ecs:Describe*",
                            "ecs:List*",
                            "elasticache:Describe*",
                            "elasticache:List*",
                            "elasticbeanstalk:Check*",
                            "elasticbeanstalk:Describe*",
                            "elasticbeanstalk:List*",
                            "elasticbeanstalk:RequestEnvironmentInfo",
                            "elasticbeanstalk:RetrieveEnvironmentInfo",
                            "elasticloadbalancing:Describe*",
                            "elasticmapreduce:Describe*",
                            "elasticmapreduce:List*",
                            "elastictranscoder:List*",
                            "elastictranscoder:Read*",
                            "firehose:Describe*",
                            "firehose:List*",
                            "glacier:ListVaults",
                            "glacier:DescribeVault",
                            "glacier:GetDataRetrievalPolicy",
                            "glacier:GetVaultAccessPolicy",
                            "glacier:GetVaultLock",
                            "glacier:GetVaultNotifications",
                            "glacier:ListJobs",
                            "glacier:ListMultipartUploads",
                            "glacier:ListParts",
                            "glacier:ListTagsForVault",
                            "glacier:DescribeJob",
                            "glacier:GetJobOutput",
                            "iam:GenerateCredentialReport",
                            "iam:Get*",
                            "iam:List*",
                            "inspector:Describe*",
                            "inspector:Get*",
                            "inspector:List*",
                            "inspector:LocalizeText",
                            "inspector:PreviewAgentsForResourceGroup",
                            "iot:Describe*",
                            "iot:Get*",
                            "iot:List*",
                            "kinesis:Describe*",
                            "kinesis:Get*",
                            "kinesis:List*",
                            "kms:Describe*",
                            "kms:Get*",
                            "kms:List*",
                            "lambda:List*",
                            "lambda:Get*",
                            "logs:Describe*",
                            "logs:Get*",
                            "logs:TestMetricFilter",
                            "mobilehub:GetProject",
                            "mobilehub:ListAvailableFeatures",
                            "mobilehub:ListAvailableRegions",
                            "mobilehub:ListProjects",
                            "mobilehub:ValidateProject",
                            "mobilehub:VerifyServiceRole",
                            "opsworks:Describe*",
                            "opsworks:Get*",
                            "rds:Describe*",
                            "rds:ListTagsForResource",
                            "redshift:Describe*",
                            "redshift:ViewQueriesInConsole",
                            "route53:Get*",
                            "route53:List*",
                            "route53domains:CheckDomainAvailability",
                            "route53domains:GetDomainDetail",
                            "route53domains:GetOperationDetail",
                            "route53domains:ListDomains",
                            "route53domains:ListOperations",
                            "route53domains:ListTagsForDomain",
                            "s3:Get*",
                            "s3:List*",
                            "sdb:GetAttributes",
                            "sdb:List*",
                            "sdb:Select*",
                            "ses:Get*",
                            "ses:List*",
                            "sns:Get*",
                            "sns:List*",
                            "sqs:GetQueueAttributes",
                            "sqs:ListQueues",
                            "sqs:ReceiveMessage",
                            "storagegateway:Describe*",
                            "storagegateway:List*",
                            "swf:Count*",
                            "swf:Describe*",
                            "swf:Get*",
                            "swf:List*",
                            "tag:Get*",
                            "trustedadvisor:Describe*",
                            "waf:Get*",
                            "waf:List*"
                        ],
                        "Resource": "*"
                    }]
                }
            ),
            'simianarmy': iam.Policy(
                PolicyName='SimianArmyInteract',
                PolicyDocument={
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "Stmt1357739573947",
                            "Action": [
                                "ec2:CreateTags",
                                "ec2:DeleteSnapshot",
                                "ec2:DescribeImages",
                                "ec2:DescribeInstances",
                                "ec2:DescribeSnapshots",
                                "ec2:DescribeVolumes",
                                "ec2:TerminateInstances",
                                "ses:SendEmail",
                                "elasticloadbalancing:*"
                            ]
                        },
                        {
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "Stmt1357739649609",
                            "Action": [
                                "autoscaling:DeleteAutoScalingGroup",
                                "autoscaling:DescribeAutoScalingGroups",
                                "autoscaling:DescribeAutoScalingInstances",
                                "autoscaling:DescribeLaunchConfigurations"
                            ]
                        },
                        {
                            "Effect": "Allow",
                            "Resource": "*",
                            "Sid": "Stmt1357739730279",
                            "Action": [
                                "sdb:BatchDeleteAttributes",
                                "sdb:BatchPutAttributes",
                                "sdb:DomainMetadata",
                                "sdb:GetAttributes",
                                "sdb:PutAttributes",
                                "sdb:ListDomains",
                                "sdb:CreateDomain",
                                "sdb:Select"
                            ]
                        }
                    ]
                }
            )
        }

    def get_policy(self, policy_type, receiver_name):
        print("WARNING: Allowing %s access for %s" % (policy_type, receiver_name))

        return self.POLICY_MAP.get(policy_type)

    def add_sqs_queue(
        self,
        name,
        delay_seconds=0,
        maximum_message_size=262144,
        message_retention_period=345600,
        receive_message_wait_time_seconds=0,
        visibility_timeout=30,
    ):
        """
        Helper that creates a SQS Queue
        @param name [string] name of the queue
        @param delay_seconds [integer] he time in seconds that the delivery of
        all messages in the queue will be delayed
        @param maximum_message_size [integer] The limit of how many bytes a
        message can contain before Amazon SQS rejects it
        @param message_retention_period [integer] The number of seconds Amazon
        SQS retains a message
        @param receive_message_wait_time_seconds [integer] Specifies the
        duration, in seconds, that the ReceiveMessage action call waits until
        a message is in the queue in order to include it in the response, as
        opposed to returning an empty response if a message is not yet
        available
        @param visibility_timeout [integer] The length of time during which the
        queue will be unavailable once a message is delivered from the queue
        """
        return self.add_resource(
            sqs.Queue(
                name.replace('-', '').replace('_', ''),
                QueueName=name,
                DelaySeconds=delay_seconds,
                MaximumMessageSize=maximum_message_size,
                MessageRetentionPeriod=message_retention_period,
                ReceiveMessageWaitTimeSeconds=receive_message_wait_time_seconds,
                VisibilityTimeout=visibility_timeout
            )
        )

    def add_hosted_zone(
        self,
        name,
        region
    ):
        """
        Helper that creates a hosted zone
        @param name [string] name of the private hosted zone that will be
        attached to the vpc
        @param region [string] name of the region, as if it could be different
        than the vpc's
        """

        return self.add_resource(route53.HostedZone(
            "PrivateHostedZone",
            HostedZoneConfig=route53.HostedZoneConfiguration(
                Comment="Private HostedZone"
            ),
            Name=name,
            VPCs=[route53.HostedZoneVPCs(VPCId=Ref(self.vpc_id), VPCRegion=region)]
        ))

    def add_scheduled_action(
        self,
        name,
        autoscaling_group,
        min_size,
        max_size,
        desired_size,
        recurrence
    ):
        """
        Helper method creates a scheduled action for a given autoscaling group
        @param name [string] Unique name for the scheduled action
        @param name [AutoScalingGroup] Troposphere object containing the
        autoscaling group
        @param min_size [int] minimum size for the group
        @param max_size [int] maximum size for the group
        @param desired_size [int] the size resulting from this action
        @param min_size [string] cron string scehdule to trigger this action
        """

        return self.add_resource(autoscaling.ScheduledAction(
            name,
            AutoScalingGroupName=Ref(autoscaling_group),
            DesiredCapacity=desired_size,
            Recurrence=recurrence,
            MaxSize=max_size,
            MinSize=min_size,
        ))

    def add_elb_dns_alias(self, elb, name, zone_name):
        """
        Helper to attach an alias dns entry to an elb
        @param elb [ELB] target elb
        @param name [string] name of the domain
        @param zone_name [string] hostzone name
        """
        if name:
            name = name.lower() + '.' + zone_name
        else:
            name = zone_name.lower()
        return self.add_resource(
            route53.RecordSetGroup(
                name.replace('.', '') + "ELBRecordSetGroup" + zone_name.replace('.', ''),
                HostedZoneName=zone_name.lower(),
                RecordSets=[
                    route53.RecordSet(
                        Name=name,
                        Type='A',
                        AliasTarget=route53.AliasTarget(
                            GetAtt(elb, "CanonicalHostedZoneID"),
                            GetAtt(elb, "DNSName")
                        )
                    )
                ]
            )
        )

    def add_dns_alias(self, name, dns_name, zone_id, zone_name):
        """
        Helper to attach an alias dns entry to an elb
        @param dns_name [string] name of the domain
        @param zone_id [string] hostzone id for the target
        @param zone_name [string] hostzone name
        """
        return self.add_resource(
            route53.RecordSetGroup(
                name.replace(".", "") + "AliasRecordSetGroup" + zone_name.replace('.', ''),
                HostedZoneName=zone_name,
                RecordSets=[
                    route53.RecordSet(
                        Name=name,
                        Type='A',
                        AliasTarget=route53.AliasTarget(
                            zone_id,
                            dns_name
                        )
                    )
                ]
            )
        )

    def add_instance_dns_a_record(self, instance, name, zone_name, att='PrivateIp'):
        """
        Helper to attach an alias dns entry to an elb
        @param instance [Instance] target instance
        @param name [string] name of the domain
        @param zone_name [string] hostzone name
        @param att [string] the attribute to use for binding the record
        """
        return self.add_resource(
            route53.RecordSetGroup(
                name.replace(".", "") + "InstanceRecordSetGroup",
                HostedZoneName=zone_name,
                RecordSets=[
                    route53.RecordSet(
                        Name=name + '.' + zone_name,
                        Type='A',
                        TTL='60',
                        ResourceRecords=[GetAtt(instance, att)]
                    )
                ]
            )
        )

    def update_sg_with_cidr(
        self,
        security_group,
        cidr_ip,
        ports,
        ip_protocol='tcp'
    ):
        """
        Helper method for adding rules to an sg from an sg
        @param security_group [SecurityGroup] security group to update
        @param cidr_ip [string] cidr ip
        @param ports [Dict] dictionary of from:to port objects
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """
        security_group_rules = security_group.SecurityGroupIngress
        for from_port, to_port in ports.items():
            security_group_rules.append(ec2.SecurityGroupRule(
                IpProtocol=ip_protocol,
                FromPort=to_port,
                ToPort=to_port,
                CidrIp=cidr_ip
            ))

    def update_sg_with_sg(
        self,
        security_group,
        source_security_group_id,
        ports,
        ip_protocol='tcp'
    ):
        """
        Helper method for adding rules to an sg from an sg
        @param security_group [SecurityGroup] security group to update
        @param source_security_group_id [string] Id of the security group to
        allow ingress from
        @param ports [Dict] dictionary of from:to port objects
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """
        security_group_rules = security_group.SecurityGroupIngress
        for from_port, to_port in ports.items():
            security_group_rules.append(ec2.SecurityGroupRule(
                IpProtocol=ip_protocol,
                FromPort=to_port,
                ToPort=to_port,
                SourceSecurityGroupId=source_security_group_id
            ))

    def add_sg_with_sg(
        self,
        name,
        description,
        vpc_id,
        source_security_group_id,
        ports,
        ip_protocol='tcp'
    ):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Unique name for the security group
        @param description [string] Simple description of the security group
        @param vpc_id [string] id of the vpc this sg will target
        @param source_security_group_id [string] Id of the security group to
        allow ingress from
        @param ports [Dict] dictionary of from:to port objects
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """
        security_group_rules = []
        for from_port, to_port in ports.items():
            security_group_rules.append(ec2.SecurityGroupRule(
                IpProtocol=ip_protocol,
                FromPort=to_port,
                ToPort=to_port,
                SourceSecurityGroupId=source_security_group_id
            ))

        return self.add_resource(
            ec2.SecurityGroup(
                name,
                GroupDescription=description,
                VpcId=Ref(vpc_id),
                SecurityGroupIngress=security_group_rules,
            )
        )

    def add_sg_with_cidr_port_list(
        self,
        name,
        description,
        vpc_id,
        cidr,
        ports,
        ip_protocol='tcp'
    ):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Unique name for the security group
        @param description [string] Simple description of the security group
        @param vpc_id [string] id of the vpc this sg will target
        @param cidr [string] cidr ip range for ingress
        @param ports [list] list of dictionary of from:to port objects
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """
        security_group = self.add_sg_with_cidr(
            name,
            description,
            vpc_id,
            cidr,
            ports[0],
            ip_protocol
        )

        for ii in range(1, len(ports)):
            self.update_sg_with_cidr(
                security_group,
                cidr,
                ports[ii],
                ip_protocol
            )
        return security_group

    def add_sg_with_cidr(
        self,
        name,
        description,
        vpc_id,
        cidr,
        ports,
        ip_protocol='tcp'
    ):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Unique name for the security group
        @param description [string] Simple description of the security group
        @param vpc_id [string] id of the vpc this sg will target
        @param cidr [string] cidr ip range for ingress
        @param ports [Dict] dictionary of from:to port objects
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """
        securityGroupRules = []
        for from_port, to_port in ports.items():
            securityGroupRules.append(ec2.SecurityGroupRule(
                IpProtocol=ip_protocol,
                FromPort=to_port,
                ToPort=to_port,
                CidrIp=cidr
            ))

        return self.add_resource(
            ec2.SecurityGroup(
                name,
                GroupDescription=description,
                VpcId=Ref(vpc_id),
                SecurityGroupIngress=securityGroupRules,
            )
        )

    def add_simple_sg_with_sg(
        self,
        name,
        description,
        vpc_id,
        source_security_group_id,
        from_port,
        to_port=None,
        ip_protocol='tcp'
    ):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Unique name for the security group
        @param description [string] Simple description of the security group
        @param vpc_id [string] id of the vpc this sg will target
        @param source_security_group_id [string] Id of the security group to
        allow ingress from
        @param from_port [string] lower boundary of the port range to set for
        the secuirty group rules
        @param to_port [string] upper boundary of the port range to set for the
        security group rules
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """

        return self.add_resource(
            ec2.SecurityGroup(
                name,
                GroupDescription=description,
                VpcId=Ref(vpc_id),
                SecurityGroupIngress=[
                    ec2.SecurityGroupRule(
                        IpProtocol=ip_protocol,
                        FromPort=from_port,
                        ToPort=to_port,
                        SourceSecurityGroupId=source_security_group_id
                    )
                ],
            )
        )

    def add_simple_sg_with_cidr(
        self,
        name,
        description,
        vpc_id,
        source_cidr,
        from_port,
        to_port=None,
        ip_protocol='tcp'
    ):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Unique name for the security group
        @param description [string] Simple description of the security group
        @param vpc_id [string] id of the vpc this sg will target
        @param source_cidr [string] CIDR format string for ingress IP address
        range
        @param from_port [string] lower boundary of the port range to set for
        the secuirty group rules
        @param to_port [string] upper boundary of the port range to set for the
        security group rules
        @param ip_protocol [string] name of the IP protocol to set this rule
        for
        """

        return self.add_resource(
            ec2.SecurityGroup(
                name,
                GroupDescription=description,
                VpcId=Ref(vpc_id),
                SecurityGroupIngress=[
                    ec2.SecurityGroupRule(
                        IpProtocol=ip_protocol,
                        FromPort=from_port,
                        ToPort=to_port,
                        CidrIp=source_cidr
                    )
                ],
            )
        )

    def add_rds_database(self, name, engine, username, password, storage, instance_type, rds_subnet_group,
                         rds_security_group, multiaz_status, parameter_group_name, encrypt):
        print "WARNING: Adding RDS for %s" % name
        rds_database = DBInstance(
            'rds' + name, Engine=engine, MasterUsername=username,
            MasterUserPassword=password, AllocatedStorage=storage,
            StorageType='gp2',
            DBInstanceClass=instance_type, DBName='rds' + name,
            DeletionPolicy="Snapshot",
            DBSubnetGroupName=Ref(rds_subnet_group),
            BackupRetentionPeriod=7,
            DBParameterGroupName=Ref(parameter_group_name),
            VPCSecurityGroups=[Ref(rds_security_group)],
            MultiAZ=multiaz_status)

        if encrypt:
            rds_database.properties['KmsKeyId'] = encrypt
            rds_database.properties['StorageEncrypted'] = True

        return self.add_resource(rds_database)

    def add_rds_db_subnet(self, name, subnet):
        return self.add_resource(DBSubnetGroup(
            name + "DBSubnetGroup",
            DBSubnetGroupDescription="Subnets available for the RDS DB Instance",
            SubnetIds=subnet))

    def add_rds_security_group(self, name, vpc_id):
        return self.add_resource(
            ec2.SecurityGroup(
                name + "RDSSecurityGroup",
                GroupDescription="Security group for RDS DB Instance.",
                VpcId=Ref(vpc_id)
            )
        )

    def add_rds_dns_alias(self, rds, name, zone_name):
        """
        Helper to attach an alias dns entry to an elb
        @param instance [Instance] target instance
        @param name [string] name of the domain
        @param zone_name [string] hostzone name
        @param att [string] the attribute to use for binding the record
        """
        if 'admin' in zone_name:
            record_name = 'rds' + name + '.' + zone_name
        else:
            record_name = name + '.rds.' + zone_name

        return self.add_resource(
            route53.RecordSetGroup(
                name.replace(".", "") + "RDSRecordSetGroup",
                HostedZoneName=zone_name,
                RecordSets=[
                    route53.RecordSet(
                        Name=record_name,
                        Type='CNAME',
                        TTL='60',
                        ResourceRecords=[
                            GetAtt(rds, "Endpoint.Address")
                        ]
                    )
                ]
            )
        )

    def add_kms_key(self, name):
        print('Adding KMS key for %s service' % name)

        account_id = self.config.get('account_id', None)

        if not account_id:
            print('Unable to add KMS Key')
            sys.exit('Unable to add KMS Key! No Account ID')

        keypolicy = {
            "Version": "2012-10-17",
            "Id": name,
            "Statement": [{
                "Sid": "Allow administration of the key",
                "Effect": "Allow",
                "Principal": {"AWS": ("arn:aws:iam::%s:root" % account_id)},
                "Action": [
                    "kms:Create*",
                    "kms:Describe*",
                    "kms:Enable*",
                    "kms:List*",
                    "kms:Put*",
                    "kms:Update*",
                    "kms:Revoke*",
                    "kms:Disable*",
                    "kms:Get*",
                    "kms:Delete*",
                    "kms:ScheduleKeyDeletion",
                    "kms:CancelKeyDeletion"
                ],
                "Resource": "*"
            }]
        }

        return self.add_resource(kms.Key(name, KeyPolicy=keypolicy))

    def add_instance_profile_ecs(self, layer_name, iam_policies, path_prefix):
        """
        Helper function to add role and instance profile resources to this
        template using the provided iam_policies. The instance_profile will be
        created at:
        '/<path_prefix>/<layer_name>/'
        """
        iam_role_obj = iam.Role(
            layer_name + 'IAMRole',
            AssumeRolePolicyDocument={
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': {'Service': ['ec2.amazonaws.com', 'ecs.amazonaws.com']},
                    'Action': ['sts:AssumeRole']
                }]
            },
            Path=Join('', ['/' + path_prefix + '/', layer_name, '/'])
        )

        if iam_policies is not None:
            iam_role_obj.Policies = iam_policies

        iam_role = self.add_resource(iam_role_obj)

        return self.add_resource(
            iam.InstanceProfile(
                layer_name + 'InstancePolicy',
                Path='/' + path_prefix + '/',
                Roles=[Ref(iam_role)]
            )
        )

    def add_elasticache_sg(self, name, engine):
        return self.add_resource(
            elasticache.SecurityGroup(
                name + engine + 'ClusterSecurityGroup',
                Description='ElastiCache security group for ' + name + engine
            )
        )

    def add_elasticache_sg_ingress(self, clustersg, name, engine):
        return self.add_resource(
            elasticache.SecurityGroupIngress(
                name + engine + 'ClusterSecurityGroupIngress',
                CacheSecurityGroupName=Ref(clustersg),
                EC2SecurityGroupName=Ref('commonSecurityGroup')
            )
        )

    def add_cachecluster(self, cache_node_type, clustersg, name, engine, num_nodes, subnet_group):
        return self.add_resource(elasticache.CacheCluster(
            name + engine + 'Cluster',
            Engine=engine,
            CacheNodeType=cache_node_type,
            NumCacheNodes=num_nodes,
            VpcSecurityGroupIds=[Ref(clustersg)],
            CacheSubnetGroupName=Ref(subnet_group)
        ))

    def add_elasticache_dns_alias(self, cluster, name, engine, zone_name):
        if engine == 'redis':
            address = "RedisEndpoint.Address"
        if engine == 'memcached':
            address = "ConfigurationEndpoint.Address"

        return self.add_resource(route53.RecordSetGroup(
            name + engine + "ElastiCacheRecordSetGroup",
            HostedZoneName=zone_name,
            RecordSets=[
                route53.RecordSet(
                    Name=name + engine + '.' + zone_name,
                    Type='CNAME',
                    TTL='60',
                    ResourceRecords=[
                        GetAtt(cluster, address)
                    ]
                )
            ]
        )
        )

    def add_elasticache_subnet_group(self, name, engine, private_subnets):
        return self.add_resource(elasticache.SubnetGroup(Description=name + engine + 'SubnetGroup', SubnetIds=private_subnets))

    def add_ecr(self, container_name):
        print 'Creating ECR for %s' % container_name
        return(
            self.add_resource(
                Repository(
                    container_name + 'ECR',
                    RepositoryName='AWSFrederick/' + container_name,
                    RepositoryPolicyText=self.add_ecr_policy_text_allow_prod()
                )
            )
        )

    def add_container_def(self, container):
        return ecs.ContainerDefinition(
            Image=container['Image'],
            Memory=container['Memory'],
            Name=container['Name'],
            Privileged=container['Priviledge']
        )

    def add_container(self, **kwargs):
        container = {}
        container['Name'] = kwargs['Name']
        container['Image'] = kwargs['Image']
        container['Memory'] = kwargs['Memory']
        container['Priviledge'] = kwargs['Privileged'] or False
        port_mapping = kwargs['PortMappings'] or None
        mountpoint_count_dict = kwargs['MountPoints'] or None
        environment_vars = kwargs['Environment'] or None
        volume_count_dict = kwargs['Volumes'] or None

        ecs_container_def = self.add_container_def(container)

        if environment_vars:
            ecs_container_def.properties['Environment'] = environment_vars

        if port_mapping:
            ecs_container_def.properties['PortMappings'] = port_mapping

        if mountpoint_count_dict:
            ecs_container_def.properties['MountPoints'] = [mountpoint_count_dict[0]]

        ecs_task = ecs.TaskDefinition(
            container['Name'] + 'Task',
            ContainerDefinitions=[ecs_container_def]
        )

        if volume_count_dict:
            ecs_task.properties['Volumes'] = [volume_count_dict[0]]

        return(self.add_resource(ecs_task))

    def add_service(self, **kwargs):
        port = kwargs['Port'] or None

        if port:
            ecs_service = ecs.Service(
                kwargs['Name'] + 'service',
                Cluster=Ref(kwargs['Cluster']),
                TaskDefinition=Ref(kwargs['Task']),
                Role=Ref(kwargs['Role']),
                DesiredCount=1,
                LoadBalancers=[
                    ecs.LoadBalancer(
                        ContainerName=kwargs['Name'],
                        ContainerPort=port,
                        LoadBalancerName=Ref(kwargs['ELB'])
                    )
                ]
            )
            self.add_elb_dns_alias(kwargs['ELB'], kwargs['Name'], kwargs['Zone'])
            return(self.add_resource(ecs_service))
        else:
            ecs_service = ecs.Service(
                kwargs['Name'] + 'service',
                Cluster=Ref(kwargs['Cluster']),
                TaskDefinition=Ref(kwargs['Task']),
                DesiredCount=1
            )
            return(self.add_resource(ecs_service))
