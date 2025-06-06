import textwrap

from aws_cdk import RemovalPolicy, aws_ec2 as ec2, aws_route53
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from constructs import Construct

from .config import (
    ODIN_AWS_REGION,
    ODIN_KEY_PAIR,
)

LOG_GROUP = "/Odin/Admin"


class AdminInstance(ec2.Instance):
    def __init__(
        self,
        scope: Construct,
        id: str,
        vpc: ec2.IVpc,
        public_zone: aws_route53.IHostedZone,
        private_zone: aws_route53.IHostedZone,
    ) -> None:
        vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        security_group = ec2.SecurityGroup(scope, "OdinAdminSecurityGroup", vpc=vpc)
        security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(22))

        # Create IAM role for EC2 instances
        role = iam.Role(
            scope,
            "OdinAdminInstanceRole",
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
            "yum install -y mongodb-mongosh awslogs",
            f"sed -i 's|region = us-east-1|region = {ODIN_AWS_REGION}|' /etc/awslogs/awscli.conf",
            f"sed -i 's|#log_group_name = |log_group_name = {LOG_GROUP}|' /etc/awslogs/awslogs.conf",
            "service awslogs start",
            "chkconfig awslogs on",
        )
        super().__init__(
            scope,
            id,
            instance_type=ec2.InstanceType("t3.nano"),
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

        logs.LogGroup(
            scope,
            "OdinAdminLogGroup",
            log_group_name=LOG_GROUP,
            removal_policy=RemovalPolicy.DESTROY,
            retention=logs.RetentionDays.SIX_MONTHS,
        )

        aws_route53.ARecord(
            scope,
            "OdinAdminAliasRecord",
            zone=public_zone,
            target=aws_route53.RecordTarget.from_ip_addresses(self.instance_public_ip),
            record_name="admin.odin-smr.org",
        )
        aws_route53.ARecord(
            scope,
            "OdinAdminPrivateAliasRecord",
            zone=private_zone,
            target=aws_route53.RecordTarget.from_ip_addresses(
                self.instance_private_ip,
            ),
            record_name="admin.odin",
        )
