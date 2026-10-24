import type { NodeKind } from '../types';
import { titles } from '../types';

const kinds: NodeKind[] = ['start', 'llm', 'condition', 'end'];
const descriptions = { start: '接收工作流输入', llm: '模板替换与模拟输出', condition: '按表达式选择分支', end: '结束本次执行' };

export default function NodePanel() {
  return <aside className="node-panel">
    <h2>节点库</h2><p className="muted">拖拽节点到画布</p>
    {kinds.map(kind => <div key={kind} className={`palette-node ${kind}`} draggable
      onDragStart={event => {
        event.dataTransfer.setData('application/reactflow', kind);
        event.dataTransfer.effectAllowed = 'move';
      }}>
      <strong>{titles[kind]}</strong><code>{kind}</code><small>{descriptions[kind]}</small>
    </div>)}
    <p className="hint">从节点右侧圆点连到另一节点左侧圆点。选中节点或连线后按 Delete / Backspace 删除，也可使用右侧按钮。</p>
  </aside>;
}
