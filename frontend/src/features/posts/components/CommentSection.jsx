/**
 * CommentSection Component
 * Complete comment section with input and list
 */

import { useState, memo, useCallback } from 'react';
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
  onUserClick,
  isLoading = false
}) => {
  const [commentText, setCommentText] = useState('');

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

      {/* Comments List */}
      {comments.length > 0 ? (
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id || Math.random()}
              comment={comment}
              onUserClick={onUserClick}
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

