import React from 'react';

interface BarsaLogoProps {
  size?: number;
  className?: string;
  showWordmark?: boolean;
}

export const BarsaLogo: React.FC<BarsaLogoProps> = ({
  size = 32,
  className = '',
  showWordmark = false,
}) => {
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      {/* Faceted Ice Crystal with Flame Core */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform duration-300 hover:scale-105"
      >
        <defs>
          <linearGradient id="barsaFlameCore" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFC93C" />
            <stop offset="50%" stopColor="#FF7A1A" />
            <stop offset="100%" stopColor="#E5301F" />
          </linearGradient>
          <linearGradient id="barsaIceFacet1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#CFE0EC" stopOpacity="0.65" />
          </linearGradient>
          <linearGradient id="barsaIceFacet2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#E3EDF5" stopOpacity="0.85" />
            <stop offset="100%" stopColor="#B3CDE0" stopOpacity="0.55" />
          </linearGradient>
          <filter id="barsaCoreGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Faceted Ice Hexagon */}
        <polygon points="50,6 88,28 50,50" fill="url(#barsaIceFacet1)" stroke="#6F8FA8" strokeWidth="1.5" strokeLinejoin="round" />
        <polygon points="88,28 88,72 50,50" fill="url(#barsaIceFacet2)" stroke="#6F8FA8" strokeWidth="1.5" strokeLinejoin="round" />
        <polygon points="88,72 50,94 50,50" fill="url(#barsaIceFacet1)" stroke="#6F8FA8" strokeWidth="1.5" strokeLinejoin="round" />
        <polygon points="50,94 12,72 50,50" fill="url(#barsaIceFacet2)" stroke="#6F8FA8" strokeWidth="1.5" strokeLinejoin="round" />
        <polygon points="12,72 12,28 50,50" fill="url(#barsaIceFacet1)" stroke="#6F8FA8" strokeWidth="1.5" strokeLinejoin="round" />
        <polygon points="12,28 50,6 50,50" fill="url(#barsaIceFacet2)" stroke="#6F8FA8" strokeWidth="1.5" strokeLinejoin="round" />

        {/* Outer Perimeter */}
        <polygon points="50,6 88,28 88,72 50,94 12,72 12,28" fill="none" stroke="#6F8FA8" strokeWidth="2.5" strokeLinejoin="round" />

        {/* Flame Core */}
        <polygon points="50,26 68,50 50,74 32,50" fill="url(#barsaFlameCore)" filter="url(#barsaCoreGlow)" />
        <polygon points="50,34 60,50 50,66 40,50" fill="#FFC93C" />
        <circle cx="50" cy="50" r="3.5" fill="#FFFFFF" opacity="0.95" />
      </svg>

      {/* Wordmark "BARSA" in Space Grotesk 600, with "BRAIN" small in mono */}
      {showWordmark && (
        <div className="flex items-baseline gap-1.5 select-none">
          <span className="font-heading font-semibold text-lg tracking-tight text-text-primary">
            BARSA
          </span>
          <span className="font-mono text-[10px] tracking-widest uppercase font-medium text-text-muted bg-ice-100 dark:bg-white/[0.08] px-1.5 py-0.5 rounded border border-border-subtle">
            BRAIN
          </span>
        </div>
      )}
    </div>
  );
};
