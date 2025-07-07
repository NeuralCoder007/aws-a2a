#!/usr/bin/env python3
import aws_cdk as cdk
from agent_stack import AgentDiscoveryStack

app = cdk.App()
AgentDiscoveryStack(app, "AgentDiscoveryStack")
app.synth() 