# """
# app.py
# HPCM Plagiarism Detection System — FastAPI Server
# ---------------------------------------------------
# Endpoints:
#   GET  /health  — health check
#   POST /compare — run HPCM pipeline on submitted documents
# Runs on port 8000.
# """

# import logging
# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel

# from modules.pipeline import run_full_comparison

# # ---------------------------------------------------------------------------
# # Logging
# # ---------------------------------------------------------------------------
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
# )
# logger = logging.getLogger("hpcm.api")

# # ---------------------------------------------------------------------------
# # FastAPI App
# # ---------------------------------------------------------------------------
# app = FastAPI(
#     title="HPCM Plagiarism Detection Engine",
#     description="ML engine for hybrid plagiarism detection (Lexical + Semantic + Stylometric)",
#     version="1.0.0",
# )

# # CORS — allow React (port 3000) and Node (port 5000) to call this
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://localhost:5000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ---------------------------------------------------------------------------
# # Request / Response Models
# # ---------------------------------------------------------------------------
# class SuspectDocument(BaseModel):
#     id: str
#     title: str = "Untitled"
#     text: str


# class CompareRequest(BaseModel):
#     project_id: str
#     project_text: str
#     compare_against: list[SuspectDocument]
#     use_layer4: bool = True


# class HealthResponse(BaseModel):
#     status: str
#     service: str
#     version: str


# # ---------------------------------------------------------------------------
# # Endpoints
# # ---------------------------------------------------------------------------
# @app.get("/health", response_model=HealthResponse)
# def health_check():
#     """Health check endpoint."""
#     return {
#         "status": "ok",
#         "service": "HPCM Plagiarism Detection Engine",
#         "version": "1.0.0",
#     }


# @app.post("/compare")
# def compare_documents(request: CompareRequest):
#     """
#     Run the HPCM pipeline: compare project_text against all suspect documents.

#     Receives from Node.js backend:
#     {
#         "project_id": "abc123",
#         "project_text": "full text of the uploaded document...",
#         "compare_against": [
#             {"id": "doc1", "title": "Some Paper", "text": "..."},
#             {"id": "doc2", "title": "Another Paper", "text": "..."}
#         ],
#         "use_layer4": true
#     }
#     """
#     # Validate input
#     if not request.project_text.strip():
#         raise HTTPException(status_code=400, detail="project_text is empty")

#     if not request.compare_against:
#         raise HTTPException(status_code=400, detail="compare_against list is empty")

#     logger.info(
#         "Compare request: project=%s against %d documents (layer4=%s)",
#         request.project_id,
#         len(request.compare_against),
#         request.use_layer4,
#     )

#     try:
#         # Convert Pydantic models to dicts for pipeline
#         suspects = [
#             {"id": s.id, "title": s.title, "text": s.text}
#             for s in request.compare_against
#         ]

#         result = run_full_comparison(
#             project_id=request.project_id,
#             project_text=request.project_text,
#             compare_against=suspects,
#             use_layer4=request.use_layer4,
#         )

#         logger.info(
#             "Compare complete: project=%s → highest_risk=%s, highest_score=%.4f",
#             request.project_id,
#             result["highest_risk"],
#             result["highest_score"],
#         )
#         return result

#     except Exception as e:
#         logger.error("Pipeline error: %s", str(e), exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


# # ---------------------------------------------------------------------------
# # Run directly: uvicorn
# # ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     import uvicorn
#     import os
#     port = int(os.environ.get("PORT", 8000))
#     uvicorn.run(app, host="0.0.0.0", port=port)

"""
app.py
HPCM Plagiarism Detection System — FastAPI Server
---------------------------------------------------
Endpoints:
  GET  /health  — health check
  POST /compare — run HPCM pipeline on submitted documents
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from modules.pipeline import run_full_comparison

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
)
logger = logging.getLogger("hpcm.api")

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="HPCM Plagiarism Detection Engine",
    description="ML engine for hybrid plagiarism detection (Lexical + Semantic + Stylometric)",
    version="1.0.0",
)

# CORS — allow all origins for deployment flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------
class SuspectDocument(BaseModel):
    id: str
    title: str = "Untitled"
    text: str


class CompareRequest(BaseModel):
    project_id: str
    project_text: str
    compare_against: list[SuspectDocument]
    use_layer4: bool = True


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "HPCM Plagiarism Detection Engine"}
@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "HPCM Plagiarism Detection Engine",
        "version": "1.0.0",
    }


@app.post("/compare")
def compare_documents(request: CompareRequest):
    """
    Run the HPCM pipeline: compare project_text against all suspect documents.
    """
    if not request.project_text.strip():
        raise HTTPException(status_code=400, detail="project_text is empty")

    if not request.compare_against:
        raise HTTPException(status_code=400, detail="compare_against list is empty")

    logger.info(
        "Compare request: project=%s against %d documents (layer4=%s)",
        request.project_id,
        len(request.compare_against),
        request.use_layer4,
    )

    try:
        suspects = [
            {"id": s.id, "title": s.title, "text": s.text}
            for s in request.compare_against
        ]

        result = run_full_comparison(
            project_id=request.project_id,
            project_text=request.project_text,
            compare_against=suspects,
            use_layer4=request.use_layer4,
        )

        logger.info(
            "Compare complete: project=%s → highest_risk=%s, highest_score=%.4f",
            request.project_id,
            result["highest_risk"],
            result["highest_score"],
        )
        return result

    except Exception as e:
        logger.error("Pipeline error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)