import { Button } from "@/components/ui/button";
import { Heart, Sparkles, Users, MessageCircle, Brain, Zap } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const REDIRECT_URL = window.location.origin + "/dashboard";

const LandingPage = ({ setUser }) => {
  const handleLogin = () => {
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(
      REDIRECT_URL
    )}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-50 via-purple-50 to-indigo-50 overflow-hidden">
      {/* Floating Elements */}
      <div className="absolute top-20 left-10 w-32 h-32 bg-pink-200 rounded-full opacity-20 blur-3xl floating-animation"></div>
      <div className="absolute bottom-20 right-10 w-40 h-40 bg-purple-200 rounded-full opacity-20 blur-3xl floating-animation" style={{ animationDelay: "2s" }}></div>
      <div className="absolute top-1/2 left-1/4 w-24 h-24 bg-indigo-200 rounded-full opacity-20 blur-3xl floating-animation" style={{ animationDelay: "4s" }}></div>

      {/* Header */}
      <header className="relative z-10 px-6 py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Heart className="w-6 h-6 text-white fill-white" />
            </div>
            <h1 className="text-2xl font-bold gradient-text">AI Match</h1>
          </div>
          <Button
            onClick={handleLogin}
            data-testid="header-login-btn"
            className="bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white px-6 py-2 rounded-full font-medium"
          >
            Sign In
          </Button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-20 pb-32">
        <div className="text-center fade-in">
          <div className="inline-flex items-center space-x-2 bg-white/60 backdrop-blur-sm border border-purple-200 rounded-full px-4 py-2 mb-6">
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span className="text-sm text-purple-700 font-medium">AI-Powered Dating</span>
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
            <span className="gradient-text">Let AI Find</span>
            <br />
            <span className="text-gray-800">Your Perfect Match</span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-600 max-w-2xl mx-auto mb-10 leading-relaxed">
            Your AI agent chats with potential matches while you live your life. Get validated, high-quality connections ready for real conversations.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              onClick={handleLogin}
              data-testid="hero-get-started-btn"
              className="btn-primary text-white px-8 py-6 rounded-full text-lg font-semibold shadow-lg"
            >
              <Heart className="w-5 h-5 mr-2" />
              Get Started Free
            </Button>
            <Button
              variant="outline"
              data-testid="hero-learn-more-btn"
              className="border-2 border-purple-300 text-purple-700 hover:bg-purple-50 px-8 py-6 rounded-full text-lg font-semibold"
            >
              <Brain className="w-5 h-5 mr-2" />
              How It Works
            </Button>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-3 gap-6 mt-24">
          <div className="glass-morphism p-8 rounded-3xl card-hover fade-in" style={{ animationDelay: "0.2s" }} data-testid="feature-card-ai-agents">
            <div className="w-14 h-14 bg-gradient-to-br from-pink-400 to-pink-600 rounded-2xl flex items-center justify-center mb-4">
              <Users className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-xl font-bold text-gray-800 mb-3">AI Agents Chat First</h3>
            <p className="text-gray-600 leading-relaxed">
              Your personal AI agent represents you, chatting with other AI agents to find genuine compatibility.
            </p>
          </div>

          <div className="glass-morphism p-8 rounded-3xl card-hover fade-in" style={{ animationDelay: "0.4s" }} data-testid="feature-card-graph-rag">
            <div className="w-14 h-14 bg-gradient-to-br from-purple-400 to-purple-600 rounded-2xl flex items-center justify-center mb-4">
              <Brain className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-xl font-bold text-gray-800 mb-3">Graph RAG Learning</h3>
            <p className="text-gray-600 leading-relaxed">
              Advanced knowledge graphs continuously learn about you, making smarter matches over time.
            </p>
          </div>

          <div className="glass-morphism p-8 rounded-3xl card-hover fade-in" style={{ animationDelay: "0.6s" }} data-testid="feature-card-validated-matches">
            <div className="w-14 h-14 bg-gradient-to-br from-indigo-400 to-indigo-600 rounded-2xl flex items-center justify-center mb-4">
              <MessageCircle className="w-7 h-7 text-white" />
            </div>
            <h3 className="text-xl font-bold text-gray-800 mb-3">Validated Matches</h3>
            <p className="text-gray-600 leading-relaxed">
              Only see profiles that AI has validated for compatibility. Start real conversations that matter.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="relative z-10 bg-white/40 backdrop-blur-sm py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl sm:text-5xl font-bold gradient-text mb-4">How It Works</h2>
            <p className="text-lg text-gray-600">Four simple steps to AI-powered dating</p>
          </div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              { icon: Brain, title: "Create Profile", desc: "Chat with your AI to build a rich profile" },
              { icon: Sparkles, title: "AI Agents Connect", desc: "Your agent chats with potential matches" },
              { icon: Zap, title: "Get Scores", desc: "Receive compatibility scores & insights" },
              { icon: Heart, title: "Start Chatting", desc: "Connect with validated matches" },
            ].map((step, idx) => (
              <div key={idx} className="text-center fade-in" style={{ animationDelay: `${idx * 0.1}s` }}>
                <div className="w-20 h-20 bg-gradient-to-br from-pink-400 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
                  <step.icon className="w-10 h-10 text-white" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 mb-2">{step.title}</h3>
                <p className="text-gray-600">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-4xl sm:text-5xl font-bold mb-6">
            <span className="gradient-text">Ready to Find</span>
            <br />
            <span className="text-gray-800">Your AI-Validated Match?</span>
          </h2>
          <p className="text-lg text-gray-600 mb-8">
            Join thousands using AI agents to find meaningful connections
          </p>
          <Button
            onClick={handleLogin}
            data-testid="cta-get-started-btn"
            className="btn-primary text-white px-10 py-6 rounded-full text-lg font-semibold shadow-2xl"
          >
            <Heart className="w-5 h-5 mr-2" />
            Start Your Journey
          </Button>
        </div>
      </section>
    </div>
  );
};

export default LandingPage;
