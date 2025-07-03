from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uvicorn
import os

from backend.models.database import get_db, create_tables, GeospatialJob, GeospatialData
from backend.services.job_queue import JobQueue, process_geospatial_job
from backend.config import Config

app = FastAPI(title="AI-Powered Geospatial Analysis Platform", version="1.0.0")

# Create database tables
create_tables()

# Initialize services
job_queue = JobQueue()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main application page"""
    with open("frontend/index.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/jobs/")
async def create_job(request: Dict[str, Any], db: Session = Depends(get_db)):
    """Create a new geospatial analysis job"""
    try:
        # Create job record
        job = GeospatialJob(
            user_query=request.get("query", ""),
            status="pending"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Enqueue job for processing
        job_queue.enqueue_job(str(job.id), {"query": request.get("query", "")})
        
        # Start processing (in production, this would be handled by Celery workers)
        process_geospatial_job.delay(str(job.id))
        
        return {"job_id": job.id, "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Get job status and results"""
    job = db.query(GeospatialJob).filter(GeospatialJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.id,
        "status": job.status,
        "created_at": job.created_at.isoformat(),
        "plan": job.plan,
        "code": job.code,
        "result": job.result,
        "error_message": job.error_message,
        "is_completed": job.is_completed
    }

@app.get("/api/jobs/")
async def list_jobs(db: Session = Depends(get_db)):
    """List all jobs"""
    jobs = db.query(GeospatialJob).order_by(GeospatialJob.created_at.desc()).limit(50).all()
    return [
        {
            "job_id": job.id,
            "query": job.user_query,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "is_completed": job.is_completed
        }
        for job in jobs
    ]

@app.post("/api/data/upload")
async def upload_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload geospatial data"""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Determine data type
        data_type = "unknown"
        if file.filename.endswith(('.shp', '.geojson', '.json')):
            data_type = "vector"
        elif file.filename.endswith(('.tif', '.tiff', '.jpg', '.png')):
            data_type = "raster"
        
        # Save to database
        data_record = GeospatialData(
            name=file.filename,
            data_type=data_type,
            file_path=file_path,
            metadata={"original_filename": file.filename, "size": len(content)}
        )
        db.add(data_record)
        db.commit()
        
        return {"message": "File uploaded successfully", "data_id": data_record.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/")
async def list_data(db: Session = Depends(get_db)):
    """List available geospatial data"""
    data = db.query(GeospatialData).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "data_type": item.data_type,
            "created_at": item.created_at.isoformat(),
            "metadata": item.metadata
        }
        for item in data
    ]

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)