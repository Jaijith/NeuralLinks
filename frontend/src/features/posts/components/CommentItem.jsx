/**
 * CommentItem Component
 * Individual comment display component with reply functionality (LinkedIn style with thread lines)
 */

import { useState } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatTimeAgo } from '@/utils/dateUtils';
import { memo } from 'react';
import { Send } from 'lucide-react';

const CommentItem = memo(({ comment, onUserClick, onReply, onLikeComment, currentUser, level = 0, isLastReply = false }) => {
  const [showReplyInput, setShowReplyInput] = useState(false);
  const [replyText, setReplyText] = useState('');
  const [showReplies, setShowReplies] = useState(true);
  const [isLiked, setIsLiked] = useState(comment?.is_liked || false);
  const [likesCount, setLikesCount] = useState(comment?.likes_count || 0);

  if (!comment || typeof comment !== 'object') return null;

  const userName = comment.user_name || 'Unknown';
  const userPicture = comment.user_picture || '';
  const text = comment.text || '';
  const createdAt = comment.created_at;
  const replies = comment.replies || [];
  const replyingTo = comment.replyingTo || null;

  const handleSubmitReply = () => {
    if (replyText.trim() && onReply) {
      onReply(comment.id, replyText.trim());
      setReplyText('');
      setShowReplyInput(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitReply();
    }
  };

  const handleLike = () => {
    if (onLikeComment) {
      onLikeComment(comment.id, !isLiked);
    }
    setIsLiked(!isLiked);
    setLikesCount(prev => isLiked ? prev - 1 : prev + 1);
  };

  // Avatar size decreases with nesting level
  const avatarSize = level === 0 ? 'w-8 h-8' : level === 1 ? 'w-7 h-7' : 'w-6 h-6';
  
  return (
    <div className={`relative ${level > 0 ? 'mt-2' : 'mt-3 first:mt-0'}`}>
      <div className="flex gap-2">
        <Avatar 
          className={`${avatarSize} cursor-pointer flex-shrink-0`}
          onClick={() => onUserClick?.(comment.user_id)}
        >
          <AvatarImage src={userPicture} alt={userName} />
          <AvatarFallback className="text-xs bg-purple-100 text-purple-700">{userName.charAt(0).toUpperCase()}</AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="rounded-xl px-3 py-2 bg-gray-100 inline-block max-w-full">
            <div className="flex items-center gap-2 flex-wrap">
              <p 
                className="text-sm font-semibold text-gray-900 cursor-pointer hover:underline"
                onClick={() => onUserClick?.(comment.user_id)}
              >
                {userName}
              </p>
              {/* Show who this is replying to */}
              {replyingTo && (
                <span className="text-xs text-gray-500">
                  → <span className="text-blue-600 cursor-pointer hover:underline">@{replyingTo}</span>
                </span>
              )}
            </div>
            {comment.user_title && (
              <p className="text-xs text-gray-500">{comment.user_title}</p>
            )}
            <p className="text-sm text-gray-700 whitespace-pre-wrap mt-0.5">{text}</p>
          </div>
          
          {/* LinkedIn-style action row: Like · Reply · X replies · Time */}
          <div className="flex items-center flex-wrap gap-x-1 gap-y-0.5 mt-1 ml-1 text-xs text-gray-500">
            <button
              onClick={handleLike}
              className={`font-semibold hover:underline ${isLiked ? 'text-blue-600' : 'text-gray-600 hover:text-blue-600'}`}
            >
              {isLiked ? 'Liked' : 'Like'}
            </button>
            {likesCount > 0 && (
              <span className="text-gray-500">({likesCount})</span>
            )}
            <span className="text-gray-400">·</span>
            {level < 2 && onReply && (
              <>
                <button
                  onClick={() => setShowReplyInput(!showReplyInput)}
                  className="font-semibold text-gray-600 hover:text-blue-600 hover:underline"
                >
                  Reply
                </button>
                <span className="text-gray-400">·</span>
              </>
            )}
            {replies.length > 0 && (
              <>
                <button
                  onClick={() => setShowReplies(!showReplies)}
                  className="font-semibold text-gray-600 hover:text-blue-600 hover:underline"
                >
                  {showReplies ? 'Hide' : 'View'} {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
                </button>
                <span className="text-gray-400">·</span>
              </>
            )}
            {createdAt && (
              <span className="text-gray-400">
                {formatTimeAgo(createdAt)}
              </span>
            )}
          </div>
          
          {/* Reply Input */}
          {showReplyInput && currentUser && (
            <div className="flex items-center gap-2 mt-2 ml-2 pl-4 border-l-2 border-blue-300">
              <Avatar className="w-6 h-6">
                <AvatarImage src={currentUser?.picture || currentUser?.avatar_picture} />
                <AvatarFallback className="text-xs bg-blue-100 text-blue-700">
                  {(currentUser?.name || currentUser?.avatar_name || '?').charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 flex gap-2">
                <Input
                  placeholder={`Reply to ${userName}...`}
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyPress={handleKeyPress}
                  className="text-sm rounded-full flex-1 h-8 bg-gray-100 border-gray-200"
                  autoFocus
                />
                <Button
                  onClick={handleSubmitReply}
                  disabled={!replyText.trim()}
                  size="sm"
                  className="rounded-full h-8 px-3 bg-blue-600 hover:bg-blue-700 text-white"
                >
                  <Send className="w-3 h-3" />
                </Button>
              </div>
            </div>
          )}
          
          {/* Nested Replies with thread lines */}
          {showReplies && replies.length > 0 && (
            <div className={`relative mt-2 pl-3 ${level < 3 ? 'ml-3 border-l-2 border-gray-300' : 'ml-1'}`}>
              {replies.map((reply, index) => (
                <CommentItem
                  key={reply.id || Math.random()}
                  comment={{...reply, replyingTo: reply.replyingTo || userName}}
                  onUserClick={onUserClick}
                  onReply={level < 2 ? onReply : null} // Limit reply depth to 3 levels
                  onLikeComment={onLikeComment}
                  currentUser={currentUser}
                  level={level + 1}
                  isLastReply={index === replies.length - 1}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

CommentItem.displayName = 'CommentItem';

export default CommentItem;

