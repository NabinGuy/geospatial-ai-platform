import redis
import json
from typing import Dict, Any, Optional
from celery import Celery
from backend.config import Config

# Initialize Redis connection
redis_client = redis.from_url(Config.REDIS_URL)

# Initialize Celery
celery_app = Celery('geospatial_tasks', broker=Config.REDIS_URL)

class JobQueue:
    def __init__(self):
        self.redis_client = redis_client
    
    def enqueue_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Add a job to the queue"""
        try:
            self.redis_client.lpush("geospatial_jobs", json.dumps({
                "job_id": job_id,
                "data": job_data
            }))
            return True
        except Exception as e:
            print(f"Failed to enqueue job: {e}")
            return False
    
    def dequeue_job(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get a job from the queue"""
        try:
            result = self.redis_client.brpop("geospatial_jobs", timeout=timeout)
            if result:
                return json.loads(result[1])
            return None
        except Exception as e:
            print(f"Failed to dequeue job: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        try:
            status = self.redis_client.get(f"job_status:{job_id}")
            if status:
                return json.loads(status)
            return None
        except Exception as e:
            print(f"Failed to get job status: {e}")
            return None
    
    def update_job_status(self, job_id: str, status: Dict[str, Any]) -> bool:
        """Update job status"""
        try:
            self.redis_client.set(
                f"job_status:{job_id}",
                json.dumps(status),
                ex=3600  # Expire after 1 hour
            )
            return True
        except Exception as e:
            print(f"Failed to update job status: {e}")
            return False

# Celery task for processing geospatial jobs
@celery_app.task
def process_geospatial_job(job_id: str):
    """Process a geospatial analysis job"""
    from backend.agents.planner import PlannerAgent
    from backend.agents.coder import CoderAgent
    from backend.agents.validator import ValidatorAgent
    from backend.models.database import SessionLocal, GeospatialJob
    
    db = SessionLocal()
    job_queue = JobQueue()
    
    try:
        # Get job from database
        job = db.query(GeospatialJob).filter(GeospatialJob.id == job_id).first()
        if not job:
            return {"error": "Job not found"}
        
        # Update status
        job_queue.update_job_status(job_id, {"status": "processing", "stage": "planning"})
        
        # Step 1: Create plan
        planner = PlannerAgent()
        plan = planner.create_plan(job.user_query, [])  # Add available data
        
        if "error" in plan:
            job.status = "failed"
            job.error_message = plan["error"]
            db.commit()
            return plan
        
        job.plan = plan
        job_queue.update_job_status(job_id, {"status": "processing", "stage": "coding"})
        
        # Step 2: Generate code
        coder = CoderAgent()
        code_result = coder.generate_code(plan)
        
        if "error" in code_result:
            job.status = "failed"
            job.error_message = code_result["error"]
            db.commit()
            return code_result
        
        job.code = code_result["code"]
        job_queue.update_job_status(job_id, {"status": "processing", "stage": "validation"})
        
        # Step 3: Validate and execute
        validator = ValidatorAgent()
        validation_result = validator.validate_and_execute(code_result, {})
        
        if validation_result["success"]:
            job.status = "completed"
            job.result = validation_result["result"]
            job.is_completed = True
            job_queue.update_job_status(job_id, {"status": "completed", "result": validation_result["result"]})
        else:
            job.status = "failed"
            job.error_message = validation_result["error"]
            job_queue.update_job_status(job_id, {"status": "failed", "error": validation_result["error"]})
        
        db.commit()
        return validation_result
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
        job_queue.update_job_status(job_id, {"status": "failed", "error": str(e)})
        return {"error": str(e)}
    finally:
        db.close()