import { useEffect, useState } from 'react';

interface CrystalBurstProps {
  onComplete?: () => void;
}

export function CrystalBurst({ onComplete }: CrystalBurstProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 1000);
    return () => clearTimeout(timer);
  }, [onComplete]);

  if (!visible) return null;

  // 8 radial ice shard vectors
  const shards = [
    { x: 0, y: -28, rot: 0, delay: '0ms' },
    { x: 20, y: -20, rot: 45, delay: '40ms' },
    { x: 28, y: 0, rot: 90, delay: '80ms' },
    { x: 20, y: 20, rot: 135, delay: '120ms' },
    { x: 0, y: 28, rot: 180, delay: '160ms' },
    { x: -20, y: 20, rot: 225, delay: '200ms' },
    { x: -28, y: 0, rot: 270, delay: '240ms' },
    { x: -20, y: -20, rot: 315, delay: '280ms' },
  ];

  // A few tiny rising ember sparks
  const embers = [
    { x: -12, y: -10, size: 3, delay: '50ms' },
    { x: 8, y: -18, size: 2.5, delay: '150ms' },
    { x: 14, y: 6, size: 2, delay: '220ms' },
    { x: -6, y: 12, size: 3.5, delay: '300ms' },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-30 overflow-visible">
      <div className="relative w-8 h-8 flex items-center justify-center">
        {/* Central burst glow */}
        <div className="absolute w-14 h-14 rounded-full bg-lava-orange/40 blur-lg animate-ping" />

        {/* Radiating ice shards */}
        {shards.map((s, i) => (
          <div
            key={`shard-${i}`}
            className="absolute transition-all duration-700 ease-out animate-crystal-burst"
            style={{
              transform: `translate(${s.x * 1.6}px, ${s.y * 1.6}px) rotate(${s.rot}deg)`,
              animationDelay: s.delay,
            }}
          >
            {/* Ice faceted shard polygon */}
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <polygon points="6,0 12,6 6,12 0,6" fill="#CFE0EC" stroke="#6F8FA8" strokeWidth="1" />
            </svg>
          </div>
        ))}

        {/* Tiny ember sparks */}
        {embers.map((e, idx) => (
          <div
            key={`ember-${idx}`}
            className="absolute rounded-full animate-emberRise"
            style={{
              left: `calc(50% + ${e.x}px)`,
              top: `calc(50% + ${e.y}px)`,
              width: `${e.size}px`,
              height: `${e.size}px`,
              backgroundColor: '#FF7A1A',
              boxShadow: '0 0 8px #FF7A1A',
              animationDelay: e.delay,
            }}
          />
        ))}
      </div>
    </div>
  );
}
