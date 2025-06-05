from aws_cdk import Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_route53
from constructs import Construct

from odin_infrastructure.odin_ui_cloudfront import OdinUICloudfront

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

        public_zone: aws_route53.IHostedZone = aws_route53.HostedZone.from_lookup(
            self, "OdinPublicZone", domain_name="odin-smr.org"
        )

        private_zone: aws_route53.IHostedZone = aws_route53.PrivateHostedZone(
            self,
            "OdinPrivateZone",
            vpc=vpc,
            zone_name="odin",
        )

        mongo: ec2.IInstance = MongoInstance(self, "OdinMongo", vpc, zone=private_zone)
        admin: ec2.IInstance = AdminInstance(
            self, "OdinAdmin", vpc, public_zone=public_zone, private_zone=private_zone
        )
        cluster: ecs.ICluster = ecs.Cluster(
            self, "OdinCluster", vpc=vpc, cluster_name="OdinApiCluster"
        )
        service = OdinService(
            self,
            "OdinAPIFargateService",
            mongo,
            cluster,
        )

        OdinUICloudfront(
            self,
            "OdinUICloudFront",
            alb_name=service.load_balancer.load_balancer_dns_name,
            zone=public_zone,
        )
