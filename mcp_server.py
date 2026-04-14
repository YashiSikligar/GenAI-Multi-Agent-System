
import os
import shutil
import tempfile

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests  import Request
from starlette.responses import JSONResponse

load_dotenv()


#we basically load the agents once and reuse them for every request to avaoid re-initializing the LLM and DB on every call.

_sql_agent = None
_rag_agent = None
_router = None


def get_agents():
    """Initialize agents once and return them it is safe to call multiple times"""
    global _sql_agent, _rag_agent, _router

    if _router is None:
        print("[MCP Server] Initialising agents...")
        from sql_agent import SQLAgent
        from rag_agent import RAGAgent
        from router_agent import RouterOrchestrator

        _sql_agent= SQLAgent()           
        _rag_agent= RAGAgent()           
        _router = RouterOrchestrator(_sql_agent, _rag_agent)  
        print("[MCP Server] All agents ready.")

    return _sql_agent, _rag_agent, _router


#creating the MCP server

mcp = FastMCP(name="Customer Support Multi-Agent MCP Server")


@mcp.tool
def chat_with_agent(query: str) -> str:

    _, _, router = get_agents()
    #here the router decides rag/sql
    result = router.run(query)
    return result["answer"]

#tool for uploading the pdf
@mcp.tool
def upload_policy_pdf(filename: str, file_bytes_base64: str) -> str:
 
    #for decoding files data
    import base64

    #checks and only pdf are allowed
    if not filename.lower().endswith(".pdf"):
        return "Only PDF files are supported."

    try:
        pdf_bytes = base64.b64decode(file_bytes_base64)
    except Exception:
        return "Could not decode file. Make sure it is base64-encoded."

    #save to a temp file on the disk and pass path to RAGAgent.add_pdf()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        _, rag, _ =get_agents()
        #pdf is processed, chunks are created, embeddings are generated and stored in VB
        chunks =rag.add_pdf(tmp_path)
    finally:
        os.unlink(tmp_path) #delete temp file

    return f"'{filename}' uploaded and indexed successfully. {chunks} chunks added to RAG knowledge base."

#this tool is for checking the server status
@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """
    Health check basically is called by app.py on every page load to check server status and 
    returns rag_ready=True once when one PDF has been uploaded and indexed
    """
    _, rag, _ = get_agents()
    return JSONResponse({
        "status":"healthy",
        "rag_ready":rag.is_ready(), 
        "sql_ready":True,  #ready (DB seeded on startup)
    })


@mcp.custom_route("/chat", methods=["POST"])
async def chat(request: Request) -> JSONResponse:
    """
    chat endpoint called by app.py with {"query": "..."}
    runs the full LangGraph pipeline and returns the answer.
    """
    body  = await request.json() #reads JSON request
    query = body.get("query", "").strip() #extracts user query

    if not query:
        return JSONResponse({"error": "Query cannot be empty."}, status_code=400)

    _, _, router = get_agents()
    result = router.run(query)   #route to the specific agent

    return JSONResponse({
        "answer": result["answer"],
        "agent_used": result["route"],   
    })


@mcp.custom_route("/upload_pdf", methods=["POST"])
async def upload_pdf(request: Request) -> JSONResponse:
    """
    here the pDF upload endpoint is called by app.py as multipart/form-data we saves the PDF to a temp file and pass to to RAG,
    then returns chunk count so app.py can show the success message.

    """
    form = await request.form()
    file_obj = form.get("file")

    if file_obj is None:
        return JSONResponse({"error": "No file provided."}, status_code=400)

    filename = file_obj.filename
    if not filename.lower().endswith(".pdf"):
        return JSONResponse({"error": "Only PDF files are accepted."}, status_code=400)

    # Save uploaded bytes to a temp file (RAGAgent.add_pdf needs a file path)
    contents = await file_obj.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        _, rag, _ = get_agents()
        chunks = rag.add_pdf(tmp_path)   # RAGAgent.add_pdf() → int (chunk count)
    finally:
        os.unlink(tmp_path)  # always clean up the temp file

    return JSONResponse({
        "message":  f"PDF '{filename}' indexed successfully.",
        "chunks_indexed": chunks,
        "filename": filename,
    })




if __name__ == "__main__":
    #preloads agents so first request is fast
    get_agents()

    print("\n Customer Support MCP Server starting...")
    print(" MCP protocol - http://localhost:8000/mcp")
    print(" Health check - http://localhost:8000/health")
    print(" Chat API- http://localhost:8000/chat")
    print(" PDF upload - http://localhost:8000/upload_pdf")
    print("\n MCP Tools: chat_with_agent, upload_policy_pdf")
    print(" Run UI with: streamlit run app.py\n")

    #HTTP transport so app.py can reach us over the network
    mcp.run(transport="http", host="0.0.0.0", port=8000)
