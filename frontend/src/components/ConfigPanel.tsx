import type { Branch, NodeData, WorkflowEdge, WorkflowNode } from '../types';

interface Props {
  node?: WorkflowNode;
  edge?: WorkflowEdge;
  edgeSource?: WorkflowNode;
  updateNode: (id: string, data: NodeData) => void;
  updateEdge: (id: string, condition?: Branch) => void;
  deleteSelection: () => void;
}

export default function ConfigPanel({ node, edge, edgeSource, updateNode, updateEdge, deleteSelection }: Props) {
  return <aside className="config-panel">
    <h2>配置</h2>
    {node ? <>
      <p className="selection-id">{node.id}</p><p className="muted">类型：{node.type}</p>
      {node.type === 'llm' && <label>prompt_template
        <textarea rows={7} value={node.data.prompt_template ?? ''} onChange={event => updateNode(node.id, { prompt_template: event.target.value })} />
        <small>支持 {'{{input}}'} 和 {'{{node_id.output}}'}。</small>
      </label>}
      {node.type === 'condition' && <label>expression
        <textarea rows={5} value={node.data.expression ?? ''} onChange={event => updateNode(node.id, { expression: event.target.value })} />
        <small>例如 len(llm_1) &gt; 20。节点 id 直接代表输出字符串。请为出边配置 true / false。</small>
      </label>}
      {(node.type === 'start' || node.type === 'end') && <p className="hint">此节点无需额外配置。</p>}
    </> : edge ? <>
      <p className="selection-id">{edge.source} → {edge.target}</p>
      <label>condition
        <select value={edge.data?.condition ?? ''} disabled={edgeSource?.type !== 'condition'}
          onChange={event => updateEdge(edge.id, (event.target.value || undefined) as Branch | undefined)}>
          <option value="">未设置</option><option value="true">true</option><option value="false">false</option>
        </select>
      </label>
      <p className="hint">仅 condition 节点的出边使用分支标签。未匹配时走最后一条出边。</p>
    </> : <p className="hint">选择一个节点或一条连线，即可编辑配置。修改会立即应用到画布。</p>}
    {(node || edge) && <button className="danger" onClick={deleteSelection}>删除选中项</button>}
  </aside>;
}
