from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkflowState(TypedDict):
    input: str
    node_outputs: dict[str, Any]


class NodeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: Literal["start", "llm", "condition", "end"]
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if value in {"__start__", "__end__", "len", "__builtins__"}:
            raise ValueError("节点 id 使用了保留名称")
        return value


class EdgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    condition: Literal["true", "false"] | None = None


class WorkflowDSL(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[NodeSpec] = Field(min_length=1, max_length=100)
    edges: list[EdgeSpec] = Field(default_factory=list, max_length=200)


class RunRequest(BaseModel):
    dsl: WorkflowDSL
    input: str


class RunResponse(BaseModel):
    outputs: dict[str, Any]
