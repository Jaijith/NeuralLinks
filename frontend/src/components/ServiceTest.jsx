/**
 * Service Test Component
 * Use this component temporarily to test all services are working
 * Add <ServiceTest /> to App.js temporarily to run tests
 */

import { useEffect, useState } from 'react';
import { 
  authService, 
  postService, 
  userService, 
  friendService, 
  messageService, 
  matchService,
  endpoints 
} from '@/services/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const ServiceTest = () => {
  const [results, setResults] = useState({
    structure: { passed: 0, failed: 0, errors: [] },
    imports: { passed: 0, failed: 0, errors: [] },
  });

  useEffect(() => {
    testServices();
  }, []);

  const testServices = () => {
    const structureResults = { passed: 0, failed: 0, errors: [] };
    const importResults = { passed: 0, failed: 0, errors: [] };

    // Test 1: Structure Tests
    const testStructure = (name, service, methods) => {
      try {
        if (!service) throw new Error('Service is not defined');
        methods.forEach(method => {
          if (typeof service[method] !== 'function') {
            throw new Error(`Method ${method} is missing or not a function`);
          }
        });
        structureResults.passed++;
        return true;
      } catch (error) {
        structureResults.failed++;
        structureResults.errors.push({ name, error: error.message });
        return false;
      }
    };

    // Test all services structure
    testStructure('authService', authService, ['getCurrentUser', 'logout', 'deleteAccount']);
    testStructure('postService', postService, [
      'getFeedPosts', 'getUserPosts', 'createPost', 'createPostWithImage',
      'deletePost', 'likePost', 'getPostLikes', 'getPostComments', 'addComment'
    ]);
    testStructure('userService', userService, [
      'getUserProfile', 'updateProfile', 'updateAvatarProfile',
      'getAvatarProfile', 'uploadProfilePicture', 'uploadCoverPhoto'
    ]);
    testStructure('friendService', friendService, [
      'getFriends', 'getFriendRequests', 'sendFriendRequest',
      'acceptFriendRequest', 'declineFriendRequest', 'removeFriend', 'getSuggestions'
    ]);
    testStructure('messageService', messageService, [
      'sendMessage', 'getAvatarConversations', 'getConversation'
    ]);
    testStructure('matchService', matchService, [
      'getMatches', 'discoverMatches', 'getMatchConversation'
    ]);

    // Test 2: Endpoints structure
    try {
      if (!endpoints.auth) throw new Error('endpoints.auth is missing');
      if (!endpoints.posts) throw new Error('endpoints.posts is missing');
      if (!endpoints.users) throw new Error('endpoints.users is missing');
      if (!endpoints.friends) throw new Error('endpoints.friends is missing');
      if (!endpoints.messages) throw new Error('endpoints.messages is missing');
      if (!endpoints.matches) throw new Error('endpoints.matches is missing');
      importResults.passed++;
    } catch (error) {
      importResults.failed++;
      importResults.errors.push({ name: 'endpoints', error: error.message });
    }

    // Test 3: Endpoint functions
    try {
      if (typeof endpoints.posts.delete !== 'function') throw new Error('endpoints.posts.delete is not a function');
      if (typeof endpoints.friends.sendRequest !== 'function') throw new Error('endpoints.friends.sendRequest is not a function');
      if (typeof endpoints.users.profile !== 'function') throw new Error('endpoints.users.profile is not a function');
      importResults.passed++;
    } catch (error) {
      importResults.failed++;
      importResults.errors.push({ name: 'endpointFunctions', error: error.message });
    }

    setResults({
      structure: structureResults,
      imports: importResults,
    });
  };

  const totalPassed = results.structure.passed + results.imports.passed;
  const totalFailed = results.structure.failed + results.imports.failed;

  return (
    <Card className="p-6 m-4 max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">🧪 Service Structure Tests</h2>
      
      <div className="space-y-4">
        <div>
          <h3 className="font-semibold mb-2">Structure Tests</h3>
          <p className="text-sm text-gray-600">
            ✅ Passed: {results.structure.passed} | ❌ Failed: {results.structure.failed}
          </p>
          {results.structure.errors.length > 0 && (
            <ul className="list-disc list-inside text-sm text-red-600 mt-2">
              {results.structure.errors.map((err, idx) => (
                <li key={idx}>{err.name}: {err.error}</li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="font-semibold mb-2">Import Tests</h3>
          <p className="text-sm text-gray-600">
            ✅ Passed: {results.imports.passed} | ❌ Failed: {results.imports.failed}
          </p>
          {results.imports.errors.length > 0 && (
            <ul className="list-disc list-inside text-sm text-red-600 mt-2">
              {results.imports.errors.map((err, idx) => (
                <li key={idx}>{err.name}: {err.error}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="pt-4 border-t">
          <h3 className="font-semibold mb-2">Summary</h3>
          <p className={`text-lg font-bold ${totalFailed === 0 ? 'text-green-600' : 'text-red-600'}`}>
            {totalFailed === 0 ? '✅ All tests passed!' : `❌ ${totalFailed} test(s) failed`}
          </p>
          <p className="text-sm text-gray-600">
            Total: {totalPassed} passed, {totalFailed} failed
          </p>
        </div>

        <Button onClick={testServices} className="mt-4">
          Re-run Tests
        </Button>
      </div>
    </Card>
  );
};

export default ServiceTest;

