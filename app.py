#!/usr/bin/env python3
import aws_cdk as cdk
from odin_infrastructure.config import ODIN_AWS_ACCOUNT, ODIN_AWS_REGION

from odin_infrastructure.odin_api_stack import OdinAPIStack


app = cdk.App()
OdinAPIStack(
    app,
    "OdinAPIStack",
    env=cdk.Environment(account=ODIN_AWS_ACCOUNT, region=ODIN_AWS_REGION),
)

app.synth()
