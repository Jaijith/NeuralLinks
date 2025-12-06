import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { FileText, MessageCircle, Heart, Hand } from 'lucide-react';
import { postService } from '@/services/api';

/**
 * Avatar Activity Log Component
 * Displays recent avatar activities
 */
const AvatarActivityLog = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchActivities = async () => {
      try {
        // Note: This endpoint might need to be created or adjusted
        const response = await postService.getAvatarActivities?.() || { activities: [] };
        setActivities(response.activities || []);
      } catch (error) {
        console.error('Failed to fetch activities:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchActivities();
  }, []);

  if (loading) return <p className="text-gray-500">Loading activities...</p>;
  if (activities.length === 0) return <p className="text-gray-500">No activities yet. Enable autonomy to see your avatar in action!</p>;

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto">
      {activities.map((activity, idx) => {
        let IconComponent;
        let iconColor;
        if (activity.action_type === 'post') {
          IconComponent = FileText;
          iconColor = 'text-blue-600';
        } else if (activity.action_type === 'comment') {
          IconComponent = MessageCircle;
          iconColor = 'text-green-600';
        } else if (activity.action_type === 'like') {
          IconComponent = Heart;
          iconColor = 'text-red-600';
        } else {
          IconComponent = Hand;
          iconColor = 'text-yellow-600';
        }

        return (
          <Card key={idx} className="p-3 hover:bg-gray-50 transition-colors">
            <div className="flex items-start space-x-4">
              <div className={`p-2 rounded-lg bg-gray-100 ${iconColor}`}>
                <IconComponent className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-800">{activity.description}</p>
                <p className="text-xs text-gray-500 mt-1">{new Date(activity.timestamp).toLocaleString()}</p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
};

export default AvatarActivityLog;
