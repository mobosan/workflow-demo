import { MarkerType } from '@xyflow/react';
import type { WorkflowEdge, WorkflowNode } from './types';

export function createExample(): { nodes: WorkflowNode[]; edges: WorkflowEdge[] } {
  return {
    nodes: [
      { id: 'start', type: 'start', position: { x: 50, y: 180 }, data: {} },
      { id: 'llm_1', type: 'llm', position: { x: 320, y: 180 }, data: { prompt_template: '总结：{{input}}' } },
      { id: 'cond_1', type: 'condition', position: { x: 590, y: 180 }, data: { expression: 'len(llm_1) > 20' } },
      { id: 'llm_long', type: 'llm', position: { x: 860, y: 40 }, data: { prompt_template: '展开：{{llm_1.output}}' } },
      { id: 'end', type: 'end', position: { x: 1130, y: 180 }, data: {} },
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'llm_1' },
      { id: 'e2', source: 'llm_1', target: 'cond_1' },
      { id: 'e3', source: 'cond_1', target: 'llm_long', data: { condition: 'true' }, label: 'true' },
      { id: 'e4', source: 'cond_1', target: 'end', data: { condition: 'false' }, label: 'false' },
      { id: 'e5', source: 'llm_long', target: 'end' },
    ].map(edge => ({ ...edge, type: 'smoothstep', markerEnd: { type: MarkerType.ArrowClosed } } as WorkflowEdge)),
  };
}
