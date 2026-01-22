import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Save, User as UserIcon, MapPin, Cake, Tag } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { ImmersivePageWrapper } from "@/components/ambient";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Profile = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    age: user.age || "",
    gender: user.gender || "",
    location: user.location || "",
    bio: user.bio || "",
    interests: user.interests?.join(", ") || "",
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updateData = {
        ...formData,
        age: parseInt(formData.age) || null,
        interests: formData.interests
          .split(",")
          .map((i) => i.trim())
          .filter((i) => i),
        profile_completed: true,
      };

      await axios.put(`${API}/profile`, updateData, {
        withCredentials: true,
      });

      // Refresh user data
      const response = await axios.get(`${API}/auth/me`, {
        withCredentials: true,
      });
      setUser(response.data);

      toast.success("Profile updated successfully!");
      setEditing(false);
    } catch (error) {
      console.error("Error updating profile:", error);
      toast.error("Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ImmersivePageWrapper pageId="profile-edit" user={user}>
      {/* Header */}
      <header className="bg-white/70 backdrop-blur-md border-b border-purple-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              onClick={() => navigate("/dashboard")}
              data-testid="back-to-dashboard-btn"
              className="hover:bg-purple-50"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h1 className="text-2xl font-bold gradient-text">Profile</h1>
          </div>
          {!editing ? (
            <Button
              onClick={() => setEditing(true)}
              data-testid="edit-profile-btn"
              className="btn-primary text-white px-6 py-2 rounded-full"
            >
              Edit Profile
            </Button>
          ) : (
            <div className="flex space-x-2">
              <Button
                variant="outline"
                onClick={() => {
                  setEditing(false);
                  setFormData({
                    age: user.age || "",
                    gender: user.gender || "",
                    location: user.location || "",
                    bio: user.bio || "",
                    interests: user.interests?.join(", ") || "",
                  });
                }}
                data-testid="cancel-edit-btn"
                className="border-2 border-purple-300 text-purple-700 hover:bg-purple-50"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
                data-testid="save-profile-btn"
                className="btn-primary text-white px-6 py-2 rounded-full"
              >
                {saving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        {/* Profile Card */}
        <Card className="glass-morphism p-8 mb-8" data-testid="profile-card">
          {/* Avatar Section */}
          <div className="text-center mb-8">
            <Avatar className="w-32 h-32 border-4 border-white shadow-xl mx-auto mb-4">
              <AvatarImage src={user.picture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-4xl">
                {user.name?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            <h2 className="text-3xl font-bold text-gray-800 mb-1">{user.name}</h2>
            <p className="text-gray-600">{user.email}</p>
            {user.profile_completed && (
              <Badge className="mt-2 bg-gradient-to-r from-green-500 to-emerald-600 text-white">
                Profile Complete
              </Badge>
            )}
          </div>

          {/* Profile Fields */}
          <div className="space-y-6">
            {/* Age */}
            <div data-testid="profile-age-field">
              <label className="flex items-center text-sm font-semibold text-gray-700 mb-2">
                <Cake className="w-4 h-4 mr-2 text-purple-600" />
                Age
              </label>
              {editing ? (
                <Input
                  type="number"
                  value={formData.age}
                  onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                  placeholder="Enter your age"
                  className="border-2 border-purple-200 focus:border-purple-400 rounded-xl"
                  data-testid="age-input"
                />
              ) : (
                <p className="text-gray-800 py-2">{user.age || "Not set"}</p>
              )}
            </div>

            {/* Gender */}
            <div data-testid="profile-gender-field">
              <label className="flex items-center text-sm font-semibold text-gray-700 mb-2">
                <UserIcon className="w-4 h-4 mr-2 text-purple-600" />
                Gender
              </label>
              {editing ? (
                <Input
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  placeholder="Enter your gender"
                  className="border-2 border-purple-200 focus:border-purple-400 rounded-xl"
                  data-testid="gender-input"
                />
              ) : (
                <p className="text-gray-800 py-2">{user.gender || "Not set"}</p>
              )}
            </div>

            {/* Location */}
            <div data-testid="profile-location-field">
              <label className="flex items-center text-sm font-semibold text-gray-700 mb-2">
                <MapPin className="w-4 h-4 mr-2 text-purple-600" />
                Location
              </label>
              {editing ? (
                <Input
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="Enter your location"
                  className="border-2 border-purple-200 focus:border-purple-400 rounded-xl"
                  data-testid="location-input"
                />
              ) : (
                <p className="text-gray-800 py-2">{user.location || "Not set"}</p>
              )}
            </div>

            {/* Bio */}
            <div data-testid="profile-bio-field">
              <label className="flex items-center text-sm font-semibold text-gray-700 mb-2">
                <UserIcon className="w-4 h-4 mr-2 text-purple-600" />
                Bio
              </label>
              {editing ? (
                <Textarea
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  placeholder="Tell us about yourself..."
                  rows={4}
                  className="border-2 border-purple-200 focus:border-purple-400 rounded-xl"
                  data-testid="bio-input"
                />
              ) : (
                <p className="text-gray-800 py-2">{user.bio || "Not set"}</p>
              )}
            </div>

            {/* Interests */}
            <div data-testid="profile-interests-field">
              <label className="flex items-center text-sm font-semibold text-gray-700 mb-2">
                <Tag className="w-4 h-4 mr-2 text-purple-600" />
                Interests
              </label>
              {editing ? (
                <>
                  <Input
                    value={formData.interests}
                    onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
                    placeholder="hiking, reading, music (comma separated)"
                    className="border-2 border-purple-200 focus:border-purple-400 rounded-xl"
                    data-testid="interests-input"
                  />
                  <p className="text-xs text-gray-500 mt-1">Separate interests with commas</p>
                </>
              ) : user.interests && user.interests.length > 0 ? (
                <div className="flex flex-wrap gap-2 pt-2">
                  {user.interests.map((interest, idx) => (
                    <span
                      key={idx}
                      className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full text-sm"
                    >
                      {interest}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-800 py-2">No interests added</p>
              )}
            </div>
          </div>
        </Card>

        {/* AI Agent Info */}
        <Card className="glass-morphism p-6" data-testid="ai-agent-info">
          <h3 className="text-xl font-bold text-gray-800 mb-3">Your AI Agent</h3>
          <p className="text-gray-600">
            Your personal AI agent represents you in conversations with other users' AI agents. It learns
            from your profile, interests, and preferences to find the best matches for you.
          </p>
        </Card>
      </main>
    </ImmersivePageWrapper>
  );
};

export default Profile;
