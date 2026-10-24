import type { Edge, Node } from '@xyflow/react';

export type NodeKind = 'start' | 'llm' | 'condition' | 'end';
export type Branch = 'true' | 'false';
export type NodeData = { prompt_template?: string; expression?: string };
export type WorkflowNode = Node<NodeData, NodeKind>;
export type WorkflowEdge = Edge<{ condition?: Branch }>;
export interface WorkflowDSL {
  nodes: { id: string; type: NodeKind; data: NodeData }[];
  edges: { source: string; target: string; condition?: Branch }[];
}

export const titles: Record<NodeKind, string> = {
  start: '开始', llm: '模拟 LLM', condition: '条件分支', end: '结束',
};

export function toDSL(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowDSL {
  return {
    nodes: nodes.map(({ id, type, data }) => ({ id, type: type!, data })),
    edges: edges.map(({ source, target, data }) => ({
      source, target, ...(data?.condition ? { condition: data.condition } : {}),
    })),
  };
}
