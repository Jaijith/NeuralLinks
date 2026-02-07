import { Globe, Sparkles } from "lucide-react";
import { useWorldMode } from "@/contexts/WorldModeContext";
import useViewMode from "@/hooks/useViewMode";

const WorldModeToggle = ({ className = "" }) => {
  const { worldMode, toggleWorldMode } = useWorldMode();
  const { isImmersive } = useViewMode();
  const isAvatar = worldMode === 'avatar';
  const isDark = isAvatar && isImmersive;

  const handleClick = (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
      e.nativeEvent?.stopImmediatePropagation?.();
    }
    toggleWorldMode();
  };

  return (
    <div 
      className={`relative ${className}`} 
      style={{ 
        zIndex: 9999,
        position: 'relative',
        isolation: 'isolate',
      }}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
      }}
      onTouchStart={(e) => e.stopPropagation()}
      onTouchEnd={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        onClick={handleClick}
        onTouchEnd={(e) => {
          e.preventDefault();
          e.stopPropagation();
          handleClick(e);
        }}
        style={{
          position: 'relative',
          overflow: 'hidden',
          padding: '7px 14px',
          borderRadius: '9999px',
          fontWeight: '600',
          fontSize: '12px',
          letterSpacing: '0.01em',
          transition: 'all 0.3s ease',
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: '72px',
          minHeight: '36px',
          touchAction: 'manipulation',
          WebkitTapHighlightColor: 'transparent',
          userSelect: 'none',
          zIndex: 9999,
          background: isAvatar
            ? (isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)')
            : (isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.08)'),
          color: isAvatar
            ? (isDark ? '#c4b5fd' : '#7c3aed')
            : (isDark ? '#93c5fd' : '#2563eb'),
          border: `1.5px solid ${isAvatar
            ? (isDark ? 'rgba(139, 92, 246, 0.3)' : 'rgba(139, 92, 246, 0.25)')
            : (isDark ? 'rgba(59, 130, 246, 0.3)' : 'rgba(59, 130, 246, 0.2)')}`,
          boxShadow: 'none',
        }}
        data-testid="world-mode-toggle"
        aria-label={`Switch to ${isAvatar ? 'Sense' : 'Maya'} world`}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          {isAvatar ? (
            <>
              <Sparkles style={{ width: '14px', height: '14px' }} />
              <span>Maya</span>
            </>
          ) : (
            <>
              <Globe style={{ width: '14px', height: '14px' }} />
              <span>Sense</span>
            </>
          )}
        </div>
      </button>
    </div>
  );
};

export default WorldModeToggle;
