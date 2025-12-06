/**
 * Service structure validation tests
 * Tests that all services are properly exported and have correct method signatures
 */

// Mock axios for testing
jest.mock('../../apiClient', () => ({
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
}));

describe('API Services Structure Tests', () => {
  let authService, postService, userService, friendService, messageService, matchService;
  let endpoints, apiClient;

  beforeAll(() => {
    // Import services
    authService = require('../authService').default;
    postService = require('../postService').default;
    userService = require('../userService').default;
    friendService = require('../friendService').default;
    messageService = require('../messageService').default;
    matchService = require('../matchService').default;
    endpoints = require('../endpoints').default;
    apiClient = require('../apiClient').default;
  });

  describe('Endpoints', () => {
    test('should export all endpoint categories', () => {
      expect(endpoints).toHaveProperty('auth');
      expect(endpoints).toHaveProperty('users');
      expect(endpoints).toHaveProperty('posts');
      expect(endpoints).toHaveProperty('friends');
      expect(endpoints).toHaveProperty('messages');
      expect(endpoints).toHaveProperty('matches');
    });

    test('should have all auth endpoints', () => {
      expect(endpoints.auth).toHaveProperty('login');
      expect(endpoints.auth).toHaveProperty('callback');
      expect(endpoints.auth).toHaveProperty('me');
      expect(endpoints.auth).toHaveProperty('logout');
      expect(endpoints.auth).toHaveProperty('account');
    });

    test('should have all post endpoints', () => {
      expect(endpoints.posts).toHaveProperty('create');
      expect(endpoints.posts).toHaveProperty('getUserPosts');
      expect(endpoints.posts).toHaveProperty('getFeedPosts');
      expect(endpoints.posts).toHaveProperty('delete');
      expect(endpoints.posts).toHaveProperty('like');
      expect(endpoints.posts).toHaveProperty('getLikes');
      expect(endpoints.posts).toHaveProperty('getComments');
      expect(endpoints.posts).toHaveProperty('addComment');
      expect(endpoints.posts).toHaveProperty('uploadImage');
    });
  });

  describe('Auth Service', () => {
    test('should have getCurrentUser method', () => {
      expect(typeof authService.getCurrentUser).toBe('function');
    });

    test('should have logout method', () => {
      expect(typeof authService.logout).toBe('function');
    });

    test('should have deleteAccount method', () => {
      expect(typeof authService.deleteAccount).toBe('function');
    });
  });

  describe('Post Service', () => {
    test('should have getFeedPosts method', () => {
      expect(typeof postService.getFeedPosts).toBe('function');
    });

    test('should have getUserPosts method', () => {
      expect(typeof postService.getUserPosts).toBe('function');
    });

    test('should have createPost method', () => {
      expect(typeof postService.createPost).toBe('function');
    });

    test('should have createPostWithImage method', () => {
      expect(typeof postService.createPostWithImage).toBe('function');
    });

    test('should have deletePost method', () => {
      expect(typeof postService.deletePost).toBe('function');
    });

    test('should have likePost method', () => {
      expect(typeof postService.likePost).toBe('function');
    });

    test('should have getPostLikes method', () => {
      expect(typeof postService.getPostLikes).toBe('function');
    });

    test('should have getPostComments method', () => {
      expect(typeof postService.getPostComments).toBe('function');
    });

    test('should have addComment method', () => {
      expect(typeof postService.addComment).toBe('function');
    });
  });

  describe('User Service', () => {
    test('should have getUserProfile method', () => {
      expect(typeof userService.getUserProfile).toBe('function');
    });

    test('should have updateProfile method', () => {
      expect(typeof userService.updateProfile).toBe('function');
    });

    test('should have updateAvatarProfile method', () => {
      expect(typeof userService.updateAvatarProfile).toBe('function');
    });

    test('should have getAvatarProfile method', () => {
      expect(typeof userService.getAvatarProfile).toBe('function');
    });

    test('should have uploadProfilePicture method', () => {
      expect(typeof userService.uploadProfilePicture).toBe('function');
    });

    test('should have uploadCoverPhoto method', () => {
      expect(typeof userService.uploadCoverPhoto).toBe('function');
    });
  });

  describe('Friend Service', () => {
    test('should have getFriends method', () => {
      expect(typeof friendService.getFriends).toBe('function');
    });

    test('should have getFriendRequests method', () => {
      expect(typeof friendService.getFriendRequests).toBe('function');
    });

    test('should have sendFriendRequest method', () => {
      expect(typeof friendService.sendFriendRequest).toBe('function');
    });

    test('should have acceptFriendRequest method', () => {
      expect(typeof friendService.acceptFriendRequest).toBe('function');
    });

    test('should have declineFriendRequest method', () => {
      expect(typeof friendService.declineFriendRequest).toBe('function');
    });

    test('should have removeFriend method', () => {
      expect(typeof friendService.removeFriend).toBe('function');
    });

    test('should have getSuggestions method', () => {
      expect(typeof friendService.getSuggestions).toBe('function');
    });
  });

  describe('Message Service', () => {
    test('should have sendMessage method', () => {
      expect(typeof messageService.sendMessage).toBe('function');
    });

    test('should have getAvatarConversations method', () => {
      expect(typeof messageService.getAvatarConversations).toBe('function');
    });

    test('should have getConversation method', () => {
      expect(typeof messageService.getConversation).toBe('function');
    });
  });

  describe('Match Service', () => {
    test('should have getMatches method', () => {
      expect(typeof matchService.getMatches).toBe('function');
    });

    test('should have discoverMatches method', () => {
      expect(typeof matchService.discoverMatches).toBe('function');
    });

    test('should have getMatchConversation method', () => {
      expect(typeof matchService.getMatchConversation).toBe('function');
    });
  });
});

