import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Settings, Link2, Eye, User } from "lucide-react";
import IntegrationsPage from "./IntegrationsPage";
import AvatarVisualization from "./AvatarVisualization";

const SettingsPage = ({ user }) => {
  const [activeTab, setActiveTab] = useState("integrations");

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-2">
            <Settings className="w-8 h-8 text-purple-600" />
            <h1 className="text-4xl font-bold gradient-text">Settings</h1>
          </div>
          <p className="text-gray-600">Manage your integrations and view your avatar's knowledge graph</p>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-6">
            <TabsTrigger value="integrations" className="flex items-center justify-center space-x-2">
              <Link2 className="w-4 h-4" />
              <span>Integrations</span>
            </TabsTrigger>
            <TabsTrigger value="avatar" className="flex items-center justify-center space-x-2">
              <Eye className="w-4 h-4" />
              <span>Avatar Visualization</span>
            </TabsTrigger>
            <TabsTrigger value="profile" className="flex items-center justify-center space-x-2">
              <User className="w-4 h-4" />
              <span>Profile</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="integrations" className="mt-0">
            <IntegrationsPage user={user} hideHeader={true} />
          </TabsContent>

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

          <TabsContent value="profile" className="mt-0">
            <Card className="glass-morphism p-6">
              <div className="text-center py-12">
                <User className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-gray-800 mb-2">Profile Settings</h3>
                <p className="text-gray-600 mb-6">
                  Profile settings are available in your profile page
                </p>
                <a
                  href="/profile"
                  className="text-purple-600 hover:text-purple-700 font-semibold"
                >
                  Go to Profile →
                </a>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default SettingsPage;

