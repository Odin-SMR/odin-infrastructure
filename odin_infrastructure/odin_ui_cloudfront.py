from aws_cdk import aws_certificatemanager as certificatemanager
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_elasticloadbalancingv2
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from constructs import Construct

from odin_infrastructure.config import (
    ODIN_CERTIFICATE_ARN,
    ODIN_DOMAIN_NAME,
    ODIN_UI_BUCKET,
)


class OdinUICloudfront(cloudfront.Distribution):
    def __init__(
        self,
        scope: Construct,
        id: str,
        alb_name: aws_elasticloadbalancingv2.ILoadBalancerV2,
        zone: route53.IHostedZone,
    ) -> None:
        bucket = s3.Bucket(
            scope,
            "OdinUIBucket",
            bucket_name=ODIN_UI_BUCKET,
        )

        cert = certificatemanager.Certificate.from_certificate_arn(
            scope,
            "OdinSiteCertificate",
            certificate_arn=ODIN_CERTIFICATE_ARN,
        )

        super().__init__(
            scope,
            id,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    bucket,
                    origin_access_levels=[
                        cloudfront.AccessLevel.READ,
                    ],
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/rest_api/*": cloudfront.BehaviorOptions(
                    origin=origins.LoadBalancerV2Origin(
                        load_balancer=alb_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
                    ),
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                )
            },
            default_root_object="index.html",
            domain_names=[ODIN_DOMAIN_NAME],
            certificate=cert,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                )
            ],
        )
        
        route53.ARecord(
            scope,
            "OdinUIAliasRecord",
            zone=zone,
            target=route53.RecordTarget.from_alias(targets.CloudFrontTarget(self)),
            record_name="",
        )
