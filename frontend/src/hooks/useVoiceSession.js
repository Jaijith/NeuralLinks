/**
 * useVoiceSession - Hook for managing real-time voice sessions
 * 
 * Handles WebRTC connection to OpenAI Realtime API for speech-to-speech
 * communication with minimal latency.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { createVoiceSession, recordVoiceEvent, getVoiceContext, prewarmContext, saveTranscript, triggerWorkflow } from '../services/api/voiceService';

// Generate unique ID for session (uses crypto if available, fallback to timestamp)
const generateSessionId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback: timestamp + random
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

// Session states
export const VoiceSessionState = {
  IDLE: 'idle',
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  LISTENING: 'listening',
  SPEAKING: 'speaking',
  ERROR: 'error',
  DISCONNECTED: 'disconnected'
};

/**
 * Hook for managing voice sessions with OpenAI Realtime API
 * 
 * @param {Object} options - Configuration options
 * @param {string} options.avatarId - Avatar ID for session
 * @param {string} options.settingPreset - Voice setting preset
 * @param {Function} options.onTranscript - Callback for transcripts
 * @param {Function} options.onStateChange - Callback for state changes
 * @param {Function} options.onError - Callback for errors
 */
export function useVoiceSession({
  avatarId,
  settingPreset = 'default',
  onTranscript,
  onStateChange,
  onError
} = {}) {
  const [sessionState, setSessionState] = useState(VoiceSessionState.IDLE);
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [aiTranscript, setAiTranscript] = useState('');
  const [error, setError] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);
  
  // Refs for WebRTC components
  const peerConnectionRef = useRef(null);
  const dataChannelRef = useRef(null);
  const localStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sessionStartTimeRef = useRef(null);
  const animationFrameRef = useRef(null);
  
  // Refs for transcript accumulation
  const sessionIdRef = useRef(null);
  const messagesRef = useRef([]);
  const currentUserTranscriptRef = useRef('');
  const currentAiTranscriptRef = useRef('');
  
  // Update state and notify callback
  const updateState = useCallback((newState) => {
    setSessionState(newState);
    onStateChange?.(newState);
    
    if (newState === VoiceSessionState.LISTENING) {
      setIsListening(true);
      setIsSpeaking(false);
    } else if (newState === VoiceSessionState.SPEAKING) {
      setIsSpeaking(true);
      setIsListening(false);
    } else if (newState === VoiceSessionState.CONNECTED) {
      setIsListening(true);
    }
  }, [onStateChange]);
  
  // Handle data channel messages from OpenAI
  const handleDataChannelMessage = useCallback((event) => {
    try {
      const message = JSON.parse(event.data);
      
      switch (message.type) {
        case 'session.created':
          console.log('Voice session created:', message.session?.id);
          updateState(VoiceSessionState.CONNECTED);
          break;
          
        case 'input_audio_buffer.speech_started':
          updateState(VoiceSessionState.LISTENING);
          break;
          
        case 'input_audio_buffer.speech_stopped':
          // User stopped speaking, waiting for response
          break;
          
        // GA API event names
        case 'response.output_audio_transcript.delta':
        case 'response.audio_transcript.delta':  // Keep for backwards compatibility
          // AI is speaking - accumulate transcript
          setAiTranscript(prev => prev + (message.delta || ''));
          updateState(VoiceSessionState.SPEAKING);
          break;
          
        case 'response.output_audio_transcript.done':
        case 'response.audio_transcript.done':  // Keep for backwards compatibility
          // AI finished speaking - save to transcript history
          const fullTranscript = message.transcript || '';
          setAiTranscript(fullTranscript);
          onTranscript?.({ type: 'ai', text: fullTranscript });
          
          // Accumulate for saving
          if (fullTranscript.trim()) {
            messagesRef.current.push({
              role: 'assistant',
              content: fullTranscript,
              timestamp: new Date().toISOString()
            });
          }
          
          updateState(VoiceSessionState.CONNECTED);
          break;
          
        case 'conversation.item.input_audio_transcription.completed':
          // User speech transcription - save to transcript history
          const userText = message.transcript || '';
          setTranscript(userText);
          onTranscript?.({ type: 'user', text: userText });
          
          // Accumulate for saving
          if (userText.trim()) {
            messagesRef.current.push({
              role: 'user',
              content: userText,
              timestamp: new Date().toISOString()
            });
          }
          break;
          
        case 'response.done':
          // Response complete
          setAiTranscript('');
          updateState(VoiceSessionState.CONNECTED);
          break;
          
        case 'response.output_item.added':
        case 'response.output_item.done':
          // GA API uses these for response items
          console.debug('Response output item:', message.type);
          break;
          
        case 'conversation.item.added':
        case 'conversation.item.done':
          // GA API conversation item events
          console.debug('Conversation item:', message.type);
          break;
          
        case 'response.function_call_arguments.done':
          // AI wants to call a function - handle it
          handleFunctionCall(message);
          break;
          
        case 'error':
          console.error('Voice session error:', message.error);
          setError(message.error?.message || 'Voice session error');
          onError?.(message.error);
          break;
          
        default:
          // Log other messages for debugging
          console.debug('Voice message:', message.type);
      }
    } catch (err) {
      console.error('Error parsing data channel message:', err);
    }
  }, [onTranscript, onError, updateState]);
  
  // Handle function calls from the AI
  const handleFunctionCall = useCallback(async (message) => {
    const { call_id, name, arguments: argsString } = message;
    
    try {
      const args = JSON.parse(argsString || '{}');
      console.log(`AI calling function: ${name}`, args);
      
      let result;
      
      if (name === 'recall_social_context') {
        // Handle social context recall
        result = await getVoiceContext({
          avatarId,
          contextType: args.context_type,
          friendName: args.friend_name,
          timeRange: args.time_range
        });
        
        // Send function result back to the AI
        if (dataChannelRef.current && dataChannelRef.current.readyState === 'open') {
          const outputEvent = {
            type: 'conversation.item.create',
            item: {
              type: 'function_call_output',
              call_id: call_id,
              output: result.summary || 'No information available.'
            }
          };
          dataChannelRef.current.send(JSON.stringify(outputEvent));
          dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
        }
        
      } else if (name === 'trigger_workflow') {
        // Handle workflow trigger
        console.log('Triggering workflow:', args);
        
        result = await triggerWorkflow({
          avatarId,
          missionType: args.mission_type,
          missionName: args.mission_name,
          description: args.description,
          interests: args.interests || [],
          keywords: args.keywords || [],
          approach: args.approach || 'friendly',
          maxTargets: args.max_targets || 10
        });
        
        // Send function result back to the AI
        if (dataChannelRef.current && dataChannelRef.current.readyState === 'open') {
          const outputMessage = result.success 
            ? `${result.message} Mission ID: ${result.mission_id}`
            : result.message;
          
          const outputEvent = {
            type: 'conversation.item.create',
            item: {
              type: 'function_call_output',
              call_id: call_id,
              output: outputMessage
            }
          };
          dataChannelRef.current.send(JSON.stringify(outputEvent));
          dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
        }
        
      } else {
        console.warn('Unknown function call:', name);
        // Send error result for unknown function
        if (dataChannelRef.current && dataChannelRef.current.readyState === 'open') {
          const errorEvent = {
            type: 'conversation.item.create',
            item: {
              type: 'function_call_output',
              call_id: call_id,
              output: "I don't know how to do that right now."
            }
          };
          dataChannelRef.current.send(JSON.stringify(errorEvent));
          dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
        }
      }
      
    } catch (err) {
      console.error('Error handling function call:', err);
      
      // Send error result back to AI
      if (dataChannelRef.current && dataChannelRef.current.readyState === 'open') {
        const errorEvent = {
          type: 'conversation.item.create',
          item: {
            type: 'function_call_output',
            call_id: call_id,
            output: "I'm having trouble with that right now. Could you try again?"
          }
        };
        dataChannelRef.current.send(JSON.stringify(errorEvent));
        dataChannelRef.current.send(JSON.stringify({ type: 'response.create' }));
      }
    }
  }, [avatarId]);
  
  // Analyze audio levels for visualization
  const analyzeAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    setAudioLevel(average / 255); // Normalize to 0-1
    
    animationFrameRef.current = requestAnimationFrame(analyzeAudioLevel);
  }, []);
  
  // Start voice session
  const startSession = useCallback(async () => {
    if (sessionState !== VoiceSessionState.IDLE && sessionState !== VoiceSessionState.DISCONNECTED) {
      console.warn('Session already active or connecting');
      return;
    }
    
    try {
      setError(null);
      updateState(VoiceSessionState.CONNECTING);
      
      // Initialize session tracking
      sessionIdRef.current = generateSessionId();
      messagesRef.current = [];
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,  // Near-field noise removal
          autoGainControl: true,
          sampleRate: 24000
        }
      });
      localStreamRef.current = stream;
      
      // Set up audio analysis for visualization
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      
      // Start audio level monitoring
      analyzeAudioLevel();
      
      // Get ephemeral token from backend
      const sessionData = await createVoiceSession({
        avatarId,
        settingPreset
      });
      
      if (!sessionData.success || !sessionData.ephemeral_token) {
        throw new Error(sessionData.error || 'Failed to create voice session');
      }
      
      // Create WebRTC peer connection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });
      peerConnectionRef.current = pc;
      
      // Add local audio track
      stream.getTracks().forEach(track => {
        pc.addTrack(track, stream);
      });
      
      // Handle remote audio (AI voice)
      pc.ontrack = (event) => {
        const audio = new Audio();
        audio.srcObject = event.streams[0];
        audio.autoplay = true;
      };
      
      // Create data channel for events
      const dc = pc.createDataChannel('oai-events');
      dataChannelRef.current = dc;
      
      dc.onopen = () => {
        console.log('Data channel opened');
        sessionStartTimeRef.current = Date.now();
        recordVoiceEvent('session_started', {
          avatar_id: avatarId,
          timestamp: new Date().toISOString()
        });
      };
      
      dc.onmessage = handleDataChannelMessage;
      
      dc.onerror = (err) => {
        console.error('Data channel error:', err);
        setError('Connection error');
        onError?.(err);
      };
      
      dc.onclose = () => {
        console.log('Data channel closed');
        updateState(VoiceSessionState.DISCONNECTED);
      };
      
      // Create and set local description
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      // Send offer to OpenAI Realtime API (GA endpoint)
      const response = await fetch('https://api.openai.com/v1/realtime/calls', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${sessionData.ephemeral_token}`,
          'Content-Type': 'application/sdp'
        },
        body: offer.sdp
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`WebRTC connection failed: ${response.status} - ${errorText}`);
      }
      
      const answerSdp = await response.text();
      await pc.setRemoteDescription({
        type: 'answer',
        sdp: answerSdp
      });
      
      setIsConnected(true);
      updateState(VoiceSessionState.CONNECTED);
      
      console.log('Voice session connected successfully');
      
    } catch (err) {
      console.error('Error starting voice session:', err);
      setError(err.message);
      updateState(VoiceSessionState.ERROR);
      onError?.(err);
      
      // Cleanup on error
      cleanup();
    }
  }, [avatarId, settingPreset, sessionState, handleDataChannelMessage, analyzeAudioLevel, onError, updateState]);
  
  // Stop voice session
  const stopSession = useCallback(async () => {
    const endTime = new Date().toISOString();
    const startTime = sessionStartTimeRef.current 
      ? new Date(sessionStartTimeRef.current).toISOString()
      : endTime;
    const duration = sessionStartTimeRef.current 
      ? Math.floor((Date.now() - sessionStartTimeRef.current) / 1000)
      : 0;
    
    // Record session end
    try {
      await recordVoiceEvent('session_ended', {
        avatar_id: avatarId,
        timestamp: endTime,
        duration_seconds: duration
      });
    } catch (err) {
      console.error('Error recording session end:', err);
    }
    
    // Save transcript to backend (fire-and-forget)
    // Only save if we have messages and a meaningful conversation (>10s)
    if (messagesRef.current.length > 0 && duration > 10) {
      saveTranscript({
        sessionId: sessionIdRef.current,
        avatarId: avatarId,
        messages: messagesRef.current,
        startedAt: startTime,
        endedAt: endTime,
        durationSeconds: duration
      });
      console.log(`Saved transcript: ${messagesRef.current.length} messages, ${duration}s`);
    }
    
    // Clear session data
    sessionIdRef.current = null;
    messagesRef.current = [];
    
    cleanup();
    updateState(VoiceSessionState.IDLE);
  }, [avatarId, updateState]);
  
  // Cleanup resources
  const cleanup = useCallback(() => {
    // Stop animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    
    // Close data channel
    if (dataChannelRef.current) {
      dataChannelRef.current.close();
      dataChannelRef.current = null;
    }
    
    // Close peer connection
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }
    
    // Stop local stream
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
      localStreamRef.current = null;
    }
    
    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    setIsConnected(false);
    setIsSpeaking(false);
    setIsListening(false);
    setAudioLevel(0);
  }, []);
  
  // Send text message (for hybrid text/voice mode)
  const sendMessage = useCallback((text) => {
    if (!dataChannelRef.current || dataChannelRef.current.readyState !== 'open') {
      console.warn('Data channel not open');
      return;
    }
    
    // Send user message event (GA API format)
    const event = {
      type: 'conversation.item.create',
      item: {
        type: 'message',
        role: 'user',
        content: [{ type: 'input_text', text }]
      }
    };
    
    dataChannelRef.current.send(JSON.stringify(event));
    
    // Request response (GA API)
    dataChannelRef.current.send(JSON.stringify({ 
      type: 'response.create'
    }));
  }, []);
  
  // Interrupt AI response
  const interrupt = useCallback(() => {
    if (!dataChannelRef.current || dataChannelRef.current.readyState !== 'open') {
      return;
    }
    
    dataChannelRef.current.send(JSON.stringify({ type: 'response.cancel' }));
  }, []);
  
  // Pre-warm context (call on hover over orb)
  const prewarm = useCallback(async () => {
    if (!avatarId) return;
    
    try {
      console.log('Pre-warming voice context...');
      await prewarmContext(avatarId);
      console.log('Context pre-warmed');
    } catch (err) {
      // Silently fail - this is just optimization
      console.debug('Pre-warm failed:', err);
    }
  }, [avatarId]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);
  
  return {
    // State
    sessionState,
    isConnected,
    isSpeaking,
    isListening,
    transcript,
    aiTranscript,
    error,
    audioLevel,
    
    // Actions
    startSession,
    stopSession,
    sendMessage,
    interrupt,
    prewarm
  };
}

export default useVoiceSession;
