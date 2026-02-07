import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Save, User as UserIcon, MapPin, Cake, Tag, FileText, Sparkles } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { ImmersivePageWrapper } from "@/components/ambient";
import { useWorldMode } from "@/contexts/WorldModeContext";
import useViewMode from "@/hooks/useViewMode";
import AppHeader from "@/components/AppHeader";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Profile = ({ user, setUser }) => {
  const navigate = useNavigate();
  const { worldMode } = useWorldMode();
  const { isImmersive } = useViewMode();
  const isAvatarWorld = worldMode === 'avatar';

  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    age: user.age || "",
    gender: user.gender || "",
    location: user.location || "",
    bio: user.bio || "",
    interests: user.interests?.join(", ") || "",
  });
  const [saving, setSaving] = useState(false);

  // Theme tokens
  const t = {
    headerBg: isImmersive ? 'rgba(10, 15, 30, 0.95)' : 'rgba(255, 255, 255, 0.85)',
    headerBorder: isImmersive ? 'rgba(71, 85, 105, 0.3)' : '#e9d5ff',
    cardBg: isImmersive ? 'rgba(15, 23, 42, 0.85)' : 'rgba(255, 255, 255, 0.98)',
    cardBorder: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
    text: isImmersive ? '#e2e8f0' : '#1e293b',
    textMuted: isImmersive ? '#94a3b8' : '#64748b',
    textSubtle: isImmersive ? '#64748b' : '#94a3b8',
    labelColor: isImmersive ? '#cbd5e1' : '#374151',
    inputBg: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
    inputBorder: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#d8b4fe',
    inputFocusBorder: isImmersive ? 'rgba(139, 92, 246, 0.6)' : '#a855f7',
    inputText: isImmersive ? '#e2e8f0' : '#1e293b',
    valueBg: isImmersive ? 'rgba(30, 35, 55, 0.4)' : '#f8fafc',
    valueText: isImmersive ? '#cbd5e1' : '#1e293b',
    badgeBg: isImmersive ? 'rgba(168, 85, 247, 0.2)' : '#f3e8ff',
    badgeText: isImmersive ? '#c4b5fd' : '#7c3aed',
    accentPurple: isImmersive ? '#a78bfa' : '#7c3aed',
    shadow: isImmersive 
      ? '0 8px 32px rgba(0, 0, 0, 0.4)' 
      : '0 4px 24px rgba(0, 0, 0, 0.06)',
  };

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

  // Form field component
  const FormField = ({ icon: Icon, label, testId, children }) => (
    <div data-testid={testId}>
      <label 
        className="flex items-center text-sm font-semibold mb-2.5"
        style={{ color: t.labelColor }}
      >
        <Icon className="w-4 h-4 mr-2" style={{ color: t.accentPurple }} />
        {label}
      </label>
      {children}
    </div>
  );

  return (
    <ImmersivePageWrapper pageId="profile-edit" user={user}>
      <AppHeader user={user} setUser={setUser} currentPage="profile" />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
        {/* Page Title */}
        <div className="flex items-center justify-between mb-6 sm:mb-8">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              data-testid="back-to-dashboard-btn"
              className="rounded-xl"
              style={{ color: t.text }}
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold" style={{ color: t.text }}>
                Profile
              </h1>
              <p className="text-sm mt-0.5" style={{ color: t.textMuted }}>
                Manage your personal information
              </p>
            </div>
          </div>
          {!editing ? (
            <Button
              onClick={() => setEditing(true)}
              data-testid="edit-profile-btn"
              className="bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white px-5 py-2 rounded-xl text-sm font-medium"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Edit Profile
            </Button>
          ) : (
            <div className="flex gap-2">
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
                className="rounded-xl text-sm"
                style={{ 
                  borderColor: isImmersive ? 'rgba(139, 92, 246, 0.4)' : '#d8b4fe',
                  color: isImmersive ? '#c4b5fd' : '#7c3aed',
                  backgroundColor: 'transparent',
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={saving}
                data-testid="save-profile-btn"
                className="bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white px-5 py-2 rounded-xl text-sm font-medium"
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

        {/* Profile Card */}
        <div 
          className="rounded-2xl p-6 sm:p-8 mb-6"
          data-testid="profile-card"
          style={{ 
            backgroundColor: t.cardBg, 
            border: `1px solid ${t.cardBorder}`,
            boxShadow: t.shadow,
          }}
        >
          {/* Avatar Section */}
          <div className="text-center mb-8">
            <Avatar 
              className="w-28 h-28 sm:w-32 sm:h-32 mx-auto mb-4"
              style={{ 
                border: `4px solid ${isImmersive ? 'rgba(139, 92, 246, 0.3)' : 'white'}`,
                boxShadow: isImmersive 
                  ? '0 0 30px rgba(139, 92, 246, 0.15)' 
                  : '0 8px 24px rgba(0, 0, 0, 0.1)',
              }}
            >
              <AvatarImage src={user.picture} />
              <AvatarFallback className="bg-gradient-to-br from-pink-400 to-purple-600 text-white text-3xl sm:text-4xl">
                {user.name?.charAt(0)}
              </AvatarFallback>
            </Avatar>
            <h2 className="text-2xl sm:text-3xl font-bold mb-1" style={{ color: t.text }}>
              {user.name}
            </h2>
            <p className="text-sm" style={{ color: t.textMuted }}>{user.email}</p>
            {user.profile_completed && (
              <Badge className="mt-3 bg-gradient-to-r from-green-500 to-emerald-600 text-white px-3 py-1">
                Profile Complete
              </Badge>
            )}
          </div>

          {/* Profile Fields */}
          <div className="space-y-5 sm:space-y-6">
            {/* Age */}
            <FormField icon={Cake} label="Age" testId="profile-age-field">
              {editing ? (
                <Input
                  type="number"
                  value={formData.age}
                  onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                  placeholder="Enter your age"
                  className="rounded-xl h-11"
                  style={{ backgroundColor: t.inputBg, borderColor: t.inputBorder, color: t.inputText }}
                  data-testid="age-input"
                />
              ) : (
                <p 
                  className="py-2.5 px-4 rounded-xl text-sm"
                  style={{ backgroundColor: t.valueBg, color: t.valueText }}
                >
                  {user.age || "Not set"}
                </p>
              )}
            </FormField>

            {/* Gender */}
            <FormField icon={UserIcon} label="Gender" testId="profile-gender-field">
              {editing ? (
                <Input
                  value={formData.gender}
                  onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                  placeholder="Enter your gender"
                  className="rounded-xl h-11"
                  style={{ backgroundColor: t.inputBg, borderColor: t.inputBorder, color: t.inputText }}
                  data-testid="gender-input"
                />
              ) : (
                <p 
                  className="py-2.5 px-4 rounded-xl text-sm"
                  style={{ backgroundColor: t.valueBg, color: t.valueText }}
                >
                  {user.gender || "Not set"}
                </p>
              )}
            </FormField>

            {/* Location */}
            <FormField icon={MapPin} label="Location" testId="profile-location-field">
              {editing ? (
                <Input
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="Enter your location"
                  className="rounded-xl h-11"
                  style={{ backgroundColor: t.inputBg, borderColor: t.inputBorder, color: t.inputText }}
                  data-testid="location-input"
                />
              ) : (
                <p 
                  className="py-2.5 px-4 rounded-xl text-sm"
                  style={{ backgroundColor: t.valueBg, color: t.valueText }}
                >
                  {user.location || "Not set"}
                </p>
              )}
            </FormField>

            {/* Bio */}
            <FormField icon={FileText} label="Bio" testId="profile-bio-field">
              {editing ? (
                <Textarea
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  placeholder="Tell us about yourself..."
                  rows={4}
                  className="rounded-xl resize-none"
                  style={{ backgroundColor: t.inputBg, borderColor: t.inputBorder, color: t.inputText }}
                  data-testid="bio-input"
                />
              ) : (
                <p 
                  className="py-2.5 px-4 rounded-xl text-sm"
                  style={{ backgroundColor: t.valueBg, color: t.valueText }}
                >
                  {user.bio || "Not set"}
                </p>
              )}
            </FormField>

            {/* Interests */}
            <FormField icon={Tag} label="Interests" testId="profile-interests-field">
              {editing ? (
                <>
                  <Input
                    value={formData.interests}
                    onChange={(e) => setFormData({ ...formData, interests: e.target.value })}
                    placeholder="hiking, reading, music (comma separated)"
                    className="rounded-xl h-11"
                    style={{ backgroundColor: t.inputBg, borderColor: t.inputBorder, color: t.inputText }}
                    data-testid="interests-input"
                  />
                  <p className="text-xs mt-1.5" style={{ color: t.textSubtle }}>
                    Separate interests with commas
                  </p>
                </>
              ) : user.interests && user.interests.length > 0 ? (
                <div className="flex flex-wrap gap-2 pt-1">
                  {user.interests.map((interest, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1.5 rounded-full text-sm font-medium"
                      style={{ backgroundColor: t.badgeBg, color: t.badgeText }}
                    >
                      {interest}
                    </span>
                  ))}
                </div>
              ) : (
                <p 
                  className="py-2.5 px-4 rounded-xl text-sm"
                  style={{ backgroundColor: t.valueBg, color: t.valueText }}
                >
                  No interests added
                </p>
              )}
            </FormField>
          </div>
        </div>

        {/* AI Agent Info */}
        <div 
          className="rounded-2xl p-6"
          data-testid="ai-agent-info"
          style={{ 
            backgroundColor: t.cardBg, 
            border: `1px solid ${t.cardBorder}`,
            boxShadow: t.shadow,
          }}
        >
          <h3 className="text-lg font-bold mb-2" style={{ color: t.text }}>
            Your AI Agent
          </h3>
          <p className="text-sm leading-relaxed" style={{ color: t.textMuted }}>
            Your personal AI agent represents you in conversations with other users' AI agents. It learns
            from your profile, interests, and preferences to find the best matches for you.
          </p>
        </div>
      </main>
    </ImmersivePageWrapper>
  );
};

export default Profile;
