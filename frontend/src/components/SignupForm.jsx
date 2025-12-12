import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Mail, User, CheckCircle, Loader2 } from "lucide-react";
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
  const [status, setStatus] = useState(null);

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
      <div className="w-full max-w-md mx-auto">
        <div className="text-center space-y-4">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 rounded-full flex items-center justify-center ring-2 ring-cyan-400/30">
            <CheckCircle className="w-8 h-8 text-cyan-400" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-white mb-2">Request Submitted!</h3>
            <p className="text-gray-400 text-sm mb-6">
              Your signup request has been sent for approval. You'll receive an email at <span className="text-cyan-400 font-medium">{formData.email}</span> once it's reviewed.
            </p>
            <Button
              onClick={checkStatus}
              variant="outline"
              className="border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 hover:border-cyan-400/50"
            >
              Check Status
            </Button>
            {status === 'approved' && (
              <div className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                <p className="text-green-400 text-sm font-medium">
                  ✓ Your request has been approved! You can now log in.
                </p>
              </div>
            )}
            {status === 'pending' && (
              <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                <p className="text-amber-400 text-sm">
                  ⏳ Your request is still pending approval.
                </p>
              </div>
            )}
            {status === 'rejected' && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                <p className="text-red-400 text-sm">
                  ✗ Your request was not approved. Please contact support.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Header */}
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">
          Join 2N1
        </h2>
        <p className="text-gray-400 text-sm">
          Request access to create your avatar
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Full Name
          </label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="text"
              placeholder="Enter your name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
              className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Email Address
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
            <input
              type="email"
              placeholder="your.email@example.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              className="w-full pl-10 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 transition-colors"
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            You'll use this email to log in with Google after approval
          </p>
        </div>

        <Button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold py-6 rounded-lg shadow-lg shadow-cyan-500/25 hover:shadow-cyan-500/40 transition-all"
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

        <div className="text-center pt-2">
          <button
            type="button"
            onClick={onSwitchToLogin}
            className="text-sm text-gray-400 hover:text-cyan-400 transition-colors"
          >
            Already approved? <span className="text-cyan-400 hover:underline">Log in with Google</span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default SignupForm;
