import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Settings, Link2, Eye, User, Trash2, AlertTriangle } from "lucide-react";
import IntegrationsPage from "./IntegrationsPage";
import AvatarVisualization from "./AvatarVisualization";
import AppHeader from "@/components/AppHeader";
import { useWorldMode } from "@/contexts/WorldModeContext";
import useViewMode from "@/hooks/useViewMode";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { ImmersivePageWrapper } from "@/components/ambient";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SettingsPage = ({ user, setUser }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("avatar");
  const { worldMode } = useWorldMode();
  const { isImmersive } = useViewMode();
  const isAvatarWorld = worldMode === 'avatar';
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  // Apply avatar-world class to body when in avatar mode
  useEffect(() => {
    if (isAvatarWorld) {
      document.body.classList.add('avatar-world');
    } else {
      document.body.classList.remove('avatar-world');
    }
    return () => {
      document.body.classList.remove('avatar-world');
    };
  }, [isAvatarWorld]);

  return (
    <ImmersivePageWrapper pageId="settings" user={user}>
      <AppHeader user={user} setUser={setUser} currentPage="settings" />
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 py-4 sm:py-6 md:py-8 pb-20 sm:pb-8">
        {/* Header */}
        <div className="mb-4 sm:mb-6 md:mb-8">
          <div className="flex items-center gap-2 sm:gap-3 mb-1 sm:mb-2">
            <Settings className={`w-6 h-6 sm:w-8 sm:h-8 ${isAvatarWorld ? 'text-slate-700' : 'text-purple-600'}`} />
            <h1 className={`text-2xl sm:text-3xl md:text-4xl font-bold ${isAvatarWorld ? 'text-slate-800' : 'gradient-text'}`}>
              Settings
            </h1>
          </div>
          <p className={`text-sm sm:text-base ${isAvatarWorld ? 'text-slate-600' : 'text-gray-600'}`}>
            Manage your integrations and view your avatar's knowledge graph
          </p>
        </div>

        {/* Tabs - scrollable on mobile */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-4 sm:mb-6 h-auto">
            <TabsTrigger 
              value="avatar" 
              className="flex items-center justify-center gap-1 sm:gap-2 px-2 py-2 sm:py-3 text-xs sm:text-sm min-h-[44px]"
            >
              <Eye className="w-4 h-4 flex-shrink-0" />
              <span className="hidden xs:inline">Avatar</span>
              <span className="xs:hidden">Avatar</span>
            </TabsTrigger>
            <TabsTrigger 
              value="integrations" 
              className="flex items-center justify-center gap-1 sm:gap-2 px-2 py-2 sm:py-3 text-xs sm:text-sm min-h-[44px]"
            >
              <Link2 className="w-4 h-4 flex-shrink-0" />
              <span className="hidden sm:inline">Integrations</span>
              <span className="sm:hidden">Connect</span>
            </TabsTrigger>
            <TabsTrigger 
              value="profile" 
              className="flex items-center justify-center gap-1 sm:gap-2 px-2 py-2 sm:py-3 text-xs sm:text-sm min-h-[44px]"
            >
              <User className="w-4 h-4 flex-shrink-0" />
              <span>Profile</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="avatar" className="mt-0">
            {user ? (
              <AvatarVisualization user={user} hideHeader={true} />
            ) : (
              <Card className="glass-morphism p-6">
                <div className="text-center py-12">
                  <Eye className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-gray-800 mb-2">Avatar Visualization</h3>
                  <p className="text-gray-600">Please log in to view your avatar visualization</p>
                </div>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="integrations" className="mt-0">
            <IntegrationsPage user={user} hideHeader={true} />
          </TabsContent>

          <TabsContent value="profile" className="mt-0">
            <Card className={`${isAvatarWorld ? 'card-avatar' : 'glass-morphism'} p-6`}>
              <div className="space-y-6">
                <div className="text-center py-6">
                  <User className={`w-16 h-16 mx-auto mb-4 ${isAvatarWorld ? 'text-slate-600' : 'text-gray-400'}`} />
                  <h3 className={`text-xl font-bold mb-2 ${isAvatarWorld ? 'text-slate-800' : 'text-gray-800'}`}>
                    Profile Settings
                  </h3>
                  <p className={`mb-6 ${isAvatarWorld ? 'text-slate-600' : 'text-gray-600'}`}>
                    Profile settings are available in your profile page
                  </p>
                  <a
                    href="/profile"
                    className={`font-semibold ${isAvatarWorld ? 'text-blue-600 hover:text-blue-700' : 'text-purple-600 hover:text-purple-700'}`}
                  >
                    Go to Profile →
                  </a>
                </div>
                
                {/* Delete Account Section */}
                <div className={`border-t ${isAvatarWorld ? 'border-slate-200' : 'border-gray-200'} pt-6 mt-6`}>
                  <div className={`${isAvatarWorld ? 'bg-red-50 border-red-200' : 'bg-red-50 border-red-200'} border rounded-lg p-4`}>
                    <div className="flex items-start space-x-3">
                      <AlertTriangle className={`w-5 h-5 mt-0.5 ${isAvatarWorld ? 'text-red-600' : 'text-red-600'}`} />
                      <div className="flex-1">
                        <h4 className={`font-bold mb-1 ${isAvatarWorld ? 'text-red-800' : 'text-red-800'}`}>
                          Delete Account
                        </h4>
                        <p className={`text-sm mb-4 ${isAvatarWorld ? 'text-red-700' : 'text-red-700'}`}>
                          Once you delete your account, there is no going back. This will permanently delete your account, posts, friends, and all associated data.
                        </p>
                        <Button
                          onClick={() => setShowDeleteDialog(true)}
                          variant="destructive"
                          className={isAvatarWorld ? 'bg-red-600 hover:bg-red-700 text-white' : ''}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Delete Account
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Delete Account Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent 
          className="rounded-2xl border"
          style={{ 
            backgroundColor: isImmersive ? 'rgba(10, 15, 30, 0.98)' : '#ffffff',
            borderColor: isImmersive ? 'rgba(71, 85, 105, 0.4)' : '#e2e8f0',
          }}
        >
          <DialogHeader>
            <DialogTitle style={{ color: isImmersive ? '#e2e8f0' : '#111827' }}>
              Delete Account
            </DialogTitle>
            <DialogDescription style={{ color: isImmersive ? '#94a3b8' : undefined }}>
              This action cannot be undone. This will permanently delete your account, posts, friends, and all associated data.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm mb-4" style={{ color: isImmersive ? '#cbd5e1' : '#4b5563' }}>
              To confirm, please type <strong style={{ color: isImmersive ? '#f1f5f9' : '#1f2937' }}>DELETE</strong> in the box below:
            </p>
            <Input
              type="text"
              placeholder="Type DELETE to confirm"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              className="rounded-xl"
              style={{ 
                backgroundColor: isImmersive ? 'rgba(30, 35, 55, 0.8)' : '#ffffff',
                borderColor: isImmersive ? 'rgba(71, 85, 105, 0.5)' : '#e5e7eb',
                color: isImmersive ? '#e2e8f0' : '#1e293b',
              }}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowDeleteDialog(false);
                setDeleteConfirmText("");
              }}
              disabled={deleting}
              className={isImmersive ? 'border-slate-600 text-slate-300 hover:bg-slate-800' : ''}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteAccount}
              disabled={deleteConfirmText !== "DELETE" || deleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleting ? "Deleting..." : "Delete Account"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </ImmersivePageWrapper>
  );

  async function handleDeleteAccount() {
    if (deleteConfirmText !== "DELETE") {
      toast.error("Please type DELETE to confirm");
      return;
    }

    setDeleting(true);
    try {
      const response = await axios.delete(`${API}/auth/account`, {
        withCredentials: true
      });

      if (response.data) {
        toast.success("Account deleted successfully");
        setUser(null);
        // Clear any local storage
        localStorage.clear();
        // Redirect to landing page
        navigate("/");
      }
    } catch (error) {
      console.error("Error deleting account:", error);
      toast.error(error.response?.data?.detail || "Failed to delete account. Please try again.");
    } finally {
      setDeleting(false);
      setShowDeleteDialog(false);
      setDeleteConfirmText("");
    }
  }
};

export default SettingsPage;

