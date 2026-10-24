import type { WorkflowDSL } from './types';

export async function runWorkflow(dsl: WorkflowDSL, input: string): Promise<Record<string, unknown>> {
  let response: Response;
  try {
    response = await fetch('http://localhost:8000/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dsl, input }),
      signal: AbortSignal.timeout(30000),
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'TimeoutError') {
      throw new Error('请求超时，请检查后端状态。');
    }
    throw new Error('无法连接后端，请确认 http://localhost:8000 已启动，并使用 localhost:5173 打开前端。');
  }
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body));
  return body.outputs;
}
