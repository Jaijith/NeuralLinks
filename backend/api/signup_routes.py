"""
Signup and approval routes
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging
from core.database import get_database
from services.email_service import EmailService

db = get_database()
router = APIRouter(prefix="/api/signup", tags=["signup"])
logger = logging.getLogger(__name__)
email_service = EmailService()


class SignupRequestModel(BaseModel):
    email: EmailStr
    name: str
    picture: Optional[str] = None


@router.post("/request")
async def create_signup_request(request_data: SignupRequestModel):
    """Create a new signup request (pending approval)"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": request_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email already exists")
        
        # Check if there's already a pending request
        existing_request = await db.signup_requests.find_one({
            "email": request_data.email,
            "status": "pending"
        })
        if existing_request:
            raise HTTPException(
                status_code=400, 
                detail="A signup request for this email is already pending approval"
            )
        
        # Create signup request
        request_id = str(uuid.uuid4())
        signup_request = {
            "id": request_id,
            "email": request_data.email,
            "name": request_data.name,
            "picture": request_data.picture,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_at": None,
            "reviewed_by": None,
            "notes": None
        }
        
        await db.signup_requests.insert_one(signup_request)
        
        # Send approval request email to admin
        # Generate approval URL (in production, this would be a proper admin panel URL)
        base_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        approval_url = f"{base_url}/admin/approve/{request_id}"
        
        email_service.send_approval_request(
            email=request_data.email,
            name=request_data.name,
            request_id=request_id,
            approval_url=approval_url
        )
        
        logger.info(f"Signup request created: {request_data.email}")
        
        return {
            "message": "Signup request submitted successfully. You will receive an email once your request is approved.",
            "request_id": request_id,
            "status": "pending"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating signup request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{email}")
async def check_signup_status(email: str):
    """Check the status of a signup request"""
    try:
        request = await db.signup_requests.find_one(
            {"email": email},
            sort=[("requested_at", -1)]  # Get most recent request
        )
        
        if not request:
            return {
                "status": "not_found",
                "message": "No signup request found for this email"
            }
        
        return {
            "status": request.get("status", "pending"),
            "requested_at": request.get("requested_at"),
            "reviewed_at": request.get("reviewed_at"),
            "message": {
                "pending": "Your request is pending approval. You will receive an email once it's reviewed.",
                "approved": "Your request has been approved! You can now log in with your Google account.",
                "rejected": "Your request was not approved. Please contact support for more information."
            }.get(request.get("status", "pending"), "Unknown status")
        }
    except Exception as e:
        logger.error(f"Error checking signup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/requests")
async def list_signup_requests(request: Request, status: Optional[str] = None):
    """List all signup requests (admin only)"""
    # TODO: Add admin authentication check
    try:
        query = {}
        if status:
            query["status"] = status
        
        requests = await db.signup_requests.find(query).sort([("requested_at", -1)]).to_list(100)
        
        # Remove MongoDB _id field
        for req in requests:
            req.pop("_id", None)
        
        return {
            "requests": requests,
            "total": len(requests)
        }
    except Exception as e:
        logger.error(f"Error listing signup requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve/{request_id}")
async def approve_signup_request(request_id: str, request: Request):
    """Approve a signup request (admin only)"""
    # TODO: Add admin authentication check
    try:
        signup_request = await db.signup_requests.find_one({"id": request_id})
        
        if not signup_request:
            raise HTTPException(status_code=404, detail="Signup request not found")
        
        if signup_request.get("status") != "pending":
            raise HTTPException(
                status_code=400, 
                detail=f"Request is already {signup_request.get('status')}"
            )
        
        # Update request status
        await db.signup_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "status": "approved",
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": "admin"  # TODO: Get from authenticated admin user
                }
            }
        )
        
        # Send approval notification email
        email_service.send_approval_notification(
            email=signup_request["email"],
            name=signup_request["name"],
            approved=True
        )
        
        logger.info(f"Signup request approved: {request_id} for {signup_request['email']}")
        
        return {
            "message": "Signup request approved successfully",
            "request_id": request_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving signup request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reject/{request_id}")
async def reject_signup_request(request_id: str, request: Request, notes: Optional[str] = None):
    """Reject a signup request (admin only)"""
    # TODO: Add admin authentication check
    try:
        signup_request = await db.signup_requests.find_one({"id": request_id})
        
        if not signup_request:
            raise HTTPException(status_code=404, detail="Signup request not found")
        
        if signup_request.get("status") != "pending":
            raise HTTPException(
                status_code=400, 
                detail=f"Request is already {signup_request.get('status')}"
            )
        
        # Update request status
        await db.signup_requests.update_one(
            {"id": request_id},
            {
                "$set": {
                    "status": "rejected",
                    "reviewed_at": datetime.now(timezone.utc).isoformat(),
                    "reviewed_by": "admin",  # TODO: Get from authenticated admin user
                    "notes": notes
                }
            }
        )
        
        # Send rejection notification email
        email_service.send_approval_notification(
            email=signup_request["email"],
            name=signup_request["name"],
            approved=False
        )
        
        logger.info(f"Signup request rejected: {request_id} for {signup_request['email']}")
        
        return {
            "message": "Signup request rejected",
            "request_id": request_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting signup request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

