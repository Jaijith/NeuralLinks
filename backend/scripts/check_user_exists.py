"""
Check if a user account exists for the given email
"""

import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_database


async def check_user():
    """Check if user exists"""
    db = get_database()
    
    email = "manju.nitc@gmail.com"
    
    print("\n" + "=" * 80)
    print(f"  CHECKING USER ACCOUNT FOR: {email}")
    print("=" * 80 + "\n")
    
    # Check users collection
    user = await db.users.find_one({"email": email})
    
    if user:
        print(f"✅ USER ACCOUNT EXISTS!\n")
        print(f"   User ID: {user.get('id')}")
        print(f"   Name: {user.get('name')}")
        print(f"   Email: {user.get('email')}")
        print(f"   Created: {user.get('created_at', 'N/A')}")
        print(f"   Avatar Name: {user.get('avatar_name', 'Not set')}")
        print(f"\n   💡 This user can already log in!")
        print(f"   🌐 Go to: https://2ness.com")
        
        # Check if there's also a signup request (shouldn't be)
        signup_req = await db.signup_requests.find_one({"email": email})
        if signup_req:
            print(f"\n   ⚠️  Found signup request (this shouldn't exist for existing users)")
            print(f"      Request Status: {signup_req.get('status')}")
    else:
        print(f"❌ No user account found for {email}\n")
        
        # Check signup requests
        signup_req = await db.signup_requests.find_one({"email": email})
        if signup_req:
            print(f"✅ But found signup request:")
            print(f"   Status: {signup_req.get('status')}")
            print(f"   Request ID: {signup_req.get('id')}")
        else:
            print(f"❌ No signup request found either")
            print(f"\n💡 Possible reasons for 'already pending' error:")
            print(f"   1. Frontend caching (try hard refresh: Cmd/Ctrl + Shift + R)")
            print(f"   2. Browser localStorage issue (clear site data)")
            print(f"   3. Request failed to reach backend")
            print(f"   4. Different email was used")
    
    print("\n" + "=" * 80)
    
    # Also check all users with similar email pattern
    print("\n🔍 Searching for similar emails (manju*)...\n")
    similar_users = await db.users.find({
        "email": {"$regex": "^manju", "$options": "i"}
    }).to_list(10)
    
    if similar_users:
        print(f"Found {len(similar_users)} user(s) with similar emails:")
        for u in similar_users:
            print(f"   • {u.get('email')} - {u.get('name')}")
    else:
        print("No similar emails found")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(check_user())
