"""
Check all signup requests for a specific email
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_database


async def check_all_signups():
    """Check all signup requests"""
    db = get_database()
    
    print("\n" + "=" * 80)
    print("  CHECKING ALL SIGNUP REQUESTS")
    print("=" * 80)
    
    # Check specifically for manju.nitc@gmail.com
    email = "manju.nitc@gmail.com"
    
    print(f"\n🔍 Searching for: {email}\n")
    
    # Get ALL requests for this email (any status)
    all_requests = await db.signup_requests.find({
        "email": email
    }).sort([("requested_at", -1)]).to_list(10)
    
    if not all_requests:
        print(f"❌ No signup requests found for {email}")
        print("\n💡 This means:")
        print("   • The request was never created in the database")
        print("   • There might have been an error during submission")
        print("   • Try submitting the request again")
        return
    
    print(f"✅ Found {len(all_requests)} request(s) for {email}:\n")
    
    for i, req in enumerate(all_requests, 1):
        print(f"Request #{i}:")
        print(f"   Request ID: {req.get('id')}")
        print(f"   Name: {req.get('name')}")
        print(f"   Status: {req.get('status')}")
        print(f"   Requested At: {req.get('requested_at')}")
        print(f"   Reviewed At: {req.get('reviewed_at', 'Not reviewed')}")
        print(f"   Reviewed By: {req.get('reviewed_by', 'N/A')}")
        print(f"   Notes: {req.get('notes', 'None')}")
        
        status = req.get('status')
        
        if status == 'pending':
            print("\n   ⚠️  STATUS: PENDING (waiting for admin approval)")
            print("   📧 User will receive email AFTER admin approves")
            request_id = req.get('id')
            approval_url = f"https://api.2ness.com/api/signup/approve/{request_id}"
            print(f"\n   🔗 APPROVAL URL: {approval_url}")
            print(f"   👉 Click this URL to approve!")
            
        elif status == 'approved':
            print("\n   ✅ STATUS: APPROVED")
            print(f"   📧 Approval email should have been sent")
            print(f"   🌐 User can now log in at https://2ness.com")
            
        elif status == 'rejected':
            print("\n   ❌ STATUS: REJECTED")
            print(f"   📧 Rejection email should have been sent")
        
        print()
    
    # Also check if user account exists
    print("-" * 80)
    user = await db.users.find_one({"email": email})
    
    if user:
        print(f"\n✅ USER ACCOUNT EXISTS for {email}")
        print(f"   User ID: {user.get('id')}")
        print(f"   Name: {user.get('name')}")
        print(f"   Status: User can log in!")
    else:
        print(f"\n❌ No user account exists for {email}")
        print("   User needs to be approved first")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(check_all_signups())
