/**
 * CommentSection Component
 * Complete comment section with input and list - supports threaded replies
 */

import { useState, memo, useCallback, useMemo } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import CommentItem from './CommentItem';

const CommentSection = memo(({ 
  postId,
  comments = [],
  currentUser,
  onAddComment,
  onReplyComment,
  onLikeComment,
  onUserClick,
  isLoading = false
}) => {
  const [commentText, setCommentText] = useState('');

  // Build threaded comment structure from flat list
  // Comments starting with @username are treated as replies to that user's most recent comment
  const threadedComments = useMemo(() => {
    if (!comments || comments.length === 0) return { threads: [], rootCount: 0 };
    
    // Sort comments by created_at to maintain chronological order
    const sortedComments = [...comments].sort((a, b) => 
      new Date(a.created_at) - new Date(b.created_at)
    );
    
    const rootComments = [];
    const commentById = {}; // Map comment id to comment object
    const commentsByUser = {}; // Map username (lowercase) to their most recent comment/reply
    const allUsernames = new Set(); // Collect all usernames for matching
    
    // First pass: collect all usernames
    sortedComments.forEach(comment => {
      if (comment.user_name) {
        allUsernames.add(comment.user_name);
      }
    });
    
    // Helper function to find mentioned username from text
    // Handles usernames with spaces by checking against known usernames
    const findMentionedUser = (text) => {
      if (!text.startsWith('@')) return null;
      
      const textAfterAt = text.slice(1); // Remove the @
      
      // Try to match against known usernames (case-insensitive, longest match first)
      const sortedUsernames = [...allUsernames].sort((a, b) => b.length - a.length);
      
      for (const username of sortedUsernames) {
        // Check if text starts with this username (case-insensitive) followed by space or end
        if (textAfterAt.toLowerCase().startsWith(username.toLowerCase())) {
          const afterUsername = textAfterAt.slice(username.length);
          // Username must be followed by space, end of string, or punctuation
          if (afterUsername === '' || /^[\s.,!?]/.test(afterUsername)) {
            const remainingText = afterUsername.trimStart();
            return { username, remainingText: remainingText || '' };
          }
        }
      }
      
      return null;
    };
    
    sortedComments.forEach(comment => {
      const text = comment.text || '';
      const mentionInfo = findMentionedUser(text);
      
      const commentObj = {
        ...comment,
        replies: []
      };
      
      // Store in id map
      commentById[comment.id] = commentObj;
      
      if (!mentionInfo) {
        // This is a root comment (no @mention or unknown user)
        rootComments.push(commentObj);
        // Track this as the user's most recent comment
        if (comment.user_name) {
          commentsByUser[comment.user_name.toLowerCase()] = commentObj;
        }
      } else {
        // This is a reply to someone
        const mentionedUser = mentionInfo.username;
        const replyText = mentionInfo.remainingText || text;
        
        commentObj.text = replyText;
        commentObj.replyingTo = mentionedUser;
        
        // Find the most recent comment/reply by the mentioned user
        const parentComment = commentsByUser[mentionedUser.toLowerCase()];
        
        if (parentComment) {
          // Add as a nested reply to that comment
          parentComment.replies.push(commentObj);
        } else {
          // No parent found - add as root but show the mention
          commentObj.text = text; // Keep original text with @mention
          rootComments.push(commentObj);
        }
        
        // Track this reply as the user's most recent comment (for nested replies)
        if (comment.user_name) {
          commentsByUser[comment.user_name.toLowerCase()] = commentObj;
        }
      }
    });
    
    return { threads: rootComments, rootCount: rootComments.length };
  }, [comments]);
  
  // Get just the threaded array for rendering
  const threads = threadedComments.threads;
  const rootCommentCount = threadedComments.rootCount;

  const handleSubmit = useCallback(() => {
    if (commentText.trim() && onAddComment) {
      onAddComment(postId, commentText.trim());
      setCommentText('');
    }
  }, [postId, commentText, onAddComment]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  // Handle reply to a comment
  const handleReply = useCallback((parentCommentId, replyText) => {
    if (onReplyComment) {
      onReplyComment(postId, parentCommentId, replyText);
    } else if (onAddComment) {
      // Fallback: add as a regular comment with mention
      const findComment = (commentsList) => {
        for (const c of commentsList) {
          if (c.id === parentCommentId) return c;
          if (c.replies?.length) {
            const found = findComment(c.replies);
            if (found) return found;
          }
        }
        return null;
      };
      const parentComment = findComment(threads);
      const mentionText = parentComment?.user_name 
        ? `@${parentComment.user_name} ${replyText}`
        : replyText;
      onAddComment(postId, mentionText);
    }
  }, [postId, threads, onAddComment, onReplyComment]);

  return (
    <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
      {/* Comment Input */}
      <div className="flex items-start gap-3 mb-4">
        <Avatar className="w-8 h-8">
          <AvatarImage src={currentUser?.picture || currentUser?.avatar_picture} />
          <AvatarFallback>
            {(currentUser?.name || currentUser?.avatar_name || '?').charAt(0).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 flex gap-2">
          <Input
            placeholder="Write a comment..."
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyPress={handleKeyPress}
            className="rounded-full text-sm bg-white border-gray-200"
            disabled={isLoading}
          />
          <Button
            onClick={handleSubmit}
            disabled={!commentText.trim() || isLoading}
            size="sm"
            className="rounded-full px-3 bg-blue-500 hover:bg-blue-600 text-white"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Comments List - Threaded */}
      {threads.length > 0 ? (
        <div className="max-h-96 overflow-y-auto pr-1">
          {/* Show actual comment count (root comments only) */}
          <p className="text-xs text-gray-500 mb-2 px-1">
            {rootCommentCount} {rootCommentCount === 1 ? 'comment' : 'comments'}
            {comments.length > rootCommentCount && ` · ${comments.length - rootCommentCount} ${comments.length - rootCommentCount === 1 ? 'reply' : 'replies'}`}
          </p>
          {threads.map((comment, index) => (
            <CommentItem
              key={comment.id || Math.random()}
              comment={comment}
              onUserClick={onUserClick}
              onReply={handleReply}
              onLikeComment={onLikeComment}
              currentUser={currentUser}
              level={0}
              isLastReply={index === threads.length - 1}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-center py-4 text-gray-500">
          No comments yet. Be the first to comment!
        </p>
      )}
    </div>
  );
});

CommentSection.displayName = 'CommentSection';

export default CommentSection;

