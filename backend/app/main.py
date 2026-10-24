from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.errors import GraphRecursionError

from .graph_builder import build_graph
from .models import RunRequest, RunResponse

app = FastAPI(title="Workflow Demo", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    messages = [f"{'.'.join(map(str, error['loc']))}: {error['msg']}" for error in exc.errors()]
    return JSONResponse(status_code=400, content={"detail": "; ".join(messages)})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/run", response_model=RunResponse)
def run_workflow(request: RunRequest):
    try:
        graph = build_graph(request.dsl)
        state = graph.invoke(
            {"input": request.input, "node_outputs": {}},
            config={"recursion_limit": 25},
        )
        return RunResponse(outputs=state["node_outputs"])
    except GraphRecursionError as exc:
        raise HTTPException(400, "执行超过 25 步，请检查循环或缩短工作流") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc
