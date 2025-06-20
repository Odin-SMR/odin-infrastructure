from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2,
    aws_ecs,
    aws_ecs_patterns,
    aws_ecr,
    aws_elasticloadbalancingv2,
    aws_logs,
    aws_ssm,
)

from .grant_buckets import grant_read_buckets


class OdinService(aws_ecs_patterns.ApplicationLoadBalancedFargateService):
    def __init__(
        self,
        scope: Stack,
        id: str,
        mongo: aws_ec2.IInstance,
        cluster: aws_ecs.ICluster,
    ):
        log_group = aws_logs.LogGroup(
            scope,
            "OdinClusterLogGroup",
            log_group_name="/Odin/OdinApi",
            removal_policy=RemovalPolicy.DESTROY,
            retention=aws_logs.RetentionDays.SIX_MONTHS,
        )

        logging = aws_ecs.AwsLogDriver(stream_prefix="OdinAPI", log_group=log_group)

        odinapi_task: aws_ecs.FargateTaskDefinition = aws_ecs.FargateTaskDefinition(
            scope,
            "OdinAPITaskDefinition",
            cpu=2048,
            memory_limit_mib=4096,
        )
        grant_read_buckets(
            scope,
            odinapi_task.task_role,
            [
                "odin-apriori",
                "odin-era5",
                "odin-osiris",
                "odin-psql",
                "odin-smr",
                "odin-solar",
                "odin-vds-data",
                "odin-zpt",
            ],
        )

        odin_secret_key = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinSecretKey", "/odin-api/secret-key"
        ).string_value
        odin_mongo_user = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinMongoUser", "/odin/mongo/user"
        ).string_value
        odin_mongo_password = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinMongoPassword", "/odin/mongo/password"
        ).string_value
        odin_pghost = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinPGHOST", "/odin/psql/host"
        ).string_value
        odin_pguser = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinPGUSER", "/odin/psql/user"
        ).string_value
        odin_pgdbname = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinPGDBNAME", "/odin/psql/db"
        ).string_value
        odin_pgpass = aws_ssm.StringParameter.from_string_parameter_name(
            scope, "OdinPGPASS", "/odin/psql/password"
        ).string_value
        ecr_repository = aws_ecr.Repository.from_repository_name(
            scope, "OdinAPIRepo", "odin-api"
        )
        odinapi_task.add_container(
            "OdinAPIContainer",
            image=aws_ecs.ContainerImage.from_ecr_repository(ecr_repository),
            port_mappings=[
                aws_ecs.PortMapping(
                    container_port=8000,
                    app_protocol=aws_ecs.AppProtocol("http2"),
                    name="odinapi",
                ),
            ],
            environment={
                "SECRET_KEY": odin_secret_key,
                "ODIN_API_PRODUCTION": "1",
                "ODINAPI_MONGODB_USERNAME": odin_mongo_user,
                "ODINAPI_MONGODB_PASSWORD": odin_mongo_password,
                "ODINAPI_MONGODB_HOST": mongo.instance_private_ip,
                "PGHOST": odin_pghost,
                "PGDBNAME": odin_pgdbname,
                "PGUSER": odin_pguser,
                "PGPASS": odin_pgpass,
            },
            health_check=aws_ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "curl -f http://localhost:8000/rest_api/health_check || exit 1",
                ],
                interval=Duration.seconds(120),
                timeout=Duration.seconds(20),
                retries=5,
            ),
            logging=logging,
        )

        super().__init__(
            scope,
            id,
            task_subnets=aws_ec2.SubnetSelection(
                subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            cpu=2048,
            service_name="OdinFargateService",
            cluster=cluster,
            desired_count=1,
            task_definition=odinapi_task,
            memory_limit_mib=4096,
            public_load_balancer=True,
            protocol=aws_elasticloadbalancingv2.ApplicationProtocol.HTTP,
            idle_timeout=Duration.seconds(360),
            redirect_http=False,
        )

        scaling = self.service.auto_scale_task_count(max_capacity=10, min_capacity=1)

        # Scale the service based on CPU Utilization
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=50,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        scaling.scale_on_request_count(
            "RequestCountScaling",
            requests_per_target=400,
            target_group=self.target_group,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )

        self.target_group.configure_health_check(
            interval=Duration.seconds(120),
            timeout=Duration.seconds(20),
            healthy_threshold_count=2,
            unhealthy_threshold_count=7,
            path="/rest_api/health_check",
        )
