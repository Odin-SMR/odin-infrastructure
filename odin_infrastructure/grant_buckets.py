from aws_cdk.aws_iam import IRole
from aws_cdk import Stack
from aws_cdk.aws_s3 import Bucket


def grant_read_buckets(scope: Stack, taskrole: IRole, bucket_names: list[str]):
    for bucket_name in bucket_names:
        bucket = Bucket.from_bucket_name(
            scope=scope, id=f"Odin-{bucket_name}", bucket_name=bucket_name
        )
        bucket.grant_read(taskrole)
