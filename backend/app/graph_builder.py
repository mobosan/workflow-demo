import ast
from collections import defaultdict
from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from .models import EdgeSpec, WorkflowDSL, WorkflowState
from .nodes import NODE_FACTORIES


def compile_expression(expression: str):
    if len(expression) > 1000:
        raise ValueError("条件表达式不能超过 1000 个字符")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"条件表达式语法错误: {exc.msg}") from exc
    allowed = (
        ast.Expression, ast.BoolOp, ast.UnaryOp, ast.Compare, ast.Call,
        ast.Name, ast.Load, ast.Constant, ast.And, ast.Or, ast.Not,
        ast.USub, ast.UAdd, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
        ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
    )
    for item in ast.walk(tree):
        if not isinstance(item, allowed):
            raise ValueError("条件仅支持 len、比较、常量以及 and/or/not")
        if isinstance(item, ast.Name) and item.id.startswith("__"):
            raise ValueError("条件不能访问内部名称")
        if isinstance(item, ast.Call) and not (
            isinstance(item.func, ast.Name) and item.func.id == "len"
            and len(item.args) == 1 and not item.keywords
        ):
            raise ValueError("条件表达式只允许调用 len(value)")
    return compile(tree, "<workflow-condition>", "eval")


def validate_workflow(dsl: WorkflowDSL) -> dict[str, list[EdgeSpec]]:
    nodes = {node.id: node for node in dsl.nodes}
    if len(nodes) != len(dsl.nodes):
        raise ValueError("节点 id 不能重复")
    starts = [node.id for node in dsl.nodes if node.type == "start"]
    if len(starts) != 1:
        raise ValueError("工作流必须恰好包含一个 start 节点")
    if not any(node.type == "end" for node in dsl.nodes):
        raise ValueError("工作流必须包含 end 节点")
    outgoing: dict[str, list[EdgeSpec]] = defaultdict(list)
    seen = set()
    for edge in dsl.edges:
        if edge.source not in nodes or edge.target not in nodes:
            raise ValueError(f"边引用了不存在的节点: {edge.source} -> {edge.target}")
        key = (edge.source, edge.target, edge.condition)
        if key in seen:
            raise ValueError("存在重复的边")
        seen.add(key)
        if nodes[edge.target].type == "start":
            raise ValueError("start 节点不能有入边")
        if nodes[edge.source].type != "condition" and edge.condition is not None:
            raise ValueError("只有 condition 节点的出边可以设置 condition")
        outgoing[edge.source].append(edge)
    for node in dsl.nodes:
        edges = outgoing[node.id]
        if node.type == "end":
            if edges:
                raise ValueError("end 节点不能有出边")
        elif node.type == "condition":
            if not 1 <= len(edges) <= 2:
                raise ValueError(f"条件节点 {node.id} 需要 1 至 2 条出边")
            labels = [edge.condition for edge in edges if edge.condition is not None]
            if len(labels) != len(set(labels)):
                raise ValueError(f"条件节点 {node.id} 的分支标签不能重复")
        elif len(edges) != 1:
            raise ValueError(f"普通节点 {node.id} 必须有一条出边；分支请使用 condition")
        field = {"llm": "prompt_template", "condition": "expression"}.get(node.type)
        if field and not isinstance(node.data.get(field), str):
            raise ValueError(f"节点 {node.id} 的 {field} 必须是字符串")
    reachable = set()
    pending = [starts[0]]
    while pending:
        current = pending.pop()
        if current not in reachable:
            reachable.add(current)
            pending.extend(edge.target for edge in outgoing[current])
    if reachable != set(nodes):
        raise ValueError("存在从 start 无法到达的节点: " + ", ".join(sorted(set(nodes) - reachable)))
    return outgoing


def build_graph(dsl: WorkflowDSL):
    outgoing = validate_workflow(dsl)
    nodes = {node.id: node for node in dsl.nodes}
    expressions = {
        node.id: compile_expression(node.data["expression"])
        for node in dsl.nodes if node.type == "condition"
    }

    def destinations(node_id: str, visiting: frozenset[str] = frozenset()) -> set[str]:
        if nodes[node_id].type != "condition":
            return {node_id}
        if node_id in visiting:
            raise ValueError("不支持只由 condition 节点组成的循环")
        result = set()
        for edge in outgoing[node_id]:
            result.update(destinations(edge.target, visiting | {node_id}))
        return result

    def create_router(condition_id: str) -> Callable[[WorkflowState], str]:
        # 每次创建独立闭包，避免循环变量晚绑定。也支持连续 condition。
        def route(state: WorkflowState) -> str:
            current = condition_id
            while nodes[current].type == "condition":
                try:
                    # 仅演示，生产环境不要用 eval。禁用内置函数，并预先限制 AST。
                    value = eval(expressions[current], {"__builtins__": {}, "len": len}, state["node_outputs"])
                except Exception as exc:
                    raise ValueError(f"条件节点 {current} 求值失败: {exc}") from exc
                label = "true" if bool(value) else "false"
                edges = outgoing[current]
                current = next((edge.target for edge in edges if edge.condition == label), edges[-1].target)
            return current

        return route

    graph = StateGraph(WorkflowState)
    for node in dsl.nodes:
        if node.type != "condition":
            graph.add_node(node.id, NODE_FACTORIES[node.type](node))
        else:
            destinations(node.id)  # 编译前拒绝没有实际执行节点的条件循环。
    for node in dsl.nodes:
        if node.type == "condition":
            continue
        for edge in outgoing[node.id]:
            if nodes[edge.target].type == "condition":
                # condition 不是执行节点：将其出边路由绑定到实际前驱节点。
                targets = destinations(edge.target)
                graph.add_conditional_edges(node.id, create_router(edge.target), {target: target for target in targets})
            else:
                graph.add_edge(edge.source, edge.target)
        if node.type == "start":
            graph.add_edge(START, node.id)
        if node.type == "end":
            graph.add_edge(node.id, END)
    return graph.compile()
