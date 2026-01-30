/**
 * VoiceSettings - Voice configuration panel
 * 
 * Allows users to customize voice interaction settings:
 * - Environment presets
 * - Noise sensitivity
 * - Response preferences
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getVoiceSettings, updateVoiceSettings } from '../../services/api/voiceService';

const VoiceSettings = ({ isOpen, onClose, colors }) => {
  const [settings, setSettings] = useState({
    preset: 'default',
    noise_threshold: 0.5,
    response_speed: 'balanced',
    prefer_shorter_responses: false,
    enable_transcription: true
  });
  const [presets, setPresets] = useState(['default']);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  
  // Load settings
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const data = await getVoiceSettings();
        if (data.success) {
          setSettings(prev => ({ ...prev, ...data.settings }));
          setPresets(data.presets || ['default']);
        }
      } catch (err) {
        console.error('Error loading voice settings:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    if (isOpen) {
      loadSettings();
    }
  }, [isOpen]);
  
  // Save settings
  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus(null);
    
    try {
      const result = await updateVoiceSettings({
        preset: settings.preset,
        custom: {
          noise_threshold: settings.noise_threshold,
          response_speed: settings.response_speed,
          prefer_shorter_responses: settings.prefer_shorter_responses,
          enable_transcription: settings.enable_transcription
        }
      });
      
      if (result.success) {
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus(null), 2000);
      } else {
        setSaveStatus('error');
      }
    } catch (err) {
      console.error('Error saving voice settings:', err);
      setSaveStatus('error');
    } finally {
      setIsSaving(false);
    }
  };
  
  // Preset descriptions
  const presetDescriptions = {
    default: 'Balanced settings for most environments',
    low_latency: 'Fast response time for natural conversations',
    ultra_low_latency: 'Fastest possible - may be sensitive to noise',
    quiet_environment: 'Higher sensitivity for quiet rooms',
    noisy_environment: 'Filters background noise better',
    push_to_talk: 'Manual control - hold to speak'
  };
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="fixed inset-0 bg-black/60 z-[300]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          
          {/* Settings panel */}
          <motion.div
            className="fixed bottom-0 left-0 right-0 sm:bottom-auto sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 sm:w-[480px] z-[301] rounded-t-2xl sm:rounded-2xl overflow-hidden"
            style={{
              background: 'linear-gradient(to bottom, rgba(30,30,40,0.98), rgba(20,20,30,0.98))',
              border: `1px solid ${colors?.primary || '#60a5fa'}30`,
              maxHeight: '90vh'
            }}
            initial={{ opacity: 0, y: 100 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 100 }}
          >
            {/* Header */}
            <div 
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: `${colors?.primary || '#60a5fa'}20` }}
            >
              <h2 className="text-lg font-semibold text-white">Voice Settings</h2>
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 transition-colors"
              >
                <span className="text-white/60 text-xl">&times;</span>
              </button>
            </div>
            
            {/* Content */}
            <div className="p-4 space-y-6 overflow-y-auto max-h-[60vh]">
              {isLoading ? (
                <div className="text-center py-8 text-white/50">Loading...</div>
              ) : (
                <>
                  {/* Environment Preset */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      Environment Preset
                    </label>
                    <div className="grid grid-cols-1 gap-2">
                      {presets.map((preset) => (
                        <button
                          key={preset}
                          onClick={() => setSettings(prev => ({ ...prev, preset }))}
                          className={`p-3 rounded-lg text-left transition-all ${
                            settings.preset === preset 
                              ? 'ring-2' 
                              : 'hover:bg-white/5'
                          }`}
                          style={{
                            background: settings.preset === preset 
                              ? `${colors?.primary || '#60a5fa'}15` 
                              : 'rgba(255,255,255,0.03)',
                            borderColor: settings.preset === preset 
                              ? colors?.primary 
                              : 'transparent',
                            ringColor: colors?.primary
                          }}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-white capitalize">
                              {preset.replace(/_/g, ' ')}
                            </span>
                            {settings.preset === preset && (
                              <span style={{ color: colors?.primary }}>✓</span>
                            )}
                          </div>
                          <p className="text-xs text-white/50 mt-1">
                            {presetDescriptions[preset] || 'Custom preset'}
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Noise Sensitivity */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      Noise Sensitivity
                    </label>
                    <div className="flex items-center gap-4">
                      <span className="text-xs text-white/50">Quiet</span>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={settings.noise_threshold}
                        onChange={(e) => setSettings(prev => ({ 
                          ...prev, 
                          noise_threshold: parseFloat(e.target.value) 
                        }))}
                        className="flex-1 h-2 rounded-full appearance-none cursor-pointer"
                        style={{
                          background: `linear-gradient(to right, ${colors?.primary || '#60a5fa'} ${settings.noise_threshold * 100}%, rgba(255,255,255,0.2) ${settings.noise_threshold * 100}%)`
                        }}
                      />
                      <span className="text-xs text-white/50">Noisy</span>
                    </div>
                    <p className="text-xs text-white/40 mt-1">
                      Higher values filter out more background noise
                    </p>
                  </div>
                  
                  {/* Response Speed */}
                  <div>
                    <label className="block text-sm font-medium text-white/80 mb-2">
                      Response Speed
                    </label>
                    <div className="flex gap-2">
                      {['quick', 'balanced', 'thoughtful'].map((speed) => (
                        <button
                          key={speed}
                          onClick={() => setSettings(prev => ({ ...prev, response_speed: speed }))}
                          className={`flex-1 py-2 px-3 rounded-lg text-sm transition-all ${
                            settings.response_speed === speed 
                              ? 'text-white' 
                              : 'text-white/60 hover:text-white/80'
                          }`}
                          style={{
                            background: settings.response_speed === speed 
                              ? `${colors?.primary || '#60a5fa'}30` 
                              : 'rgba(255,255,255,0.05)',
                            border: `1px solid ${settings.response_speed === speed ? colors?.primary : 'transparent'}`
                          }}
                        >
                          {speed.charAt(0).toUpperCase() + speed.slice(1)}
                        </button>
                      ))}
                    </div>
                  </div>
                  
                  {/* Toggle options */}
                  <div className="space-y-3">
                    {/* Shorter responses */}
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-white/80">Prefer shorter responses</p>
                        <p className="text-xs text-white/40">More concise answers</p>
                      </div>
                      <button
                        onClick={() => setSettings(prev => ({ 
                          ...prev, 
                          prefer_shorter_responses: !prev.prefer_shorter_responses 
                        }))}
                        className={`w-12 h-6 rounded-full transition-colors relative ${
                          settings.prefer_shorter_responses ? '' : 'bg-white/20'
                        }`}
                        style={{
                          background: settings.prefer_shorter_responses ? colors?.primary : undefined
                        }}
                      >
                        <span 
                          className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                            settings.prefer_shorter_responses ? 'translate-x-7' : 'translate-x-1'
                          }`} 
                        />
                      </button>
                    </div>
                    
                    {/* Transcription */}
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-white/80">Show transcription</p>
                        <p className="text-xs text-white/40">Display text of conversation</p>
                      </div>
                      <button
                        onClick={() => setSettings(prev => ({ 
                          ...prev, 
                          enable_transcription: !prev.enable_transcription 
                        }))}
                        className={`w-12 h-6 rounded-full transition-colors relative ${
                          settings.enable_transcription ? '' : 'bg-white/20'
                        }`}
                        style={{
                          background: settings.enable_transcription ? colors?.primary : undefined
                        }}
                      >
                        <span 
                          className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                            settings.enable_transcription ? 'translate-x-7' : 'translate-x-1'
                          }`} 
                        />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
            
            {/* Footer */}
            <div 
              className="p-4 border-t flex items-center justify-between"
              style={{ borderColor: `${colors?.primary || '#60a5fa'}20` }}
            >
              {saveStatus && (
                <span className={`text-sm ${saveStatus === 'saved' ? 'text-green-400' : 'text-red-400'}`}>
                  {saveStatus === 'saved' ? '✓ Saved' : '✗ Error saving'}
                </span>
              )}
              <div className="flex gap-2 ml-auto">
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-lg text-sm text-white/60 hover:text-white hover:bg-white/10 transition-all min-h-[44px]"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSave}
                  disabled={isSaving}
                  className="px-6 py-2 rounded-lg text-sm text-white transition-all min-h-[44px] disabled:opacity-50"
                  style={{
                    background: colors?.primary || '#60a5fa'
                  }}
                >
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default VoiceSettings;
