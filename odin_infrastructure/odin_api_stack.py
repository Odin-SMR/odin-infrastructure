from aws_cdk import Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_route53
from constructs import Construct

from .admin_host import AdminInstance
from .config import ODIN_API_EIP
from .mongo import MongoInstance
from .odin_cluster import OdinService


class OdinAPIStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        nat_gateway_provider = ec2.NatProvider.instance(
            instance_type=ec2.InstanceType("t3.small")
        )
        vpc: ec2.IVpc = ec2.Vpc(
            self,
            "OdinVPC",
            nat_gateway_provider=nat_gateway_provider,
            max_azs=2,
            nat_gateways=1,
            vpc_name="OdinVPC",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="OdinPublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="OdinPrivateNATSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="OdinPrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        ec2.CfnEIPAssociation(
            self,
            "OdinNATEIPAssociation",
            allocation_id=ODIN_API_EIP,
            instance_id=nat_gateway_provider.configured_gateways[0].gateway_id,
        )

        private_zone = aws_route53.PrivateHostedZone(
            self,
            "OdinPrivateZone",
            vpc=vpc,
            zone_name="odin",
        )
        mongo: ec2.IInstance = MongoInstance(self, "OdinMongo", vpc)
        admin: ec2.IInstance = AdminInstance(self, "OdinAdmin", vpc)
        cluster: ecs.ICluster = ecs.Cluster(
            self, "OdinCluster", vpc=vpc, cluster_name="OdinApiCluster"
        )
        service = OdinService(self, "OdinAPIFargateService", mongo, cluster)
        scaling = service.service.auto_scale_task_count(max_capacity=20, min_capacity=1)

        # Scale the service based on CPU Utilization
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=50,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        service.target_group.configure_health_check(
            interval=Duration.seconds(120),
            timeout=Duration.seconds(20),
            healthy_threshold_count=2,
            unhealthy_threshold_count=7,
            path="/rest_api/health_check",
        )

        aws_route53.ARecord(
            self,
            "OdinMongoPrivateAliasRecord",
            zone=private_zone,
            target=aws_route53.RecordTarget.from_ip_addresses(
                mongo.instance_private_ip,
            ),
            record_name="mongo.odin",
        )
        aws_route53.ARecord(
            self,
            "OdinAdminPrivateAliasRecord",
            zone=private_zone,
            target=aws_route53.RecordTarget.from_ip_addresses(
                admin.instance_private_ip,
            ),
            record_name="admin.odin",
        )
