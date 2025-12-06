# Reusable Components Usage Guide

## Common Components

### UserAvatar
Standardized avatar component with fallback and navigation.

```javascript
import { UserAvatar } from '@/components/common';

<UserAvatar
  user={user}
  size="md" // 'sm' | 'md' | 'lg' | 'xl'
  showName={false}
  worldMode="real" // 'real' | 'avatar'
  onClick={() => navigate(`/profile/${user.id}`)}
/>
```

### LoadingSpinner
Centralized loading component.

```javascript
import { LoadingSpinner } from '@/components/common';

<LoadingSpinner
  size="md" // 'sm' | 'md' | 'lg'
  message="Loading..."
  fullScreen={false}
/>
```

### ErrorBoundary
Catches React errors and displays fallback UI.

```javascript
import { ErrorBoundary } from '@/components/common';

<ErrorBoundary showDetails={false}>
  <YourComponent />
</ErrorBoundary>
```

## Post Components

### PostCard
Complete post card with all sections.

```javascript
import { PostCard } from '@/features/posts/components';

<PostCard
  post={post}
  currentUser={currentUser}
  worldMode={worldMode}
  isLiked={likedPosts.has(post.id)}
  onLike={(postId) => handleLikePost(postId)}
  onComment={(postId) => showComments(postId)}
  onShare={() => handleShare(post)}
  onUserClick={(userId) => navigate(`/profile/${userId}`)}
  comments={commentsData[post.id] || []}
  onAddComment={async (postId, text) => {
    const comment = await postService.addComment(postId, text);
    return comment;
  }}
  showComments={showingCommentsFor === post.id}
  onToggleComments={(postId) => setShowingCommentsFor(postId)}
/>
```

### PostHeader
Post header with user info and timestamp.

```javascript
import { PostHeader } from '@/features/posts/components';

<PostHeader
  post={post}
  user={post.user}
  worldMode={worldMode}
  onMoreClick={() => handleMoreOptions(post.id)}
/>
```

### PostContent
Post content (text and image).

```javascript
import { PostContent } from '@/features/posts/components';

<PostContent post={post} />
```

### PostEngagement
Engagement stats display.

```javascript
import { PostEngagement } from '@/features/posts/components';

<PostEngagement
  post={post}
  onLikesClick={(postId) => showLikes(postId)}
  onCommentsClick={(postId) => showComments(postId)}
/>
```

### PostActions
Action buttons (Like, Comment, Share).

```javascript
import { PostActions } from '@/features/posts/components';

<PostActions
  postId={post.id}
  isLiked={isLiked}
  onLike={(postId) => handleLike(postId)}
  onComment={(postId) => showComments(postId)}
  onShare={() => handleShare(post)}
/>
```

### CommentSection
Complete comment section with input and list.

```javascript
import { CommentSection } from '@/features/posts/components';

<CommentSection
  postId={post.id}
  comments={comments}
  currentUser={currentUser}
  onAddComment={async (postId, text) => {
    return await postService.addComment(postId, text);
  }}
  onUserClick={(userId) => navigate(`/profile/${userId}`)}
  isLoading={addingComment}
/>
```

### CommentItem
Individual comment display.

```javascript
import { CommentItem } from '@/features/posts/components';

<CommentItem
  comment={comment}
  onUserClick={(userId) => navigate(`/profile/${userId}`)}
/>
```

### LikeButton
Reusable like button.

```javascript
import { LikeButton } from '@/features/posts/components';

<LikeButton
  postId={post.id}
  isLiked={isLiked}
  likesCount={post.likes}
  onClick={(postId) => handleLike(postId)}
  showCount={true}
  variant="button" // 'button' | 'icon'
/>
```

## Benefits

- ✅ **Modular**: Each component has a single responsibility
- ✅ **Reusable**: Can be used across different pages
- ✅ **Maintainable**: Changes in one place affect all usages
- ✅ **Testable**: Easy to test individual components
- ✅ **Type-safe**: Props are clearly defined
- ✅ **Performance**: Components are memoized to prevent unnecessary re-renders

