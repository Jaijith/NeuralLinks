import { Button } from "@/components/ui/button";
import { Globe, Sparkles } from "lucide-react";
import { useWorldMode } from "@/contexts/WorldModeContext";

const WorldModeToggle = ({ className = "" }) => {
  const { worldMode, toggleWorldMode } = useWorldMode();

  return (
    <div className={`relative ${className}`}>
      <Button
        onClick={toggleWorldMode}
        className={`
          relative overflow-hidden px-6 py-6 rounded-full font-bold text-sm
          transition-all duration-500 ease-in-out
          ${worldMode === 'avatar' 
            ? 'bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 text-white shadow-lg shadow-blue-500/50 hover:shadow-blue-500/70' 
            : 'bg-gradient-to-r from-pink-500 to-purple-600 text-white shadow-lg hover:shadow-xl'
          }
        `}
        data-testid="world-mode-toggle"
      >
        <div className="flex items-center space-x-2">
          {worldMode === 'avatar' ? (
            <>
              <Sparkles className="w-5 h-5 animate-pulse" />
              <span>Maya</span>
            </>
          ) : (
            <>
              <Globe className="w-5 h-5" />
              <span>Sense</span>
            </>
          )}
        </div>
        
        {worldMode === 'avatar' && (
          <div className="absolute inset-0 overflow-hidden">
            <div className="absolute w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-[shimmer_2s_infinite]" 
                 style={{transform: 'translateX(-100%)'}} />
          </div>
        )}
      </Button>
      
      <style>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
      `}</style>
    </div>
  );
};

export default WorldModeToggle;
