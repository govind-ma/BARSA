import React from 'react';

interface EmberSparksProps {
  count?: number;
  className?: string;
}

export const EmberSparks: React.FC<EmberSparksProps> = ({ count = 5, className = '' }) => {
  // Pre-configured particles with random positions, delays, and durations
  const sparks = React.useMemo(() => {
    return Array.from({ length: count }, (_, i) => ({
      id: i,
      left: `${15 + (i * 18) % 70}%`,
      bottom: `${5 + (i * 12) % 25}%`,
      delay: `${(i * 0.7) % 3.5}s`,
      duration: `${3 + (i * 0.5) % 2}s`,
      size: `${2 + (i % 3)}px`,
      color: i % 2 === 0 ? '#FF7A1A' : '#FFC93C',
    }));
  }, [count]);

  return (
    <div
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      {sparks.map((spark) => (
        <span
          key={spark.id}
          className="absolute rounded-full animate-emberRise opacity-0"
          style={{
            left: spark.left,
            bottom: spark.bottom,
            width: spark.size,
            height: spark.size,
            backgroundColor: spark.color,
            boxShadow: `0 0 6px ${spark.color}`,
            animationDelay: spark.delay,
            animationDuration: spark.duration,
          }}
        />
      ))}
    </div>
  );
};
