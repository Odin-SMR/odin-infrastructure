import textwrap

from aws_cdk import RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

from .config import (
    ODIN_AVAILABILITY_ZONE,
    ODIN_AWS_REGION,
    ODIN_KEY_PAIR,
    ODIN_MONGO_DATA_VOLUME,
)

LOG_GROUP = "/Odin/Mongo"


class MongoInstance(ec2.Instance):
    def __init__(self, scope: Construct, id: str, vpc: ec2.IVpc) -> None:
        vpc_subnets = ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        )
        security_group = ec2.SecurityGroup(scope, "OdinMongoSecurityGroup", vpc=vpc)
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22))
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(27017))

        # Create IAM role for EC2 instances
        role = iam.Role(
            scope,
            "OdinMongoInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "CloudWatchLogsFullAccess"
                ),
            ],
        )
        mongodb_repo = textwrap.dedent(
            """
            [mongodb-org-6.0]
            name=MongoDB Repository
            baseurl=https://repo.mongodb.org/yum/amazon/2/mongodb-org/6.0/x86_64/
            gpgcheck=1
            enabled=1
            gpgkey=https://www.mongodb.org/static/pgp/server-6.0.asc
            """
        )
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            f"echo '{mongodb_repo}' > /etc/yum.repos.d/mongodb-org-6.0.repo",
            "yum update -y",
            "yum install -y mongodb-org awslogs",
            "service mongod stop",
            "mkdir -p /data/mongodb",
            "mount /dev/sdf /data/mongodb",
            "chown mongod:mongod /data/mongodb",
            'sed -i "s|/var/lib/mongo|/data/mongodb|g" /etc/mongod.conf',
            'sed -i "s|127.0.0.1|0.0.0.0|g" /etc/mongod.conf',
            "service mongod start",
            f"sed -i 's|region = us-east-1|region = {ODIN_AWS_REGION}|' /etc/awslogs/awscli.conf",
            f"sed -i 's|#log_group_name = |log_group_name = {LOG_GROUP}|' /etc/awslogs/awslogs.conf",
            "service awslogs start",
            "chkconfig awslogs on",
        )
        super().__init__(
            scope,
            id,
            instance_type=ec2.InstanceType("t3.large"),
            machine_image=ec2.MachineImage.generic_linux(
                {
                    "eu-north-1": "ami-08fdff97845b0d82e",
                }
            ),
            vpc=vpc,
            instance_name=id,
            key_name=ODIN_KEY_PAIR,
            role=role,
            security_group=security_group,
            user_data=user_data,
            vpc_subnets=vpc_subnets,
        )
        # Attach existing EBS volume to MongoDB EC2 instance
        volume = ec2.Volume.from_volume_attributes(
            scope,
            "OdinMongoDBVolume",
            volume_id=ODIN_MONGO_DATA_VOLUME,
            availability_zone=ODIN_AVAILABILITY_ZONE,
        )

        volume.grant_attach_volume(iam.ServicePrincipal("ec2.amazonaws.com"), [self])
        # attach large ebs volume
        ec2.CfnVolumeAttachment(
            scope,
            "OdinMongoVolumeAttachment",
            device="/dev/sdf",
            instance_id=self.instance_id,
            volume_id=ODIN_MONGO_DATA_VOLUME,
        )
        logs.LogGroup(
            scope,
            "OdinMongoLogGroup",
            log_group_name="/Odin/Mongo",
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.SIX_MONTHS,
        )
