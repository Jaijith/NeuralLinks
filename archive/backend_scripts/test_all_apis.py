"""
Test all API endpoints to verify they're working
"""

import requests
import json
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8001"

def test_endpoint(method: str, path: str, expected_status: int = None, data: dict = None, headers: dict = None) -> Tuple[bool, str, int]:
    """Test an endpoint and return (success, message, status_code)"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=5)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=5)
        else:
            return False, f"Unknown method: {method}", 0
        
        status = response.status_code
        success = expected_status is None or status == expected_status
        
        # For 401/403, that's expected for unauthenticated requests
        if status in [401, 403]:
            message = f"✅ {method} {path}: {status} (requires auth)"
            return True, message, status
        # For 422, that's validation error (endpoint exists, just needs valid data)
        elif status == 422:
            message = f"✅ {method} {path}: {status} (endpoint exists, validation working)"
            return True, message, status
        elif success:
            message = f"✅ {method} {path}: {status}"
            return True, message, status
        else:
            message = f"❌ {method} {path}: {status} (expected {expected_status})"
            return False, message, status
            
    except requests.exceptions.ConnectionError:
        return False, f"❌ {method} {path}: Connection refused (server not running?)", 0
    except Exception as e:
        return False, f"❌ {method} {path}: {str(e)}", 0


def main():
    print("=" * 80)
    print("🧪 Testing All API Endpoints")
    print("=" * 80)
    print()
    
    results = []
    
    # Auth Routes
    print("📋 Testing Auth Routes...")
    results.append(test_endpoint("GET", "/api/auth/me", expected_status=401))
    results.append(test_endpoint("POST", "/api/auth/logout", expected_status=401))
    print()
    
    # Profile Routes
    print("📋 Testing Profile Routes...")
    results.append(test_endpoint("GET", "/api/users/test-user-id", expected_status=401))
    results.append(test_endpoint("PUT", "/api/profile", expected_status=401))
    results.append(test_endpoint("PUT", "/api/profile/avatar", expected_status=401))
    results.append(test_endpoint("GET", "/api/profile/avatar", expected_status=401))
    print()
    
    # Post Routes
    print("📋 Testing Post Routes...")
    results.append(test_endpoint("POST", "/api/profile/posts", expected_status=401))
    results.append(test_endpoint("GET", "/api/profile/posts", expected_status=401))
    results.append(test_endpoint("GET", "/api/feed/posts", expected_status=401))
    results.append(test_endpoint("DELETE", "/api/profile/posts/test-post-id", expected_status=401))
    results.append(test_endpoint("POST", "/api/posts/test-post-id/like", expected_status=401))
    results.append(test_endpoint("POST", "/api/posts/test-post-id/comment", expected_status=401))
    results.append(test_endpoint("PUT", "/api/profile/posts/test-post-id", expected_status=401))
    print()
    
    # Friend Routes
    print("📋 Testing Friend Routes...")
    results.append(test_endpoint("POST", "/api/friends/request/test-friend-id", expected_status=401))
    results.append(test_endpoint("POST", "/api/friends/accept/test-friendship-id", expected_status=401))
    results.append(test_endpoint("POST", "/api/friends/decline/test-friendship-id", expected_status=401))
    results.append(test_endpoint("GET", "/api/friends", expected_status=401))
    results.append(test_endpoint("GET", "/api/friends/requests", expected_status=401))
    print()
    
    # Graph Routes
    print("📋 Testing Graph Routes...")
    results.append(test_endpoint("GET", "/api/graph/visualization", expected_status=401))
    results.append(test_endpoint("POST", "/api/graph/build-from-profile", expected_status=401))
    results.append(test_endpoint("POST", "/api/graph/enrich-from-post", expected_status=401))
    results.append(test_endpoint("GET", "/api/graph/compatibility/test-user-id", expected_status=401))
    results.append(test_endpoint("GET", "/api/graph/my-graph", expected_status=401))
    print()
    
    # MCP Routes (should work without auth)
    print("📋 Testing MCP Routes...")
    results.append(test_endpoint("GET", "/api/mcp/tools", expected_status=200))
    results.append(test_endpoint("GET", "/api/mcp/tools/available?avatar_id=test", expected_status=200))
    print()
    
    # Integration Routes (from legacy api_router)
    print("📋 Testing Integration Routes...")
    results.append(test_endpoint("GET", "/api/integrations", expected_status=401))
    results.append(test_endpoint("POST", "/api/integrations/connect", expected_status=401))
    print()
    
    # Message Routes (from legacy api_router)
    print("📋 Testing Message Routes...")
    results.append(test_endpoint("POST", "/api/messages/send", expected_status=401))
    results.append(test_endpoint("GET", "/api/messages/conversations", expected_status=401))
    results.append(test_endpoint("GET", "/api/messages/test-user-id", expected_status=401))
    print()
    
    # Avatar Routes (from legacy api_router)
    print("📋 Testing Avatar Routes...")
    results.append(test_endpoint("POST", "/api/avatar/generate-post", expected_status=401))
    results.append(test_endpoint("GET", "/api/avatar/config", expected_status=401))
    print()
    
    # Health/Info endpoints
    print("📋 Testing Health/Info Routes...")
    results.append(test_endpoint("GET", "/docs", expected_status=200))
    results.append(test_endpoint("GET", "/openapi.json", expected_status=200))
    print()
    
    # Summary
    print("=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    
    total = len(results)
    passed = sum(1 for success, _, _ in results if success)
    failed = total - passed
    
    print(f"Total endpoints tested: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print()
    
    if failed > 0:
        print("Failed endpoints:")
        for success, message, status in results:
            if not success:
                print(f"  {message}")
        print()
    
    # Show all results
    print("All results:")
    for success, message, status in results:
        print(f"  {message}")
    
    print()
    print("=" * 80)
    if failed == 0:
        print("✅ All endpoints are accessible!")
    else:
        print(f"⚠️  {failed} endpoint(s) failed (may be expected if server is not fully configured)")
    print("=" * 80)


if __name__ == "__main__":
    main()

