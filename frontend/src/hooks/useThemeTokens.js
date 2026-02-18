/**
 * useThemeTokens - Provides mode-aware design tokens for components
 * 
 * Returns a `t` object with all design tokens based on current mode:
 * - Sense Classic (default light mode)
 * - Maya Classic (avatar world light mode)
 * - Maya Immersive (avatar world dark mode)
 * 
 * Usage:
 *   const { t, isImmersive, isAvatarWorld } = useThemeTokens();
 *   <div style={{ background: t.cardBg, color: t.textPrimary }}>
 */

import { useMemo } from 'react';
import { useWorldMode } from '@/contexts/WorldModeContext';
import useViewMode from '@/hooks/useViewMode';

export function useThemeTokens() {
  const { worldMode } = useWorldMode();
  const { isImmersive } = useViewMode();
  const isAvatarWorld = worldMode === 'avatar';

  const t = useMemo(() => {
    if (isAvatarWorld && isImmersive) {
      // Maya Immersive - dark cosmic theme
      return {
        // Backgrounds
        pageBg: 'transparent',
        cardBg: 'rgba(15, 23, 42, 0.85)',
        cardBgHover: 'rgba(15, 23, 42, 0.95)',
        cardBgSubtle: 'rgba(15, 23, 42, 0.6)',
        inputBg: 'rgba(30, 41, 59, 0.8)',
        dialogBg: 'rgba(10, 15, 30, 0.98)',
        sidebarBg: 'rgba(15, 23, 42, 0.9)',
        hoverBg: 'rgba(255, 255, 255, 0.08)',
        activeBg: 'rgba(255, 255, 255, 0.12)',

        // Text
        textPrimary: 'rgba(255, 255, 255, 0.9)',
        textSecondary: '#e2e8f0',
        textMuted: '#94a3b8',
        textOnAccent: '#ffffff',
        textLink: '#a78bfa',
        textLinkHover: '#c4b5fd',

        // Semantic text
        textSuccess: '#6ee7b7',
        textWarning: '#fde047',
        textError: '#fca5a5',
        textInfo: '#93c5fd',
        textPurple: '#c4b5fd',

        // Borders
        borderDefault: 'rgba(51, 65, 85, 0.5)',
        borderSubtle: 'rgba(255, 255, 255, 0.1)',
        borderFocus: 'rgba(139, 92, 246, 0.5)',
        borderAccent: 'rgba(139, 92, 246, 0.3)',

        // Accents
        accentPrimary: '#8b5cf6',
        accentSecondary: '#6366f1',
        accentGradientFrom: '#ec4899',
        accentGradientTo: '#8b5cf6',

        // Shadows
        shadowSm: '0 2px 8px rgba(0, 0, 0, 0.3)',
        shadowMd: '0 4px 20px rgba(0, 0, 0, 0.3)',
        shadowLg: '0 8px 32px rgba(0, 0, 0, 0.4)',

        // Pastel background tints (for badges/tags)
        bgYellow: 'rgba(234, 179, 8, 0.15)',
        bgPurple: 'rgba(139, 92, 246, 0.15)',
        bgGreen: 'rgba(16, 185, 129, 0.15)',
        bgRed: 'rgba(239, 68, 68, 0.15)',
        bgBlue: 'rgba(59, 130, 246, 0.15)',
        bgGray: 'rgba(255, 255, 255, 0.05)',
      };
    }

    if (isAvatarWorld) {
      // Maya Classic - light professional theme
      return {
        // Backgrounds
        pageBg: 'bg-gradient-to-br from-blue-50 via-white to-slate-50',
        cardBg: 'rgba(255, 255, 255, 0.95)',
        cardBgHover: 'rgba(255, 255, 255, 1)',
        cardBgSubtle: 'rgba(255, 255, 255, 0.8)',
        inputBg: 'rgba(255, 255, 255, 0.95)',
        dialogBg: '#ffffff',
        sidebarBg: 'rgba(255, 255, 255, 0.95)',
        hoverBg: 'rgba(0, 0, 0, 0.04)',
        activeBg: 'rgba(0, 0, 0, 0.06)',

        // Text
        textPrimary: '#111827',
        textSecondary: '#374151',
        textMuted: '#6b7280',
        textOnAccent: '#ffffff',
        textLink: '#2563eb',
        textLinkHover: '#1d4ed8',

        // Semantic text
        textSuccess: '#059669',
        textWarning: '#d97706',
        textError: '#dc2626',
        textInfo: '#2563eb',
        textPurple: '#7c3aed',

        // Borders
        borderDefault: 'rgba(0, 0, 0, 0.08)',
        borderSubtle: 'rgba(0, 0, 0, 0.04)',
        borderFocus: 'rgba(59, 130, 246, 0.5)',
        borderAccent: 'rgba(59, 130, 246, 0.3)',

        // Accents
        accentPrimary: '#3b82f6',
        accentSecondary: '#8b5cf6',
        accentGradientFrom: '#ec4899',
        accentGradientTo: '#8b5cf6',

        // Shadows
        shadowSm: '0 1px 4px rgba(0, 0, 0, 0.06)',
        shadowMd: '0 2px 12px rgba(0, 0, 0, 0.08)',
        shadowLg: '0 4px 24px rgba(0, 0, 0, 0.1)',

        // Pastel backgrounds (native light pastels)
        bgYellow: '#fef9c3',
        bgPurple: '#f3e8ff',
        bgGreen: '#dcfce7',
        bgRed: '#fef2f2',
        bgBlue: '#dbeafe',
        bgGray: '#f9fafb',
      };
    }

    // Sense Classic - default light mode
    return {
      // Backgrounds
      pageBg: 'bg-gradient-to-br from-blue-50 via-white to-slate-50',
      cardBg: 'rgba(255, 255, 255, 0.7)',
      cardBgHover: 'rgba(255, 255, 255, 0.9)',
      cardBgSubtle: 'rgba(255, 255, 255, 0.5)',
      inputBg: '#ffffff',
      dialogBg: '#ffffff',
      sidebarBg: 'rgba(255, 255, 255, 0.8)',
      hoverBg: 'rgba(0, 0, 0, 0.04)',
      activeBg: 'rgba(0, 0, 0, 0.06)',

      // Text
      textPrimary: '#111827',
      textSecondary: '#374151',
      textMuted: '#6b7280',
      textOnAccent: '#ffffff',
      textLink: '#7c3aed',
      textLinkHover: '#6d28d9',

      // Semantic text
      textSuccess: '#059669',
      textWarning: '#d97706',
      textError: '#dc2626',
      textInfo: '#2563eb',
      textPurple: '#7c3aed',

      // Borders
      borderDefault: 'rgba(0, 0, 0, 0.1)',
      borderSubtle: 'rgba(0, 0, 0, 0.05)',
      borderFocus: 'rgba(124, 58, 237, 0.5)',
      borderAccent: 'rgba(124, 58, 237, 0.3)',

      // Accents
      accentPrimary: '#7c3aed',
      accentSecondary: '#ec4899',
      accentGradientFrom: '#ec4899',
      accentGradientTo: '#8b5cf6',

      // Shadows
      shadowSm: '0 1px 4px rgba(0, 0, 0, 0.06)',
      shadowMd: '0 2px 12px rgba(0, 0, 0, 0.08)',
      shadowLg: '0 4px 24px rgba(0, 0, 0, 0.1)',

      // Pastel backgrounds
      bgYellow: '#fef9c3',
      bgPurple: '#f3e8ff',
      bgGreen: '#dcfce7',
      bgRed: '#fef2f2',
      bgBlue: '#dbeafe',
      bgGray: '#f9fafb',
    };
  }, [isAvatarWorld, isImmersive]);

  return { t, isImmersive, isAvatarWorld };
}

export default useThemeTokens;
