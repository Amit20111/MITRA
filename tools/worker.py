"""Private subprocess entry point for the three fixed filesystem tools."""

import json
import sys
from pathlib import Path

from apps.api.contracts import Task, ToolCall
from security.policy import authorize
from tools.filesystem import PathInput, Workspace, WriteInput
from tools.registry import ToolRegistry


def main() -> None:
    payload = json.loads(sys.stdin.read())
    task = Task.model_validate(payload["task"])
    workspace = Workspace(Path(payload["workspace"]))
    step = task.steps[-1]
    ToolRegistry(workspace).validate(ToolCall(name=step.tool, arguments=step.arguments))
    authorize(task.id, step, task.approval)
    if step.tool == "write_file":
        result = workspace.write_file(WriteInput.model_validate(step.arguments))
    elif step.tool == "read_file":
        result = workspace.read_file(PathInput.model_validate(step.arguments))
    elif step.tool == "list_directory":
        result = workspace.list_directory(PathInput.model_validate(step.arguments))
    else:
        raise ValueError("Unregistered tool")
    print(result.model_dump_json())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}))
        sys.exit(1)
