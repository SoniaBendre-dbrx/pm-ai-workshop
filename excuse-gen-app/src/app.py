import os
import json
import logging
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Excuse Email Draft Tool")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
REQUESTS = Counter('http_requests_total', 'Total HTTP requests')
ERRORS = Counter('http_errors_total', 'Total HTTP errors')

# Environment configuration
DATABRICKS_API_TOKEN = os.getenv("DATABRICKS_API_TOKEN")
DATABRICKS_ENDPOINT_URL = os.getenv("DATABRICKS_ENDPOINT_URL")

# Request/Response Models
class ExcuseRequest(BaseModel):
    category: str
    tone: str
    seriousness: int
    recipient_name: str
    sender_name: str
    eta_when: str

class ExcuseResponse(BaseModel):
    subject: str
    body: str
    success: bool
    error: Optional[str] = None

# Static file serving configuration
static_path = Path(__file__).parent.parent / "public"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = datetime.now()
    response = await call_next(request)
    duration = datetime.now() - start_time
    logger.info(
        f"Path: {request.url.path} "
        f"Duration: {duration.total_seconds():.2f}s "
        f"Status: {response.status_code}"
    )
    return response

@app.get("/")
async def root():
    """Serve the React frontend"""
    index_path = static_path / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(str(index_path))

@app.get("/health")
@app.get("/healthz")
@app.get("/ready")
@app.get("/ping")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.get("/debug")
async def debug():
    """Debug endpoint for environment information"""
    return {
        "environment": {
            "databricks_endpoint_configured": bool(DATABRICKS_ENDPOINT_URL),
            "databricks_token_configured": bool(DATABRICKS_API_TOKEN),
            "static_path": str(static_path),
            "python_version": os.sys.version,
        }
    }

@app.post("/api/generate-excuse", response_model=ExcuseResponse)
async def generate_excuse(request: ExcuseRequest):
    """Generate an excuse email based on the provided parameters"""
    try:
        REQUESTS.inc()
        
        if not DATABRICKS_API_TOKEN or not DATABRICKS_ENDPOINT_URL:
            raise HTTPException(
                status_code=500,
                detail="Databricks configuration not found"
            )

        # Construct prompt for the LLM
        prompt = f"""Generate a professional excuse email with the following parameters:
        Category: {request.category}
        Tone: {request.tone}
        Seriousness Level: {request.seriousness}/5
        Recipient: {request.recipient_name}
        Sender: {request.sender_name}
        Timing: {request.eta_when}

        Respond with ONLY a JSON object in the following format:
        {{
            "subject": "Brief and professional subject line",
            "body": "Complete email body with greeting, explanation, and sign-off"
        }}

        Make sure the email body is appropriately formatted with proper line breaks and a professional tone."""

        # Call Databricks Model Serving endpoint
        request_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that generates excuse emails in JSON format."},
                {"role": "user", "content": prompt}
            ]
        }
        logger.info(f"Sending request to Databricks: {json.dumps(request_data, indent=2)}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DATABRICKS_ENDPOINT_URL,
                    headers={
                        "Authorization": f"Bearer {DATABRICKS_API_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json=request_data,
                    timeout=30.0
                )

                response_body = await response.aread()
                response_text = response_body.decode('utf-8')
                logger.info(f"Raw response from Databricks: {response_text}")

                if response.status_code != 200:
                    logger.error(f"Databricks API error response: {response_text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Error calling Databricks Model Serving: {response_text}"
                    )

                try:
                    response_json = json.loads(response_text)
                    logger.info(f"Parsed JSON response: {json.dumps(response_json, indent=2)}")
                    
                    # Extract the model's output
                    if isinstance(response_json, dict):
                        if "choices" in response_json and len(response_json["choices"]) > 0:
                            content = response_json["choices"][0]["message"]["content"]
                            # Content might be a list of objects or a string
                            if isinstance(content, list):
                                # Find the text object in the content list
                                text_obj = next((item for item in content if item.get("type") == "text"), None)
                                if text_obj:
                                    model_output = text_obj["text"]
                                else:
                                    raise ValueError("No text object found in response content")
                            else:
                                model_output = content
                        else:
                            raise ValueError("No choices found in response")
                    else:
                        raise ValueError("Response is not a dictionary")

                    # Try to parse the model output as JSON
                    try:
                        # Remove any potential markdown code block markers
                        clean_text = model_output.replace("```json", "").replace("```", "").strip()
                        parsed_output = json.loads(clean_text)
                        
                        return ExcuseResponse(
                            subject=parsed_output["subject"],
                            body=parsed_output["body"],
                            success=True
                        )
                    except json.JSONDecodeError:
                        # If JSON parsing fails, try to extract subject and body from the text
                        lines = model_output.split("\n")
                        subject_line = next((line for line in lines if "Subject:" in line), "")
                        subject = subject_line.replace("Subject:", "").strip()
                        
                        # Get the body by removing the subject line and any empty lines
                        body_lines = [line for line in lines if line != subject_line and line.strip()]
                        body = "\n".join(body_lines)
                        
                        return ExcuseResponse(
                            subject=subject or "Excuse Email",
                            body=body or model_output,
                            success=True
                        )

                except Exception as e:
                    logger.error(f"Error parsing response: {str(e)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error parsing model response: {str(e)}"
                    )

        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to connect to Databricks: {str(e)}"
            )

    except Exception as e:
        ERRORS.inc()
        logger.error(f"Error generating excuse: {str(e)}")
        return ExcuseResponse(
            subject="",
            body="",
            success=False,
            error=str(e)
        )