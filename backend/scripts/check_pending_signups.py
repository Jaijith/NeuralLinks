"""
Check for pending signup requests that might not have received emails
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_database


async def check_pending_signups():
    """Check for pending signup requests"""
    db = get_database()
    
    print("\n" + "=" * 80)
    print("  CHECKING PENDING SIGNUP REQUESTS")
    print("=" * 80)
    
    # Get all pending requests
    pending_requests = await db.signup_requests.find({
        "status": "pending"
    }).sort([("requested_at", -1)]).to_list(100)
    
    print(f"\n📊 Total Pending Requests: {len(pending_requests)}")
    
    if not pending_requests:
        print("   ✅ No pending requests found!")
        return
    
    print("\n" + "-" * 80)
    print("Pending Requests:\n")
    
    for i, req in enumerate(pending_requests, 1):
        email = req.get("email", "N/A")
        name = req.get("name", "N/A")
        requested_at = req.get("requested_at", "N/A")
        request_id = req.get("id", "N/A")
        
        print(f"{i}. Email: {email}")
        print(f"   Name: {name}")
        print(f"   Request ID: {request_id}")
        print(f"   Requested At: {requested_at}")
        print(f"   Status: {req.get('status', 'N/A')}")
        print()
    
    # Check specifically for manju.nitc@gmail.com
    print("-" * 80)
    manju_request = await db.signup_requests.find_one({
        "email": "manju.nitc@gmail.com"
    })
    
    if manju_request:
        print("\n🔍 Found request for manju.nitc@gmail.com:")
        print(f"   Request ID: {manju_request.get('id')}")
        print(f"   Name: {manju_request.get('name')}")
        print(f"   Status: {manju_request.get('status')}")
        print(f"   Requested At: {manju_request.get('requested_at')}")
        print(f"   Reviewed At: {manju_request.get('reviewed_at', 'Not reviewed')}")
        
        if manju_request.get('status') == 'pending':
            print("\n   ⚠️  This request is PENDING but user didn't receive email!")
            print("   📧 Admin approval email should have been sent to admin")
            print("   📧 User will get email AFTER approval")
            
            # Generate approval URL
            request_id = manju_request.get('id')
            approval_url = f"https://api.2ness.com/api/signup/approve/{request_id}"
            print(f"\n   🔗 Approval URL: {approval_url}")
            print(f"   👉 Click this URL to approve the request!")
    else:
        print("\n❌ No request found for manju.nitc@gmail.com")
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  • Total Pending: {len(pending_requests)}")
    print(f"  • Action: Review and approve pending requests")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(check_pending_signups())
