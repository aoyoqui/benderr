## Installation

* Install uv
* Create environment with ```uv sync```
* Execute a demo sequence with ```br_cli --sequence demo-sequence --config "packages/demos/src/br_demos/demo_steps.json"```

## gRPC proto

Make sure to re-generate the RPC interfaces when changing a proto file. Example:
```
pushd 
cd packages/br_sdk/src
uv run python -m grpc_tools.protoc -Ibr_sdk/_grpc=../proto --python_out=. --grpc_python_out=. ../proto/events.proto
popd
```

## Build

You can manually build wheels with the following command:
```
uv build --all-packages --wheel -o dist
```

## Demos

You can try out the following demos:
1. Execute any sequences in packages/demos/src/ by themselves
2. Execute them via br_cli. Example: ```br_cli --sequence demo-sequence --config "packages/demos/src/br_demos/demo_steps.json"```
3. Execute sequences with ```br_gui```
4. Execute a test plan with the agent. Example: ```python -m br_agent.main --plan test_plan.json```
