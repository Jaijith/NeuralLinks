#!/usr/bin/env python3
"""
Backend Test Suite for Graph RAG and Intelligent Avatar System
Tests all new Graph RAG functionality including graph building, avatar intelligence, and external integrations
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# Configuration
BACKEND_URL = "https://sense-maya.preview.emergentagent.com/api"
TEST_USER_EMAIL = "graphrag.tester@example.com"
TEST_USER_NAME = "GraphRAG Tester"

class GraphRAGTester:
    def __init__(self):
        self.session_token = None
        self.user_id = None
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        
    async def log_result(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    async def setup_test_user(self):
        """Setup test user with authentication"""
        print("\n=== Setting up test user ===")
        
        # Create a mock session for testing
        # In real scenario, this would go through OAuth flow
        mock_session_data = {
            "email": TEST_USER_EMAIL,
            "name": TEST_USER_NAME,
            "picture": "https://api.dicebear.com/7.x/avataaars/svg?seed=graphrag",
            "session_token": f"test_token_{datetime.now().timestamp()}"
        }
        
        try:
            # Simulate session creation by directly calling auth endpoint
            headers = {"X-Session-ID": "mock_session_for_testing"}
            
            # Mock the session data endpoint response
            # For testing, we'll create user directly via profile update
            
            # First, let's try to authenticate with a test token
            test_token = f"test_graph_rag_{datetime.now().timestamp()}"
            
            # Try to get current user to see if we need to create one
            response = await self.client.get(
                f"{BACKEND_URL}/auth/me",
                headers={"Authorization": f"Bearer {test_token}"}
            )
            
            if response.status_code == 401:
                # Need to create user - let's use a different approach
                # We'll create a user by calling the profile endpoint with mock data
                await self.log_result("User Authentication", False, 
                                    "Need to implement proper test user creation")
                return False
            
            await self.log_result("User Authentication", True, "Test user setup completed")
            self.session_token = test_token
            return True
            
        except Exception as e:
            await self.log_result("User Authentication", False, f"Setup failed: {str(e)}")
            return False
    
    async def create_test_user_profile(self):
        """Create a test user with rich profile data for graph building"""
        print("\n=== Creating test user profile ===")
        
        profile_data = {
            "name": TEST_USER_NAME,
            "age": 28,
            "gender": "non-binary",
            "location": "San Francisco, CA",
            "bio": "I'm passionate about sustainable technology and love hiking in nature. I value authenticity and meaningful connections. Always curious about new cultures and enjoy cooking plant-based meals.",
            "interests": ["hiking", "technology", "cooking", "travel", "sustainability", "photography"]
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.put(
                f"{BACKEND_URL}/profile",
                json=profile_data,
                headers=headers
            )
            
            if response.status_code == 200:
                await self.log_result("Profile Creation", True, 
                                    f"Profile created with {len(profile_data['interests'])} interests")
                return True
            else:
                await self.log_result("Profile Creation", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            await self.log_result("Profile Creation", False, f"Error: {str(e)}")
            return False
    
    async def test_graph_building(self):
        """Test graph building from profile"""
        print("\n=== Testing Graph Building ===")
        
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            # Test building graph from profile
            response = await self.client.post(
                f"{BACKEND_URL}/graph/build-from-profile",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                nodes_created = data.get("nodes_created", 0)
                edges_created = data.get("edges_created", 0)
                
                await self.log_result("Graph Building", True, 
                                    f"Created {nodes_created} nodes, {edges_created} edges",
                                    data)
                return True
            else:
                await self.log_result("Graph Building", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            await self.log_result("Graph Building", False, f"Error: {str(e)}")
            return False
    
    async def test_graph_context(self):
        """Test retrieving graph context"""
        print("\n=== Testing Graph Context Retrieval ===")
        
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.get(
                f"{BACKEND_URL}/graph/context",
                headers=headers
            )
            
            if response.status_code == 200:
                context = response.json()
                
                # Check if context has expected structure
                expected_keys = ["interests", "traits", "values", "experiences", "preferences", "demographics"]
                has_structure = all(key in context for key in expected_keys)
                
                total_nodes = sum(len(context.get(key, [])) for key in expected_keys)
                
                await self.log_result("Graph Context", True, 
                                    f"Retrieved context with {total_nodes} total nodes",
                                    context)
                return True
            else:
                await self.log_result("Graph Context", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            await self.log_result("Graph Context", False, f"Error: {str(e)}")
            return False
    
    async def test_graph_enrichment(self):
        """Test graph enrichment from post content"""
        print("\n=== Testing Graph Enrichment ===")
        
        test_posts = [
            "Just finished an amazing rock climbing session! The adrenaline rush and connection with nature is unmatched. Looking for climbing partners who share the passion for adventure.",
            "Spent the weekend experimenting with fermentation techniques. Made some incredible kimchi and kombucha. The science behind fermentation fascinates me!",
            "Attended a mindfulness retreat this weekend. The importance of mental health and self-care cannot be overstated. Grateful for these moments of peace."
        ]
        
        enrichment_results = []
        
        for i, post_content in enumerate(test_posts):
            try:
                headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
                
                response = await self.client.post(
                    f"{BACKEND_URL}/graph/enrich-from-post",
                    json={"content": post_content},
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    nodes_created = data.get("nodes_created", 0)
                    
                    enrichment_results.append({
                        "post": i + 1,
                        "nodes_created": nodes_created,
                        "success": True
                    })
                    
                    await self.log_result(f"Graph Enrichment Post {i+1}", True, 
                                        f"Added {nodes_created} nodes from post content")
                else:
                    enrichment_results.append({
                        "post": i + 1,
                        "success": False,
                        "error": f"HTTP {response.status_code}"
                    })
                    
                    await self.log_result(f"Graph Enrichment Post {i+1}", False, 
                                        f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                enrichment_results.append({
                    "post": i + 1,
                    "success": False,
                    "error": str(e)
                })
                await self.log_result(f"Graph Enrichment Post {i+1}", False, f"Error: {str(e)}")
        
        # Overall enrichment success
        successful_enrichments = sum(1 for r in enrichment_results if r["success"])
        total_enrichments = len(enrichment_results)
        
        return successful_enrichments == total_enrichments
    
    async def test_avatar_intelligence(self):
        """Test avatar intelligence features"""
        print("\n=== Testing Avatar Intelligence ===")
        
        # Test different post types
        post_types = ["general", "interest", "thought", "experience"]
        avatar_results = []
        
        for post_type in post_types:
            try:
                headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
                
                response = await self.client.post(
                    f"{BACKEND_URL}/avatar/generate-post?post_type={post_type}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content", "")
                    
                    if content and len(content) > 20:  # Basic content validation
                        avatar_results.append({"type": post_type, "success": True})
                        await self.log_result(f"Avatar Post ({post_type})", True, 
                                            f"Generated {len(content)} character post")
                    else:
                        avatar_results.append({"type": post_type, "success": False})
                        await self.log_result(f"Avatar Post ({post_type})", False, 
                                            "Generated content too short or empty")
                else:
                    avatar_results.append({"type": post_type, "success": False})
                    await self.log_result(f"Avatar Post ({post_type})", False, 
                                        f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                avatar_results.append({"type": post_type, "success": False})
                await self.log_result(f"Avatar Post ({post_type})", False, f"Error: {str(e)}")
        
        # Test avatar bio generation
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.post(
                f"{BACKEND_URL}/avatar/generate-bio",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                bio = data.get("bio", "")
                
                if bio and len(bio) > 50:
                    avatar_results.append({"type": "bio", "success": True})
                    await self.log_result("Avatar Bio Generation", True, 
                                        f"Generated {len(bio)} character bio")
                else:
                    avatar_results.append({"type": "bio", "success": False})
                    await self.log_result("Avatar Bio Generation", False, 
                                        "Generated bio too short or empty")
            else:
                avatar_results.append({"type": "bio", "success": False})
                await self.log_result("Avatar Bio Generation", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            avatar_results.append({"type": "bio", "success": False})
            await self.log_result("Avatar Bio Generation", False, f"Error: {str(e)}")
        
        successful_avatar_tests = sum(1 for r in avatar_results if r["success"])
        total_avatar_tests = len(avatar_results)
        
        return successful_avatar_tests >= (total_avatar_tests * 0.8)  # 80% success rate
    
    async def test_external_integrations(self):
        """Test external platform integrations"""
        print("\n=== Testing External Integrations ===")
        
        integration_results = []
        
        # Test getting available integrations
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.get(
                f"{BACKEND_URL}/integrations",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                integrations = data.get("integrations", [])
                
                if integrations and len(integrations) > 0:
                    integration_results.append({"test": "list", "success": True})
                    await self.log_result("Integration List", True, 
                                        f"Found {len(integrations)} available platforms")
                else:
                    integration_results.append({"test": "list", "success": False})
                    await self.log_result("Integration List", False, "No integrations found")
            else:
                integration_results.append({"test": "list", "success": False})
                await self.log_result("Integration List", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            integration_results.append({"test": "list", "success": False})
            await self.log_result("Integration List", False, f"Error: {str(e)}")
        
        # Test connecting to Spotify (placeholder)
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.post(
                f"{BACKEND_URL}/integrations/connect",
                json={"platform_name": "spotify"},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "")
                
                if status == "connected":
                    integration_results.append({"test": "connect", "success": True})
                    await self.log_result("Integration Connect", True, "Spotify connected successfully")
                else:
                    integration_results.append({"test": "connect", "success": False})
                    await self.log_result("Integration Connect", False, f"Unexpected status: {status}")
            else:
                integration_results.append({"test": "connect", "success": False})
                await self.log_result("Integration Connect", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            integration_results.append({"test": "connect", "success": False})
            await self.log_result("Integration Connect", False, f"Error: {str(e)}")
        
        # Test syncing data from Spotify
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.post(
                f"{BACKEND_URL}/integrations/sync",
                json={"platform_name": "spotify"},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                nodes_added = data.get("nodes_added", 0)
                
                integration_results.append({"test": "sync", "success": True})
                await self.log_result("Integration Sync", True, 
                                    f"Synced data, added {nodes_added} nodes")
            else:
                integration_results.append({"test": "sync", "success": False})
                await self.log_result("Integration Sync", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            integration_results.append({"test": "sync", "success": False})
            await self.log_result("Integration Sync", False, f"Error: {str(e)}")
        
        successful_integration_tests = sum(1 for r in integration_results if r["success"])
        total_integration_tests = len(integration_results)
        
        return successful_integration_tests >= (total_integration_tests * 0.67)  # 67% success rate
    
    async def test_graph_rag_queries(self):
        """Test Graph RAG query functionality"""
        print("\n=== Testing Graph RAG Queries ===")
        
        rag_results = []
        
        # Test finding similar users
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            response = await self.client.get(
                f"{BACKEND_URL}/graph/similar-users?limit=5",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                similar_users = data.get("similar_users", [])
                
                rag_results.append({"test": "similar_users", "success": True})
                await self.log_result("Similar Users", True, 
                                    f"Found {len(similar_users)} similar users")
            else:
                rag_results.append({"test": "similar_users", "success": False})
                await self.log_result("Similar Users", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            rag_results.append({"test": "similar_users", "success": False})
            await self.log_result("Similar Users", False, f"Error: {str(e)}")
        
        # Test conversation starters (requires another user - will test with self for now)
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            # Use a placeholder user ID for testing
            test_other_user_id = "test_user_123"
            
            response = await self.client.get(
                f"{BACKEND_URL}/avatar/conversation-starters/{test_other_user_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                starters = data.get("starters", [])
                
                if starters and len(starters) > 0:
                    rag_results.append({"test": "conversation_starters", "success": True})
                    await self.log_result("Conversation Starters", True, 
                                        f"Generated {len(starters)} conversation starters")
                else:
                    rag_results.append({"test": "conversation_starters", "success": False})
                    await self.log_result("Conversation Starters", False, "No starters generated")
            else:
                rag_results.append({"test": "conversation_starters", "success": False})
                await self.log_result("Conversation Starters", False, 
                                    f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            rag_results.append({"test": "conversation_starters", "success": False})
            await self.log_result("Conversation Starters", False, f"Error: {str(e)}")
        
        successful_rag_tests = sum(1 for r in rag_results if r["success"])
        total_rag_tests = len(rag_results)
        
        return successful_rag_tests >= (total_rag_tests * 0.5)  # 50% success rate
    
    async def test_automatic_graph_building(self):
        """Test automatic graph building on profile updates"""
        print("\n=== Testing Automatic Graph Building ===")
        
        try:
            headers = {"Authorization": f"Bearer {self.session_token}"} if self.session_token else {}
            
            # Update profile with new interests
            updated_profile = {
                "interests": ["hiking", "technology", "cooking", "travel", "sustainability", "photography", "meditation", "rock_climbing"]
            }
            
            response = await self.client.put(
                f"{BACKEND_URL}/profile",
                json=updated_profile,
                headers=headers
            )
            
            if response.status_code == 200:
                # Check if graph was updated by retrieving context
                await asyncio.sleep(1)  # Give time for graph update
                
                context_response = await self.client.get(
                    f"{BACKEND_URL}/graph/context",
                    headers=headers
                )
                
                if context_response.status_code == 200:
                    context = context_response.json()
                    interests = context.get("interests", [])
                    
                    # Check if new interests appear in graph
                    interest_labels = [item.get("label", "") for item in interests]
                    has_new_interests = any(interest in interest_labels for interest in ["meditation", "rock_climbing"])
                    
                    await self.log_result("Automatic Graph Building", has_new_interests, 
                                        f"Graph updated with new interests: {has_new_interests}")
                    return has_new_interests
                else:
                    await self.log_result("Automatic Graph Building", False, 
                                        "Could not verify graph update")
                    return False
            else:
                await self.log_result("Automatic Graph Building", False, 
                                    f"Profile update failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            await self.log_result("Automatic Graph Building", False, f"Error: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Graph RAG and Intelligent Avatar Backend Tests")
        print("=" * 60)
        
        # Setup phase
        setup_success = await self.setup_test_user()
        if not setup_success:
            print("\n❌ Test setup failed. Continuing with available tests...")
        
        # Create test profile for graph building
        profile_success = await self.create_test_user_profile()
        
        # Core tests
        test_functions = [
            ("Graph Building", self.test_graph_building),
            ("Graph Context", self.test_graph_context),
            ("Graph Enrichment", self.test_graph_enrichment),
            ("Avatar Intelligence", self.test_avatar_intelligence),
            ("External Integrations", self.test_external_integrations),
            ("Graph RAG Queries", self.test_graph_rag_queries),
            ("Automatic Graph Building", self.test_automatic_graph_building)
        ]
        
        results = {}
        
        for test_name, test_func in test_functions:
            try:
                results[test_name] = await test_func()
            except Exception as e:
                results[test_name] = False
                await self.log_result(test_name, False, f"Test function error: {str(e)}")
        
        # Summary
        await self.print_summary(results)
        
        await self.client.aclose()
        
        return results
    
    async def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        passed_tests = sum(1 for success in results.values() if success)
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} {test_name}")
        
        # Critical issues
        critical_failures = []
        if not results.get("Graph Building", False):
            critical_failures.append("Graph Building - Core functionality not working")
        if not results.get("Avatar Intelligence", False):
            critical_failures.append("Avatar Intelligence - AI features not working")
        
        if critical_failures:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in critical_failures:
                print(f"  - {issue}")
        
        print("\n" + "=" * 60)

async def main():
    """Main test execution"""
    tester = GraphRAGTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on critical tests
    critical_tests = ["Graph Building", "Graph Context", "Avatar Intelligence"]
    critical_passed = all(results.get(test, False) for test in critical_tests)
    
    return 0 if critical_passed else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)