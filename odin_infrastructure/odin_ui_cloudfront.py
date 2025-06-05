# odin_ui_stack.py (new file or appended to existing OdinAPIStack)
from aws_cdk import Stack
from aws_cdk import aws_certificatemanager as certificatemanager
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3

from odin_infrastructure.config import (
    ODIN_CERTIFICATE_ARN,
    ODIN_DOMAIN_NAME,
    ODIN_UI_BUCKET,
)


class OdinUICloudfront(cloudfront.Distribution):
    def __init__(
        self,
        scope: Stack,
        id: str,
        alb_name: str,
        zone: route53.IHostedZone,
    ) -> None:
        bucket = s3.Bucket.from_bucket_name(
            scope,
            "OdinUIBucket",
            bucket_name=ODIN_UI_BUCKET,  # replace with your actual S3 bucket name
        )

        ui_origin = origins.S3Origin(bucket)

        cert = certificatemanager.Certificate.from_certificate_arn(
            scope,
            "OdinSiteCertificate",
            certificate_arn=ODIN_CERTIFICATE_ARN,
        )

        # Create CloudFront distribution
        super().__init__(
            scope,
            id,
            default_behavior=cloudfront.BehaviorOptions(
                origin=ui_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                "/rest_api/*": cloudfront.BehaviorOptions(
                    origin=origins.HttpOrigin(
                        domain_name=f"{alb_name}",  # ALB DNS name
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                )
            },
            domain_names=[ODIN_DOMAIN_NAME],
            certificate=cert,
        )

        # DNS: Route53 A record for root domain to CloudFront
        route53.ARecord(
            scope,
            "OdinUIAliasRecord",
            zone=zone,
            target=route53.RecordTarget.from_alias(targets.CloudFrontTarget(self)),
            record_name="",
        )
