import { Handle, Position, type NodeProps } from '@xyflow/react';
import { titles, type WorkflowNode } from '../types';

export default function CustomNode({ id, type, data, selected }: NodeProps<WorkflowNode>) {
  const kind = type ?? 'llm';
  const summary = data.prompt_template ?? data.expression ?? (kind === 'start' ? '工作流输入' : '结束执行');
  return <div className={`workflow-node ${kind} ${selected ? 'selected' : ''}`}>
    {kind !== 'start' && <Handle type="target" position={Position.Left} />}
    <div className="node-heading"><strong>{titles[kind]}</strong><span>{kind}</span></div>
    <code>{id}</code><p title={summary}>{summary}</p>
    {kind !== 'end' && <Handle type="source" position={Position.Right} />}
  </div>;
}
