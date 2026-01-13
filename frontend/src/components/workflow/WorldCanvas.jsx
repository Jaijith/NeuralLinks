/**
 * WorldCanvas Component
 * A living visualization of the social/knowledge world
 * Shows entities as nodes, interactions as edges, with ambient motion
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Stable positioning for nodes - no continuous animation to prevent flickering
const useStablePositions = (nodes, width, height) => {
  const [positions, setPositions] = useState({});
  const initializedRef = useRef(new Set());
  
  useEffect(() => {
    if (!nodes.length || !width || !height) return;
    
    const centerX = width / 2;
    const centerY = height / 2;
    
    setPositions(prev => {
      const newPos = { ...prev };
      
      nodes.forEach((node, i) => {
        // Only initialize position once per node
        if (!initializedRef.current.has(node.id)) {
          initializedRef.current.add(node.id);
          
          if (node.isUserAvatar) {
            // User avatar at center
            newPos[node.id] = { x: centerX, y: centerY };
          } else {
            // Other nodes in a circle around center
            const otherNodes = nodes.filter(n => !n.isUserAvatar);
            const idx = otherNodes.findIndex(n => n.id === node.id);
            const total = otherNodes.length;
            const angle = (2 * Math.PI * idx) / Math.max(total, 1) - Math.PI / 2;
            
            // Radius based on signal strength - high signal closer to center
            const baseRadius = Math.min(width, height) * 0.3;
            const signalRadius = baseRadius * (1.2 - (node.signal || 0.5) * 0.5);
            
            newPos[node.id] = {
              x: centerX + Math.cos(angle) * signalRadius,
              y: centerY + Math.sin(angle) * signalRadius,
            };
          }
        }
      });
      
      return newPos;
    });
  }, [nodes, width, height]);
  
  // Clean up removed nodes
  useEffect(() => {
    const currentIds = new Set(nodes.map(n => n.id));
    initializedRef.current.forEach(id => {
      if (!currentIds.has(id)) {
        initializedRef.current.delete(id);
      }
    });
  }, [nodes]);
  
  return positions;
};

const WorldCanvas = ({
  entities = [],
  interactions = [],
  phase = 'idle', // idle, initializing, exploring, interacting, detecting, stabilizing
  focusedEntity = null,
  onEntityClick,
  onEntityHover,
  avatarPosition = null,
  missionActive = false,
  className = '',
}) => {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState(null);
  
  // Track container size
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };
    
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);
  
  // Convert entities to nodes
  const nodes = entities.map(e => ({
    id: e.id,
    label: e.name || e.avatar_name || 'Unknown',
    type: e.type || 'avatar',
    signal: e.signal || e.score / 100 || 0.5,
    picture: e.picture || e.avatar_picture,
    isAvatar: e.isUserAvatar,
    ...e,
  }));
  
  // Get stable node positions
  const positions = useStablePositions(nodes, dimensions.width, dimensions.height);
  
  // Phase-based visual modifiers
  const getPhaseStyles = () => {
    switch (phase) {
      case 'initializing':
        return { filter: 'brightness(1.1)', transition: 'filter 0.5s' };
      case 'exploring':
        return { filter: 'brightness(1.05) saturate(1.1)', transition: 'filter 0.5s' };
      case 'interacting':
        return { filter: 'brightness(1.0) saturate(1.2)', transition: 'filter 0.5s' };
      case 'detecting':
        return { filter: 'brightness(1.15) contrast(1.1)', transition: 'filter 0.5s' };
      case 'stabilizing':
        return { filter: 'brightness(1.0)', transition: 'filter 1s' };
      default:
        return {};
    }
  };
  
  const getNodeSize = (node) => {
    let base = 40;
    if (node.isAvatar) base = 56;
    if (node.signal > 0.8) base *= 1.3;
    if (focusedEntity === node.id) base *= 1.2;
    return base;
  };
  
  const getNodeGlow = (node) => {
    if (node.isAvatar) return 'rgba(168, 85, 247, 0.6)'; // Purple-500
    if (node.signal > 0.8) return 'rgba(236, 72, 153, 0.5)'; // Pink-500
    if (node.signal > 0.6) return 'rgba(192, 132, 252, 0.4)'; // Purple-400
    return 'rgba(167, 139, 250, 0.2)'; // Purple-300
  };

  return (
    <div 
      ref={containerRef}
      className={`relative w-full h-full overflow-hidden rounded-2xl border border-purple-200 shadow-lg ${className}`}
      style={{
        background: 'linear-gradient(135deg, #EEF2FF 0%, #FFFFFF 50%, #F8FAFC 100%)',
        ...getPhaseStyles(),
      }}
    >
      {/* Subtle gradient overlay */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(168, 85, 247, 0.05) 0%, transparent 60%)',
        }}
      />
      
      {/* Grid background for depth */}
      <svg className="absolute inset-0 w-full h-full opacity-30">
        <defs>
          <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(168, 85, 247, 0.15)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
      </svg>
      
      {/* Subtle ambient particles - fewer and slower */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(6)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 rounded-full"
            style={{
              background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.25) 0%, rgba(236, 72, 153, 0.2) 100%)',
            }}
            initial={{ 
              x: (i * dimensions.width / 6) + Math.random() * 50,
              y: Math.random() * dimensions.height,
              opacity: 0.4 
            }}
            animate={{
              y: [null, Math.random() * dimensions.height],
              opacity: [0.3, 0.6, 0.3],
            }}
            transition={{
              duration: 20 + i * 3,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ))}
      </div>
      
      {/* Edges / Connections */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        <defs>
          <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(168, 85, 247, 0.6)" />
            <stop offset="100%" stopColor="rgba(236, 72, 153, 0.6)" />
          </linearGradient>
        </defs>
        {interactions.map((edge, i) => {
          const fromPos = positions[edge.from];
          const toPos = positions[edge.to];
          if (!fromPos || !toPos) return null;
          
          const isActive = phase === 'interacting' && edge.active;
          
          return (
            <g key={i}>
              <line
                x1={fromPos.x}
                y1={fromPos.y}
                x2={toPos.x}
                y2={toPos.y}
                stroke={isActive ? 'url(#edgeGradient)' : 'rgba(168, 85, 247, 0.15)'}
                strokeWidth={isActive ? 2 : 1}
                strokeDasharray={isActive ? 'none' : '4 4'}
              />
              {/* Pulse along edge during interaction */}
              {isActive && (
                <motion.circle
                  r="3"
                  fill="rgba(236, 72, 153, 0.8)"
                  initial={{ cx: fromPos.x, cy: fromPos.y }}
                  animate={{
                    cx: [fromPos.x, toPos.x],
                    cy: [fromPos.y, toPos.y],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: 'linear',
                  }}
                />
              )}
            </g>
          );
        })}
      </svg>
      
      {/* Nodes */}
      <AnimatePresence>
        {nodes.map(node => {
          const pos = positions[node.id];
          if (!pos) return null;
          
          const size = getNodeSize(node);
          const glow = getNodeGlow(node);
          const isHovered = hoveredNode === node.id;
          const isFocused = focusedEntity === node.id;
          
          return (
            <motion.div
              key={node.id}
              className="absolute cursor-pointer"
              style={{
                left: pos.x,
                top: pos.y,
                transform: 'translate(-50%, -50%)',
                zIndex: isFocused ? 20 : isHovered ? 15 : 10,
              }}
              initial={{ scale: 0, opacity: 0 }}
              animate={{ 
                scale: 1, 
                opacity: 1,
              }}
              exit={{ scale: 0, opacity: 0 }}
              whileHover={{ scale: 1.15 }}
              onClick={() => onEntityClick?.(node)}
              onMouseEnter={() => {
                setHoveredNode(node.id);
                onEntityHover?.(node);
              }}
              onMouseLeave={() => {
                setHoveredNode(null);
                onEntityHover?.(null);
              }}
            >
              {/* Glow effect */}
              <div
                className="absolute rounded-full transition-all duration-1000"
                style={{
                  width: size * 1.4,
                  height: size * 1.4,
                  left: '50%',
                  top: '50%',
                  transform: 'translate(-50%, -50%)',
                  background: glow,
                  filter: 'blur(15px)',
                  opacity: node.signal > 0.7 ? 0.7 : 0.4,
                }}
              />
              
              {/* Avatar/Icon */}
              <div
                className={`relative rounded-full overflow-hidden border-2 shadow-lg ${
                  node.isAvatar ? 'border-purple-400 ring-2 ring-purple-400/30' : 
                  node.signal > 0.7 ? 'border-pink-400' : 'border-purple-500/30'
                }`}
                style={{ width: size, height: size }}
              >
                {node.picture ? (
                  <img 
                    src={node.picture} 
                    alt={node.label}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className={`w-full h-full flex items-center justify-center text-white font-bold ${
                    node.isAvatar ? 'bg-gradient-to-br from-purple-500 to-pink-500' :
                    'bg-gradient-to-br from-purple-600/80 to-pink-600/80'
                  }`}>
                    {node.label?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                )}
              </div>
              
              {/* Label */}
              {(isHovered || isFocused) && (
                <motion.div
                  className="absolute left-1/2 -translate-x-1/2 mt-2 px-3 py-1.5 bg-white border border-purple-200 rounded-lg text-xs text-gray-800 whitespace-nowrap shadow-lg"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {node.label}
                  {node.signal > 0.7 && (
                    <span className="ml-1 text-pink-500">★</span>
                  )}
                </motion.div>
              )}
              
              {/* Signal indicator for high-signal nodes */}
              {node.signal > 0.7 && (
                <motion.div
                  className="absolute -top-1 -right-1 w-4 h-4 bg-gradient-to-br from-pink-500 to-purple-500 rounded-full border-2 border-white shadow-lg"
                  animate={{ scale: [1, 1.15, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
      
      {/* Phase indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 text-xs bg-white/80 px-3 py-1.5 rounded-full border border-purple-100 shadow-sm">
        <div className={`w-2 h-2 rounded-full ${
          missionActive ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
        }`} />
        <span className="text-gray-600 uppercase tracking-wider font-medium">
          {phase === 'idle' ? 'World Online' : phase}
        </span>
      </div>
      
      {/* Entity count */}
      <div className="absolute bottom-4 right-4 text-xs text-gray-500 bg-white/80 px-3 py-1.5 rounded-full border border-purple-100 shadow-sm">
        {nodes.length} entities • {interactions.length} connections
      </div>
      
      {/* Empty state */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-500">
          <motion.div
            className="w-24 h-24 rounded-full border-2 border-dashed border-purple-300"
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          />
          <p className="mt-4 text-sm font-medium text-gray-600">World is listening...</p>
          <p className="text-xs text-gray-400">Start a mission to populate the canvas</p>
        </div>
      )}
    </div>
  );
};

export default WorldCanvas;

