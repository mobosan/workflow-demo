import re
from collections.abc import Callable

from .models import NodeSpec, WorkflowState

NodeFunction = Callable[[WorkflowState], dict]
VARIABLE = re.compile(r"\{\{\s*(.*?)\s*\}\}")


def render_template(template: str, state: WorkflowState) -> str:
    def replace(match: re.Match) -> str:
        variable = match.group(1).strip()
        if variable == "input":
            return state["input"]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.output", variable):
            node_id = variable.removesuffix(".output")
            if node_id not in state["node_outputs"]:
                raise ValueError(f"模板引用的节点 {node_id} 尚未产生输出")
            return str(state["node_outputs"][node_id])
        raise ValueError(f"不支持的模板变量: {variable}")

    return VARIABLE.sub(replace, template)


def create_start(node: NodeSpec) -> NodeFunction:
    def run(state: WorkflowState) -> dict:
        return {
            "input": state["input"],
            "node_outputs": {**state["node_outputs"], node.id: state["input"]},
        }

    return run


def create_llm(node: NodeSpec) -> NodeFunction:
    template = node.data["prompt_template"]

    def run(state: WorkflowState) -> dict:
        output = f"[mock-llm:{node.id}] {render_template(template, state)}"
        return {"node_outputs": {**state["node_outputs"], node.id: output}}

    return run


def create_end(node: NodeSpec) -> NodeFunction:
    def run(state: WorkflowState) -> dict:
        # end 是空操作，不添加业务输出，也不会覆盖已有输出。
        return {}

    return run


NODE_FACTORIES = {"start": create_start, "llm": create_llm, "end": create_end}
