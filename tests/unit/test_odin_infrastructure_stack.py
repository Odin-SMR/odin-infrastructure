import aws_cdk
import aws_cdk.assertions as assertions

from odin_infrastructure.odin_api_stack import OdinAPIStack
from odin_infrastructure.config import ODIN_AWS_ACCOUNT, ODIN_AWS_REGION


# example tests. To run these tests, uncomment this file along with the example
# resource in odin_infrastructure/odin_infrastructure_stack.py
def test_sqs_queue_created():
    app = aws_cdk.App()
    stack = OdinAPIStack(
        app,
        "odin-api",
        env=aws_cdk.Environment(account=ODIN_AWS_ACCOUNT, region=ODIN_AWS_REGION),
    )
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::EC2::Instance", {"Tags": [{"Key": "Name", "Value": "OdinMongo"}]}
    )
    template.has_resource_properties(
        "AWS::EC2::Instance", {"Tags": [{"Key": "Name", "Value": "OdinAdmin"}]}
    )
    template.has_resource_properties(
        "AWS::EC2::VPC", {"Tags": [{"Key": "Name", "Value": "OdinVPC"}]}
    )
