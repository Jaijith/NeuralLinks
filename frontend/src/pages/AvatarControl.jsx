import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { ScrollArea } from "../components/ui/scroll-area";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const AvatarControl = () => {
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  // Fetch avatar configuration
  const fetchConfig = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/avatar/config`, {
        withCredentials: true
      });
      setConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
      setMessage({ type: 'error', text: 'Failed to load configuration' });
    }
  };

  // Fetch avatar status
  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/avatar/status`, {
        withCredentials: true
      });
      setStatus(response.data);
    } catch (error) {
      console.error('Error fetching status:', error);
    }
  };

  // Fetch recent activity
  const fetchActivity = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/avatar/activity?limit=20`, {
        withCredentials: true
      });
      setActivities(response.data.activities || []);
    } catch (error) {
      console.error('Error fetching activity:', error);
    }
  };

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchConfig(), fetchStatus(), fetchActivity()]);
      setLoading(false);
    };
    loadData();

    // Refresh status and activity every 30 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchActivity();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Update configuration
  const updateConfig = async (updates) => {
    setSaving(true);
    setMessage(null);
    
    try {
      const params = new URLSearchParams(updates);
      const response = await axios.put(`${BACKEND_URL}/api/avatar/config?${params}`, {}, {
        withCredentials: true
      });
      
      setMessage({ type: 'success', text: response.data.message });
      
      // Refresh data
      await Promise.all([fetchConfig(), fetchStatus()]);
    } catch (error) {
      console.error('Error updating config:', error);
      setMessage({ type: 'error', text: 'Failed to update configuration' });
    } finally {
      setSaving(false);
    }
  };

  // Toggle autonomy
  const toggleAutonomy = async (enabled) => {
    await updateConfig({ avatar_autonomous: enabled });
  };

  // Change activity level
  const changeActivityLevel = async (level) => {
    await updateConfig({ avatar_activity_level: level });
  };

  // Change archetype
  const changeArchetype = async (archetype) => {
    await updateConfig({ archetype });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading avatar configuration...</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>Failed to load avatar configuration</AlertDescription>
        </Alert>
      </div>
    );
  }

  const archetypeDescriptions = {
    social_butterfly: "Highly active, loves conversations, frequent poster",
    thoughtful_contributor: "Quality over quantity, deep conversations, meaningful posts",
    casual_observer: "Reads more than posts, occasional contributions",
    niche_expert: "Focused on specific interests, deep knowledge sharing",
    enthusiastic_newcomer: "New to the platform, excited, learning the ropes"
  };

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Avatar Control Panel</h1>
        <p className="text-gray-600">
          Manage your autonomous avatar: <span className="font-semibold">{config.avatar_name || 'Not set'}</span>
        </p>
      </div>

      {/* Messages */}
      {message && (
        <Alert className="mb-6" variant={message.type === 'error' ? 'destructive' : 'default'}>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}

      {/* Main Content */}
      <Tabs defaultValue="config" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="activity">Activity Log</TabsTrigger>
          <TabsTrigger value="status">Status</TabsTrigger>
        </TabsList>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-6">
          {/* Autonomy Control */}
          <Card>
            <CardHeader>
              <CardTitle>Autonomy Control</CardTitle>
              <CardDescription>
                Enable or disable your avatar's autonomous behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <h3 className="font-semibold">Avatar Autonomy</h3>
                  <p className="text-sm text-gray-600">
                    When enabled, your avatar will automatically interact with posts, create content, and engage with others
                  </p>
                </div>
                <Switch
                  checked={config.avatar_autonomous}
                  onCheckedChange={toggleAutonomy}
                  disabled={saving}
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <Badge variant={config.avatar_autonomous ? "default" : "secondary"}>
                  {config.avatar_autonomous ? '✓ Active' : '○ Inactive'}
                </Badge>
                {config.autonomous_enabled_at && (
                  <span className="text-sm text-gray-500">
                    Since {new Date(config.autonomous_enabled_at).toLocaleString()}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Activity Level */}
          <Card>
            <CardHeader>
              <CardTitle>Activity Level</CardTitle>
              <CardDescription>
                How active should your avatar be?
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select
                value={config.avatar_activity_level}
                onValueChange={changeActivityLevel}
                disabled={saving || !config.avatar_autonomous}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">
                    <div className="flex flex-col">
                      <span className="font-medium">Low</span>
                      <span className="text-xs text-gray-500">1-2 actions per day</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="medium">
                    <div className="flex flex-col">
                      <span className="font-medium">Medium</span>
                      <span className="text-xs text-gray-500">5-10 actions per day</span>
                    </div>
                  </SelectItem>
                  <SelectItem value="high">
                    <div className="flex flex-col">
                      <span className="font-medium">High</span>
                      <span className="text-xs text-gray-500">15-20 actions per day</span>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>

              {!config.avatar_autonomous && (
                <p className="text-sm text-gray-500 italic">
                  Enable autonomy to change activity level
                </p>
              )}
            </CardContent>
          </Card>

          {/* Personality */}
          <Card>
            <CardHeader>
              <CardTitle>Personality Archetype</CardTitle>
              <CardDescription>
                Choose how your avatar behaves and interacts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select
                value={config.archetype}
                onValueChange={changeArchetype}
                disabled={saving}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {config.available_archetypes && config.available_archetypes.map((arch) => (
                    <SelectItem key={arch} value={arch}>
                      <div className="flex flex-col">
                        <span className="font-medium capitalize">
                          {arch.replace('_', ' ')}
                        </span>
                        <span className="text-xs text-gray-500">
                          {archetypeDescriptions[arch]}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-900">
                  <strong>Current:</strong> {archetypeDescriptions[config.archetype]}
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Activity Log Tab */}
        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                What your avatar has been doing
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px] pr-4">
                {activities.length === 0 ? (
                  <div className="text-center py-12 text-gray-500">
                    <p>No activity yet</p>
                    <p className="text-sm mt-2">
                      {config.avatar_autonomous 
                        ? "Your avatar will start acting soon!"
                        : "Enable autonomy to see activity"}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {activities.map((activity, index) => (
                      <div 
                        key={index}
                        className="p-4 border rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="outline">
                                {activity.activity_type.replace('_', ' ')}
                              </Badge>
                              <span className="text-xs text-gray-500">
                                {new Date(activity.timestamp).toLocaleString()}
                              </span>
                            </div>
                            {activity.details && (
                              <div className="text-sm text-gray-700 mt-2">
                                {activity.details.comment_text && (
                                  <p className="italic">"{activity.details.comment_text}"</p>
                                )}
                                {activity.details.content_preview && (
                                  <p className="italic">"{activity.details.content_preview}"</p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Status Tab */}
        <TabsContent value="status">
          <Card>
            <CardHeader>
              <CardTitle>Avatar Status</CardTitle>
              <CardDescription>
                Current state of your autonomous avatar
              </CardDescription>
            </CardHeader>
            <CardContent>
              {status && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600">Status</p>
                      <p className="text-2xl font-bold capitalize">{status.status}</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600">Actions (Last Hour)</p>
                      <p className="text-2xl font-bold">{status.actions_last_hour}</p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600">Personality</p>
                      <p className="text-lg font-semibold capitalize">
                        {status.archetype.replace('_', ' ')}
                      </p>
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <p className="text-sm text-gray-600">Activity Level</p>
                      <p className="text-lg font-semibold capitalize">{status.activity_level}</p>
                    </div>
                  </div>

                  {status.last_activity && (
                    <div className="p-4 border rounded-lg">
                      <p className="text-sm text-gray-600 mb-1">Last Activity</p>
                      <p className="font-medium">
                        {new Date(status.last_activity).toLocaleString()}
                      </p>
                    </div>
                  )}

                  {!status.is_autonomous && (
                    <Alert>
                      <AlertTitle>Avatar is Inactive</AlertTitle>
                      <AlertDescription>
                        Enable autonomy in the Configuration tab to activate your avatar
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AvatarControl;

