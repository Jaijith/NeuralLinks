import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Sidebar, SidebarSection } from '@/components/layout';
import { Users, Image, Bookmark, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';

/**
 * @typedef {Object} HomeSidebarProps
 * @property {Object} user - Current user object
 * @property {string} [worldMode] - Current world mode ('real' or 'avatar')
 */

/**
 * Home Left Sidebar component with profile card, quick links, and trending.
 * Supports both Maya (avatar) and Sense (real) worlds.
 */
const HomeSidebar = React.memo(({ user, worldMode = 'real' }) => {
  const navigate = useNavigate();
  const isAvatarWorld = worldMode === 'avatar';

  const displayName = isAvatarWorld 
    ? (user.avatar_name || user.name)
    : user.name;
  const displayPicture = isAvatarWorld
    ? (user.avatar_picture || user.picture)
    : user.picture;

  return (
    <Sidebar>
      {/* Profile Card */}
      <SidebarSection>
        <div 
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => navigate('/myprofile')}
        >
          <Avatar className="w-14 h-14">
            <AvatarImage src={displayPicture} />
            <AvatarFallback className="text-lg font-semibold bg-blue-500 text-white">
              {displayName?.charAt(0)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h3 className="font-semibold text-gray-900">
              {displayName}
            </h3>
            <p className="text-sm text-gray-600">
              {user.bio || (isAvatarWorld ? 'Digital spirit in Maya' : 'Welcome to your feed')}
            </p>
          </div>
        </div>
      </SidebarSection>

      {/* Quick Links */}
      <SidebarSection>
        <div className="space-y-1">
          {[
            { icon: Users, label: isAvatarWorld ? 'Connections' : 'Friends', path: '/friends', iconColor: '#3b82f6' },
            { icon: Image, label: 'Gallery', path: '/gallery', iconColor: '#10b981' },
            { icon: Bookmark, label: 'Saved', path: '#', iconColor: '#f59e0b' },
          ].map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                onClick={() => item.path !== '#' ? navigate(item.path) : toast.info('Coming soon!')}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all hover:bg-gray-100"
              >
                <Icon className="w-5 h-5" style={{ color: item.iconColor }} />
                <span className="font-medium text-sm text-gray-700">{item.label}</span>
              </button>
            );
          })}
        </div>
      </SidebarSection>

      {/* Trending Section */}
      <SidebarSection title={isAvatarWorld ? 'Trending in Maya' : 'Trending'}>
        <div className="space-y-3">
          {[
            { tag: '#Connections', posts: 584 },
            { tag: '#MayaWorld', posts: 803 },
            { tag: '#AIFriends', posts: 226 },
          ].map((item, idx) => (
            <div key={idx}>
              <span className="font-semibold text-sm text-gray-900">{item.tag}</span>
              <p className="text-xs text-gray-600">{item.posts} posts</p>
            </div>
          ))}
        </div>
      </SidebarSection>

    </Sidebar>
  );
});

HomeSidebar.displayName = "HomeSidebar";

export default HomeSidebar;

