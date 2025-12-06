/**
 * Service Import and Structure Test
 * Run this to verify all services can be imported and have correct structure
 * Usage: node test-services.js (or import in a component temporarily)
 */

// This file tests that all services can be imported without errors
// and have the expected structure

const testServices = () => {
  console.log('🧪 Testing API Services Structure...\n');

  const results = {
    passed: 0,
    failed: 0,
    errors: [],
  };

  const test = (name, testFn) => {
    try {
      testFn();
      results.passed++;
      console.log(`✅ ${name}`);
    } catch (error) {
      results.failed++;
      results.errors.push({ name, error: error.message });
      console.error(`❌ ${name}: ${error.message}`);
    }
  };

  // Test imports
  test('Import apiClient', () => {
    const apiClient = require('./apiClient').default;
    if (!apiClient) throw new Error('apiClient is not exported');
    if (typeof apiClient.get !== 'function') throw new Error('apiClient.get is not a function');
    if (typeof apiClient.post !== 'function') throw new Error('apiClient.post is not a function');
  });

  test('Import endpoints', () => {
    const endpoints = require('./endpoints').default;
    if (!endpoints) throw new Error('endpoints is not exported');
    if (!endpoints.auth) throw new Error('endpoints.auth is missing');
    if (!endpoints.posts) throw new Error('endpoints.posts is missing');
    if (!endpoints.users) throw new Error('endpoints.users is missing');
    if (!endpoints.friends) throw new Error('endpoints.friends is missing');
  });

  test('Import authService', () => {
    const authService = require('./authService').default;
    if (!authService) throw new Error('authService is not exported');
    if (typeof authService.getCurrentUser !== 'function') throw new Error('getCurrentUser is missing');
    if (typeof authService.logout !== 'function') throw new Error('logout is missing');
  });

  test('Import postService', () => {
    const postService = require('./postService').default;
    if (!postService) throw new Error('postService is not exported');
    if (typeof postService.getFeedPosts !== 'function') throw new Error('getFeedPosts is missing');
    if (typeof postService.getUserPosts !== 'function') throw new Error('getUserPosts is missing');
    if (typeof postService.createPost !== 'function') throw new Error('createPost is missing');
  });

  test('Import userService', () => {
    const userService = require('./userService').default;
    if (!userService) throw new Error('userService is not exported');
    if (typeof userService.getUserProfile !== 'function') throw new Error('getUserProfile is missing');
    if (typeof userService.updateProfile !== 'function') throw new Error('updateProfile is missing');
  });

  test('Import friendService', () => {
    const friendService = require('./friendService').default;
    if (!friendService) throw new Error('friendService is not exported');
    if (typeof friendService.getFriends !== 'function') throw new Error('getFriends is missing');
    if (typeof friendService.sendFriendRequest !== 'function') throw new Error('sendFriendRequest is missing');
  });

  test('Import messageService', () => {
    const messageService = require('./messageService').default;
    if (!messageService) throw new Error('messageService is not exported');
    if (typeof messageService.sendMessage !== 'function') throw new Error('sendMessage is missing');
  });

  test('Import matchService', () => {
    const matchService = require('./matchService').default;
    if (!matchService) throw new Error('matchService is not exported');
    if (typeof matchService.getMatches !== 'function') throw new Error('getMatches is missing');
  });

  test('Import centralized index', () => {
    const services = require('./index');
    if (!services.apiClient) throw new Error('apiClient not exported from index');
    if (!services.endpoints) throw new Error('endpoints not exported from index');
    if (!services.authService) throw new Error('authService not exported from index');
    if (!services.postService) throw new Error('postService not exported from index');
  });

  // Summary
  console.log('\n📊 Test Results:');
  console.log(`✅ Passed: ${results.passed}`);
  console.log(`❌ Failed: ${results.failed}`);
  
  if (results.errors.length > 0) {
    console.log('\n❌ Errors:');
    results.errors.forEach(({ name, error }) => {
      console.log(`   - ${name}: ${error}`);
    });
  }

  return results.failed === 0;
};

// Export for use in React components
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { testServices };
}

// Auto-run if executed directly (Node.js)
if (typeof window === 'undefined' && require.main === module) {
  testServices();
}

