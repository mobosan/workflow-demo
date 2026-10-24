import { useCallback, useRef, useState, type DragEvent } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap, MarkerType,
  useNodesState, useEdgesState, useReactFlow, type Connection,
} from '@xyflow/react';
import NodePanel from './components/NodePanel';
import CustomNode from './components/CustomNode';
import ConfigPanel from './components/ConfigPanel';
import { runWorkflow } from './api';
import { createExample } from './example';
import { toDSL, type Branch, type NodeData, type NodeKind, type WorkflowEdge, type WorkflowNode } from './types';

const nodeTypes = { start: CustomNode, llm: CustomNode, condition: CustomNode, end: CustomNode };
const initial = createExample();

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<WorkflowEdge>(initial.edges);
  const [input, setInput] = useState('你好');
  const [outputs, setOutputs] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);
  const [exported, setExported] = useState('');
  const busy = useRef(false);
  const { screenToFlowPosition, fitView, deleteElements } = useReactFlow<WorkflowNode, WorkflowEdge>();
  const selectedNode = nodes.find(node => node.selected);
  const selectedEdge = selectedNode ? undefined : edges.find(edge => edge.selected);

  const onConnect = useCallback((connection: Connection) => {
    const source = nodes.find(node => node.id === connection.source);
    setEdges(current => {
      // 不用 addEdge 去重：同一目标也可以分别配置 true / false 两条边。
      const siblingEdges = current.filter(edge => edge.source === connection.source);
      const condition = source?.type === 'condition'
        ? (siblingEdges.some(edge => edge.data?.condition === 'true') ? 'false' : 'true') : undefined;
      return [...current, {
        ...connection, id: `edge_${crypto.randomUUID()}`, type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed }, data: { condition }, label: condition,
      }];
    });
  }, [nodes, setEdges]);

  const onDrop = useCallback((event: DragEvent) => {
    event.preventDefault();
    const kind = event.dataTransfer.getData('application/reactflow') as NodeKind;
    if (!['start', 'llm', 'condition', 'end'].includes(kind)) return;
    const position = screenToFlowPosition({ x: event.clientX, y: event.clientY });
    setNodes(current => {
      const prefix = kind === 'condition' ? 'cond' : kind;
      let number = 1;
      while (current.some(node => node.id === `${prefix}_${number}`)) number++;
      const data: NodeData = kind === 'llm' ? { prompt_template: '总结：{{input}}' }
        : kind === 'condition' ? { expression: 'len(llm_1) > 20' } : {};
      return [...current.map(node => ({ ...node, selected: false })), { id: `${prefix}_${number}`, type: kind, position, data, selected: true }];
    });
    setEdges(current => current.map(edge => ({ ...edge, selected: false })));
  }, [screenToFlowPosition, setNodes, setEdges]);

  const updateNode = (id: string, data: NodeData) => setNodes(current => current.map(node => node.id === id ? { ...node, data: { ...node.data, ...data } } : node));
  const updateEdge = (id: string, condition?: Branch) => setEdges(current => current.map(edge => edge.id === id ? { ...edge, data: { condition }, label: condition } : edge));

  const loadExample = () => {
    const example = createExample();
    setNodes(example.nodes); setEdges(example.edges);
    setOutputs(null); setError(''); setExported('');
    window.setTimeout(() => void fitView({ padding: 0.2, duration: 200 }), 50);
  };

  const run = async () => {
    if (busy.current) return;
    busy.current = true;
    setRunning(true); setError(''); setOutputs(null);
    try { setOutputs(await runWorkflow(toDSL(nodes, edges), input)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : String(cause)); }
    finally { busy.current = false; setRunning(false); }
  };

  return <div className="app-shell">
    <header><div><h1>Workflow Demo</h1><span>拖拽编排 · LangGraph 执行 · Mock LLM</span></div>
      <div className="toolbar"><button onClick={loadExample} disabled={running}>加载示例工作流</button>
        <button onClick={() => setExported(JSON.stringify(toDSL(nodes, edges), null, 2))}>导出 DSL</button></div>
    </header>
    <main className="editor">
      <NodePanel />
      <section className="canvas" aria-label="工作流画布" onDrop={onDrop} onDragOver={event => { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; }}>
        <ReactFlow<WorkflowNode, WorkflowEdge> nodes={nodes} edges={edges} nodeTypes={nodeTypes}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} onConnect={onConnect}
          deleteKeyCode={['Backspace', 'Delete']} fitView fitViewOptions={{ padding: 0.2 }} minZoom={0.25} maxZoom={2}
          isValidConnection={connection => nodes.find(node => node.id === connection.source)?.type !== 'end' && nodes.find(node => node.id === connection.target)?.type !== 'start'}>
          <Background gap={20} /><Controls /><MiniMap pannable zoomable />
        </ReactFlow>
      </section>
      <ConfigPanel node={selectedNode} edge={selectedEdge} edgeSource={nodes.find(node => node.id === selectedEdge?.source)}
        updateNode={updateNode} updateEdge={updateEdge}
        deleteSelection={() => void deleteElements({ nodes: nodes.filter(node => node.selected), edges: edges.filter(edge => edge.selected) })} />
    </main>
    <section className="execution">
      <div className="input-panel"><label htmlFor="workflow-input">工作流输入</label>
        <textarea id="workflow-input" rows={3} value={input} onChange={event => setInput(event.target.value)} />
        <button className="primary" onClick={() => void run()} disabled={running}>{running ? '运行中…' : '运行工作流'}</button>
      </div>
      <div className="output-panel" aria-live="polite"><h2>node_outputs <span>上次运行的结果</span></h2>
        {error && <div role="alert" className="error">{error}</div>}
        <pre>{outputs ? JSON.stringify(outputs, null, 2) : running ? '正在执行…' : '运行后在此查看各节点输出。'}</pre>
        <small>start 保存输入；LLM 返回模拟文本；condition 只路由，end 为空操作，因此不出现在输出中。</small>
      </div>
    </section>
    {exported && <section className="dsl-panel"><label htmlFor="dsl-output">当前画布 DSL（导出时的快照）</label>
      <textarea id="dsl-output" rows={15} readOnly value={exported} spellCheck={false} />
    </section>}
  </div>;
}
