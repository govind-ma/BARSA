import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';

interface CrystalBurstProps {
  onComplete?: () => void;
}

export function CrystalBurst({ onComplete }: CrystalBurstProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 900);
    return () => clearTimeout(timer);
  }, [onComplete]);

  if (!visible) return null;

  // 8 radial crystal points
  const crystals = [
    { x: 0, y: -24, rot: 0, delay: '0ms' },
    { x: 17, y: -17, rot: 45, delay: '50ms' },
    { x: 24, y: 0, rot: 90, delay: '100ms' },
    { x: 17, y: 17, rot: 135, delay: '150ms' },
    { x: 0, y: 24, rot: 180, delay: '200ms' },
    { x: -17, y: 17, rot: 225, delay: '250ms' },
    { x: -24, y: 0, rot: 270, delay: '300ms' },
    { x: -17, y: -17, rot: 315, delay: '350ms' },
  ];

  return (
    <div className="absolute inset-0 pointer-events-none flex items-center justify-center z-30 overflow-visible">
      <div className="relative w-8 h-8 flex items-center justify-center">
        {/* Central burst glow */}
        <div className="absolute w-12 h-12 rounded-full bg-ice/40 blur-md animate-ping" />

        {/* Radiating crystal sparkles */}
        {crystals.map((c, i) => (
          <div
            key={i}
            className="absolute transition-all duration-700 ease-out animate-pulse"
            style={{
              transform: `translate(${c.x * 1.5}px, ${c.y * 1.5}px) rotate(${c.rot}deg)`,
              opacity: 0.9,
              animationDelay: c.delay,
            }}
          >
            <Sparkles className="h-3.5 w-3.5 text-ice drop-shadow-[0_0_8px_rgba(56,189,248,0.9)]" />
          </div>
        ))}
      </div>
    </div>
  );
}
