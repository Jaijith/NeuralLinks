import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Mail, User, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SignupForm = ({ onSignupSuccess, onSwitchToLogin }) => {
  const [formData, setFormData] = useState({
    email: "",
    name: "",
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [status, setStatus] = useState(null); // 'pending', 'approved', 'rejected'

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/signup/request`, formData);
      
      if (response.data) {
        setSubmitted(true);
        setStatus('pending');
        toast.success("Signup request submitted! You'll receive an email once approved.");
        
        if (onSignupSuccess) {
          onSignupSuccess(response.data);
        }
      }
    } catch (error) {
      if (error.response?.status === 400) {
        const message = error.response.data?.detail || "An error occurred";
        toast.error(message);
      } else {
        toast.error("Failed to submit signup request. Please try again.");
      }
      console.error("Signup error:", error);
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async () => {
    if (!formData.email) return;
    
    try {
      const response = await axios.get(`${API}/signup/status/${encodeURIComponent(formData.email)}`);
      if (response.data) {
        setStatus(response.data.status);
        if (response.data.status === 'approved') {
          toast.success("Your request has been approved! You can now log in.");
        }
      }
    } catch (error) {
      console.error("Status check error:", error);
    }
  };

  if (submitted) {
    return (
      <Card className="w-full max-w-md mx-auto glass-morphism border-purple-400/30">
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-purple-300" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white mb-2">Request Submitted!</h3>
              <p className="text-purple-200 text-sm mb-4">
                Your signup request has been sent for approval. You'll receive an email at <strong>{formData.email}</strong> once it's reviewed.
              </p>
              <Button
                onClick={checkStatus}
                variant="outline"
                className="border-purple-400/50 text-purple-200 hover:bg-purple-500/20 mb-4"
              >
                Check Status
              </Button>
              {status === 'approved' && (
                <div className="mt-4 p-3 bg-green-500/20 border border-green-400/30 rounded-lg">
                  <p className="text-green-300 text-sm font-semibold">
                    ✓ Your request has been approved! You can now log in.
                  </p>
                </div>
              )}
              {status === 'pending' && (
                <div className="mt-4 p-3 bg-yellow-500/20 border border-yellow-400/30 rounded-lg">
                  <p className="text-yellow-300 text-sm">
                    ⏳ Your request is still pending approval.
                  </p>
                </div>
              )}
              {status === 'rejected' && (
                <div className="mt-4 p-3 bg-red-500/20 border border-red-400/30 rounded-lg">
                  <p className="text-red-300 text-sm">
                    ✗ Your request was not approved. Please contact support.
                  </p>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md mx-auto glass-morphism border-purple-400/30">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-white text-center">
          Join Maya
        </CardTitle>
        <p className="text-purple-200 text-sm text-center mt-2">
          Request access to create your avatar
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-purple-200 mb-2">
              Full Name
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-purple-300" />
              <Input
                type="text"
                placeholder="Enter your name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="pl-10 bg-white/10 border-purple-400/30 text-white placeholder:text-purple-300/50 focus:border-purple-400"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-purple-200 mb-2">
              Email Address
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-purple-300" />
              <Input
                type="email"
                placeholder="your.email@example.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="pl-10 bg-white/10 border-purple-400/30 text-white placeholder:text-purple-300/50 focus:border-purple-400"
              />
            </div>
            <p className="text-xs text-purple-300/70 mt-1">
              You'll use this email to log in with Google after approval
            </p>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-purple-500 via-pink-500 to-indigo-600 hover:from-purple-600 hover:via-pink-600 hover:to-indigo-700 text-white font-bold py-6 rounded-lg shadow-xl transform hover:scale-105 transition-all"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              "Request Access"
            )}
          </Button>

          <div className="text-center">
            <button
              type="button"
              onClick={onSwitchToLogin}
              className="text-sm text-purple-300 hover:text-purple-200 underline"
            >
              Already approved? Log in with Google
            </button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default SignupForm;

