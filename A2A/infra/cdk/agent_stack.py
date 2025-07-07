from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as ddb,
    aws_sqs as sqs,
    aws_iam as iam,
    Duration
)
from constructs import Construct

class AgentDiscoveryStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB table for agent registry
        registry_table = ddb.Table(
            self, "AgentRegistryTable",
            partition_key=ddb.Attribute(name="agent_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=ddb.RemovalPolicy.DESTROY
        )

        # SQS queues
        discovery_queue = sqs.Queue(self, "DiscoveryQueue", visibility_timeout=Duration.seconds(60))
        agent_queue = sqs.Queue(self, "AgentQueue", visibility_timeout=Duration.seconds(60))

        # Lambda functions
        discovery_api_fn = _lambda.Function(
            self, "DiscoveryApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="discovery_api.lambda_handler",
            code=_lambda.Code.from_asset("../../discovery"),
            environment={
                "DISCOVERY_TABLE": registry_table.table_name,
                "AWS_REGION": self.region
            },
            timeout=Duration.seconds(30)
        )

        discovery_processor_fn = _lambda.Function(
            self, "DiscoveryProcessorHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="discovery_processor.lambda_handler",
            code=_lambda.Code.from_asset("../../discovery"),
            environment={
                "DISCOVERY_TABLE": registry_table.table_name,
                "AWS_REGION": self.region
            },
            timeout=Duration.seconds(30)
        )

        agent_registration_fn = _lambda.Function(
            self, "AgentRegistrationHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="agent_registration.lambda_handler",
            code=_lambda.Code.from_asset("../../discovery"),
            environment={
                "DISCOVERY_TABLE": registry_table.table_name,
                "AWS_REGION": self.region
            },
            timeout=Duration.seconds(30)
        )

        # Grant permissions
        registry_table.grant_read_write_data(discovery_api_fn)
        registry_table.grant_read_write_data(discovery_processor_fn)
        registry_table.grant_read_write_data(agent_registration_fn)
        discovery_queue.grant_send_messages(discovery_api_fn)
        discovery_queue.grant_consume_messages(discovery_processor_fn)
        agent_queue.grant_send_messages(discovery_processor_fn)
        agent_queue.grant_send_messages(agent_registration_fn)

        # API Gateway
        api = apigw.LambdaRestApi(
            self, "AgentDiscoveryApi",
            handler=discovery_api_fn,
            proxy=True
        ) 