from aws_frederick_common import AWSFrederickCommonTemplate
from troposphere import Ref, GetAtt, Base64, Join, Output, Template
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
from troposphere import ecs
import troposphere.elasticloadbalancing as elb
import troposphere.constants as tpc
import troposphere.autoscaling as autoscaling
import troposphere.cloudwatch as cloudwatch


class AWSFrederickECSTemplate(AWSFrederickCommonTemplate):
    """
    Enhances basic template by providing AWS Frederick ECS resources
    """

    # Collect all the values we need to assemble our SuperBowlOnARoll stack
    def __init__(self, env_name, region, cidr_range, aws_frederick_config):
        super(AWSFrederickECSTemplate, self).__init__('AWSFrederickECS')

        self.env_name = env_name
        self.region = region
        self.cidr_range = cidr_range
        self.config = aws_frederick_config

    def build_hook(self):
        print "Building Template for AWS Frederick ECS"

        hosted_zone_name = self.config.get('hosted_zone')
        ecs_config = self.config.get('ecs')
        if ecs_config is not None:
            cluster = self.add_resource(ecs.Cluster('filesharefrederick',
                                                    ClusterName='filesharefrederick'))
            for ecs in ecs_config:
                self.add_ecs(
                    ecs.get('name'),
                    ecs.get('image'),
                    ecs.get('cpu'),
                    ecs.get('memory'),
                    ecs.get('container_port'),
                    ecs.get('alb_port'),
                    ecs.get('envvars'),
                    self.cidr_range,
                    hosted_zone_name
                )

    def add_ecs(self, name, image, cpu, memory, container_port, alb_port, envvars, cidr, hosted_zone):
        """
        Helper method creates ingress given a source cidr range and a set of
        ports
        @param name [string] Name of the service
        @param image [string] Docker image name
        @param memory [int] Sets the memory size of the service
        @param envvars [list] List of envvars
        @param cidr [string] Range of addresses for this vpc
        @param hosted_zone [string] Name of the hosted zone the elb will be
        mapped to
        """
        print "Creating ECS"

        self.internal_security_group = self.add_sg_with_cidr_port_list(
            "ASGSG",
            "Security Group for ECS",
            'vpcId',
            cidr,
            [{"80": "80"}]
        )

        self.public_lb_security_group = self.add_sg_with_cidr_port_list(
            "ELBSG",
            "Security Group for accessing ECS publicly",
            'vpcId',
            '0.0.0.0/0',
            [{"443": "443"}]
        )

        container_def = ecs.ContainerDefinition(name + 'containerdef',
                                                Name=name,
                                                Image=image,
                                                Cpu=cpu,
                                                Memory=memory,
                                                PortMappings=[ecs.PortMapping(
                                                    ContainerPort=container_port
                                                )])

        task_def = self.add_resource(ecs.TaskDefinition(name + 'taskdef',
                                     Cpu=cpu,
                                     Memory=memory,
                                     RequiresCompatibilities=['FARGATE'],
                                     NetworkMode='awsvpc',
                                     ContainerDefinitions=[container_def]))

        self.add_resource(ecs.Service(name + 'service',
                                      Cluster=Ref(cluster),
                                      LaunchType='FARGATE',
                                      TaskDefinition=Ref(task_def),
                                      DesiredCount=1))
