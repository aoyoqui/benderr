## Installation

* Install uv
* Create environment with ```uv sync```
* Try to execute a demo sequence with ```benderr --sequence demo-sequenc --config "packages/demos/src/br_demos/demo_steps.json"```

## gRPC proto

Run the following when making changes to a protobuff:
```
uv run python -m grpc_tools.protoc -Ipackages/br_sdk/proto --python_out=packages/br_sdk/src --grpc_python_out=packages/br_sdk/src packages/br_sdk/proto/events.proto
```
