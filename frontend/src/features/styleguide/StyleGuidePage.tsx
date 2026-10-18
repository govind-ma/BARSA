import { useState } from 'react';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import {
  Flame,
  Copy,
  Check,
} from 'lucide-react';

export function StyleGuidePage() {
  const [activeTab, setActiveTab] = useState<'both' | 'ice' | 'obsidian'>('both');
  const [copied, setCopied] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <div className="min-h-screen p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-subtle">
        <div className="flex items-center space-x-4">
          <BarsaLogo size={42} />
          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="font-heading font-semibold text-2xl text-text-primary tracking-tight">
                BARSA Design System
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold tracking-wider uppercase bg-lava-orange/15 text-lava-orange border border-lava-orange/30">
                Ice & Lava
              </span>
            </div>
            <p className="text-xs text-text-muted mt-1">
              Frosted-white precision engineered with molten magma energy. Side-by-side theme specification.
            </p>
          </div>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center space-x-1 p-1 bg-surface border border-border-subtle rounded-xl shadow-xs self-start md:self-auto">
          <button
            onClick={() => setActiveTab('both')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'both'
                ? 'bg-ice-100 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Side-by-Side
          </button>
          <button
            onClick={() => setActiveTab('ice')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'ice'
                ? 'bg-ice-100 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Theme 1: ICE
          </button>
          <button
            onClick={() => setActiveTab('obsidian')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'obsidian'
                ? 'bg-ice-100 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            Theme 2: OBSIDIAN
          </button>
        </div>
      </div>

      {/* Global Lava & Magma Energy Palette */}
      <div className="glass-card p-6 space-y-4">
        <div className="flex items-center space-x-2">
          <Flame className="w-4 h-4 text-lava-orange animate-pulse" />
          <h2 className="font-heading font-semibold text-sm tracking-tight uppercase text-text-primary">
            Lava & Magma Energy Tokens (Both Themes)
          </h2>
          <span className="text-[11px] font-mono text-text-muted ml-auto">
            Strict 90/10 Ratio • Active only on primary actions & focus states
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          <Swatch
            label="Lava Yellow"
            token="--lava-yellow"
            hex="#FFC93C"
            textColor="#0D1A24"
            onCopy={copyToClipboard}
            copied={copied}
          />
          <Swatch
            label="Lava Orange"
            token="--lava-orange"
            hex="#FF7A1A"
            textColor="#FFFFFF"
            onCopy={copyToClipboard}
            copied={copied}
          />
          <Swatch
            label="Lava Red"
            token="--lava-red"
            hex="#E5301F"
            textColor="#FFFFFF"
            onCopy={copyToClipboard}
            copied={copied}
          />
          <Swatch
            label="Lava Deep"
            token="--lava-deep"
            hex="#A81414"
            textColor="#FFFFFF"
            onCopy={copyToClipboard}
            copied={copied}
          />
          <div className="col-span-2 rounded-xl p-3 border border-border-subtle bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red flex flex-col justify-between text-white shadow-sm min-h-[80px]">
            <div className="flex items-center justify-between">
              <span className="font-heading font-semibold text-xs tracking-wide">--magma</span>
              <span className="font-mono text-[10px] bg-black/30 px-1.5 py-0.5 rounded">linear-gradient</span>
            </div>
            <div className="text-[10px] font-mono text-white/90">
              135deg: #FFC93C 0% → #FF7A1A 45% → #E5301F 100%
            </div>
          </div>
        </div>
      </div>

      {/* Side-by-side theme comparison showcase */}
      <div className={`grid gap-6 ${activeTab === 'both' ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
        {/* ICE THEME COLUMN */}
        {(activeTab === 'both' || activeTab === 'ice') && (
          <div className="ice-theme-preview bg-[#F3F7FA] text-[#0D1A24] rounded-2xl p-6 border border-[rgba(110,150,180,0.30)] shadow-[0_8px_30px_rgba(60,100,130,0.08)] space-y-6">
            {/* Theme Header */}
            <div className="flex items-center justify-between border-b border-[rgba(110,150,180,0.22)] pb-4">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#6F8FA8]">
                  Default Light Mode
                </span>
                <h3 className="font-heading font-semibold text-lg text-[#0D1A24]">Theme 1: ICE</h3>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-[#E3EDF5] text-[#3E5A72] border border-[rgba(110,150,180,0.3)]">
                #F3F7FA Base
              </span>
            </div>

            {/* Ice Swatches */}
            <div className="space-y-2">
              <span className="text-[11px] font-mono uppercase text-[#7D8D99] tracking-wider block">
                Ice & Steel Neutral Palette
              </span>
              <div className="grid grid-cols-4 gap-2">
                <div className="p-2 rounded-lg bg-[#FFFFFF] border border-[rgba(110,150,180,0.22)] text-center">
                  <div className="text-[10px] font-mono font-bold text-[#0D1A24]">#FFFFFF</div>
                  <div className="text-[9px] text-[#7D8D99]">Surface</div>
                </div>
                <div className="p-2 rounded-lg bg-[#E9F0F6] border border-[rgba(110,150,180,0.22)] text-center">
                  <div className="text-[10px] font-mono font-bold text-[#0D1A24]">#E9F0F6</div>
                  <div className="text-[9px] text-[#7D8D99]">Elevated</div>
                </div>
                <div className="p-2 rounded-lg bg-[#E3EDF5] border border-[rgba(110,150,180,0.22)] text-center">
                  <div className="text-[10px] font-mono font-bold text-[#0D1A24]">#E3EDF5</div>
                  <div className="text-[9px] text-[#7D8D99]">Ice-100</div>
                </div>
                <div className="p-2 rounded-lg bg-[#6F8FA8] text-white text-center">
                  <div className="text-[10px] font-mono font-bold">#6F8FA8</div>
                  <div className="text-[9px] text-white/80">Steel-500</div>
                </div>
              </div>
            </div>

            {/* Interactive Component Specimens in Ice */}
            <div className="space-y-4">
              <span className="text-[11px] font-mono uppercase text-[#7D8D99] tracking-wider block">
                Component Specimens (Ice)
              </span>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3 items-center">
                <button className="btn-magma px-4 py-2 rounded-lg text-xs font-semibold text-white inline-flex items-center gap-2 shadow-sm">
                  <Flame className="w-3.5 h-3.5 text-lava-yellow" />
                  Primary Magma
                </button>
                <button className="px-4 py-2 rounded-lg text-xs font-medium bg-white/80 hover:bg-[#CFE0EC] text-[#0D1A24] border border-[#6F8FA8]/40 transition-all shadow-xs inline-flex items-center gap-1.5">
                  Secondary Ice
                </button>
                <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-white/70 border border-[rgba(110,150,180,0.25)]">
                  <span className="h-2 w-2 rounded-full bg-lava-orange animate-pulse" />
                  <span className="text-[11px] font-mono font-semibold text-[#0D1A24]">Live</span>
                </div>
              </div>

              {/* Molten Edge Recommended Task Card */}
              <div className="molten-card-container">
                <div className="relative z-10 bg-white/95 rounded-xl p-4 shadow-sm border border-[rgba(110,150,180,0.25)] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider text-white bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red shadow-xs">
                      Recommended
                    </span>
                    <span className="text-[10px] font-mono text-[#4A5B69] bg-[#E3EDF5] px-1.5 py-0.5 rounded">
                      Score: 270.0
                    </span>
                  </div>
                  <div className="font-heading font-semibold text-sm text-[#0D1A24]">
                    TASK-017: Cascade Knowledge Sync
                  </div>
                  <p className="text-xs text-[#4A5B69]">
                    FalkorDB rank #1 — all blockers resolved, zero outstanding dependencies.
                  </p>
                </div>
              </div>

              {/* Next Action Callout */}
              <div className="next-action-callout bg-white/80 border border-[rgba(110,150,180,0.22)] rounded-lg p-3">
                <div className="text-[10px] font-mono uppercase text-[#7D8D99]">Next Action</div>
                <div className="text-xs font-semibold text-[#0D1A24] mt-0.5">
                  Execute schema re-indexing on <span className="text-lava-orange font-bold">FalkorDB</span>
                </div>
              </div>

              {/* Toast Preview */}
              <div className="bg-white/95 border border-[rgba(110,150,180,0.3)] rounded-lg p-3 shadow-md relative overflow-hidden pl-4">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-lava-yellow to-lava-orange" />
                <div className="text-xs font-semibold text-[#0D1A24] flex items-center justify-between">
                  <span>Context copied</span>
                  <Check className="w-3.5 h-3.5 text-lava-orange" />
                </div>
                <div className="text-[11px] text-[#4A5B69] mt-0.5">
                  Ready to paste into your next agent terminal session.
                </div>
              </div>
            </div>
          </div>
        )}

        {/* OBSIDIAN THEME COLUMN */}
        {(activeTab === 'both' || activeTab === 'obsidian') && (
          <div className="dark bg-[#0C0A0B] text-[#F4F8FB] rounded-2xl p-6 border border-white/10 shadow-[0_8px_30px_rgba(0,0,0,0.6)] space-y-6">
            {/* Theme Header */}
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div>
                <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#A9B4BD]">
                  Volcanic Dark Mode
                </span>
                <h3 className="font-heading font-semibold text-lg text-[#F4F8FB]">Theme 2: OBSIDIAN</h3>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-[#151113] text-[#A9B4BD] border border-white/10">
                #0C0A0B Base
              </span>
            </div>

            {/* Obsidian Swatches */}
            <div className="space-y-2">
              <span className="text-[11px] font-mono uppercase text-[#6F7A83] tracking-wider block">
                Obsidian Volcanic Palette
              </span>
              <div className="grid grid-cols-4 gap-2">
                <div className="p-2 rounded-lg bg-[#151113] border border-white/10 text-center">
                  <div className="text-[10px] font-mono font-bold text-[#F4F8FB]">#151113</div>
                  <div className="text-[9px] text-[#6F7A83]">Surface</div>
                </div>
                <div className="p-2 rounded-lg bg-[#1E1819] border border-white/10 text-center">
                  <div className="text-[10px] font-mono font-bold text-[#F4F8FB]">#1E1819</div>
                  <div className="text-[9px] text-[#6F7A83]">Elevated</div>
                </div>
                <div className="p-2 rounded-lg bg-[#0C0A0B] border border-white/10 text-center">
                  <div className="text-[10px] font-mono font-bold text-[#F4F8FB]">#0C0A0B</div>
                  <div className="text-[9px] text-[#6F7A83]">Base</div>
                </div>
                <div className="p-2 rounded-lg bg-gradient-to-r from-lava-orange/20 to-lava-red/20 border border-lava-orange/40 text-center">
                  <div className="text-[10px] font-mono font-bold text-lava-orange">Glow</div>
                  <div className="text-[9px] text-lava-yellow">Heat Core</div>
                </div>
              </div>
            </div>

            {/* Interactive Component Specimens in Obsidian */}
            <div className="space-y-4">
              <span className="text-[11px] font-mono uppercase text-[#6F7A83] tracking-wider block">
                Component Specimens (Obsidian)
              </span>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3 items-center">
                <button className="btn-magma px-4 py-2 rounded-lg text-xs font-semibold text-white inline-flex items-center gap-2 shadow-[0_0_24px_rgba(255,122,26,0.4)]">
                  <Flame className="w-3.5 h-3.5 text-lava-yellow" />
                  Primary Magma
                </button>
                <button className="px-4 py-2 rounded-lg text-xs font-medium bg-[#1E1819] hover:bg-[#2A2224] text-[#F4F8FB] border border-white/15 transition-all shadow-xs inline-flex items-center gap-1.5">
                  Secondary Dark
                </button>
                <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-[#151113] border border-white/10">
                  <span className="h-2 w-2 rounded-full bg-lava-orange shadow-[0_0_8px_#FF7A1A] animate-pulse" />
                  <span className="text-[11px] font-mono font-semibold text-[#F4F8FB]">Live</span>
                </div>
              </div>

              {/* Molten Edge Recommended Task Card */}
              <div className="molten-card-container">
                <div className="relative z-10 bg-[#151113] rounded-xl p-4 shadow-lg border border-white/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider text-white bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red shadow-[0_0_12px_rgba(255,122,26,0.4)]">
                      Recommended
                    </span>
                    <span className="text-[10px] font-mono text-[#A9B4BD] bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
                      Score: 270.0
                    </span>
                  </div>
                  <div className="font-heading font-semibold text-sm text-[#F4F8FB]">
                    TASK-017: Cascade Knowledge Sync
                  </div>
                  <p className="text-xs text-[#A9B4BD]">
                    FalkorDB rank #1 — all blockers resolved, zero outstanding dependencies.
                  </p>
                </div>
              </div>

              {/* Next Action Callout */}
              <div className="next-action-callout bg-[#1E1819] border border-white/10 rounded-lg p-3">
                <div className="text-[10px] font-mono uppercase text-[#6F7A83]">Next Action</div>
                <div className="text-xs font-semibold text-[#F4F8FB] mt-0.5">
                  Execute schema re-indexing on <span className="text-lava-orange font-bold">FalkorDB</span>
                </div>
              </div>

              {/* Toast Preview */}
              <div className="bg-[#151113] border border-white/15 rounded-lg p-3 shadow-xl relative overflow-hidden pl-4">
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-lava-yellow to-lava-orange shadow-[0_0_8px_rgba(255,122,26,0.6)]" />
                <div className="text-xs font-semibold text-[#F4F8FB] flex items-center justify-between">
                  <span>Context copied</span>
                  <Check className="w-3.5 h-3.5 text-lava-orange" />
                </div>
                <div className="text-[11px] text-[#A9B4BD] mt-0.5">
                  Ready to paste into your next agent terminal session.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Typography & Knowledge Graph Design Reference */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Typography System */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="font-heading font-semibold text-sm tracking-tight text-text-primary uppercase">
              Typography Stack
            </h3>
            <span className="text-[10px] font-mono text-text-muted">Space Grotesk + Inter + JetBrains Mono</span>
          </div>

          <div className="space-y-4 text-text-primary">
            <div>
              <div className="text-[10px] font-mono uppercase text-text-muted mb-1">
                Headings: Space Grotesk (Weight: 600)
              </div>
              <div className="font-heading font-semibold text-xl tracking-tight">
                BARSA Multi-Agent Intelligence Engine
              </div>
            </div>

            <div>
              <div className="text-[10px] font-mono uppercase text-text-muted mb-1">
                Body: Inter (Clean, neutral readability)
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">
                Glacier ice calm with volcanic responsiveness. State synchronization between Claude, ChatGPT,
                and Antigravity occurs via FalkorDB knowledge graph and distributed checkpoints.
              </p>
            </div>

            <div>
              <div className="text-[10px] font-mono uppercase text-text-muted mb-1">
                Data & Hashes: JetBrains Mono
              </div>
              <div className="p-2.5 rounded-lg bg-surface border border-border-subtle font-mono text-xs text-text-primary flex items-center justify-between">
                <span>sha256:7f9a2b8e4c10... [CP-042]</span>
                <span className="text-lava-orange font-bold">270.0 READINESS</span>
              </div>
            </div>
          </div>
        </div>

        {/* Knowledge Graph Tokens & Semantics */}
        <div className="glass-card p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-3">
            <h3 className="font-heading font-semibold text-sm tracking-tight text-text-primary uppercase">
              Knowledge Graph Semantics
            </h3>
            <span className="text-[10px] font-mono text-text-muted">Cytoscape 2D Legend</span>
          </div>

          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex items-center space-x-2 p-2 rounded-lg bg-surface border border-border-subtle">
                <span className="w-3.5 h-3.5 rounded-full bg-steel-500 shrink-0" />
                <span className="font-medium text-text-primary">Task Node</span>
                <span className="text-[10px] text-text-muted ml-auto font-mono">Circle</span>
              </div>
              <div className="flex items-center space-x-2 p-2 rounded-lg bg-surface border border-border-subtle">
                <span className="w-3.5 h-3.5 bg-lava-yellow shrink-0 rotate-45 rounded-[2px]" />
                <span className="font-medium text-text-primary">Decision</span>
                <span className="text-[10px] text-text-muted ml-auto font-mono">Hexagon</span>
              </div>
              <div className="flex items-center space-x-2 p-2 rounded-lg bg-surface border border-border-subtle">
                <span className="w-3.5 h-3.5 rounded-sm bg-ice-300 dark:bg-steel-500 shrink-0" />
                <span className="font-medium text-text-primary">Capability</span>
                <span className="text-[10px] text-text-muted ml-auto font-mono">Square</span>
              </div>
              <div className="flex items-center space-x-2 p-2 rounded-lg bg-surface border border-border-subtle">
                <span className="w-3.5 h-3.5 bg-lava-orange rotate-45 shrink-0" />
                <span className="font-medium text-text-primary">Agent</span>
                <span className="text-[10px] text-text-muted ml-auto font-mono">Diamond</span>
              </div>
              <div className="flex items-center space-x-2 p-2 rounded-lg bg-surface border border-border-subtle">
                <span className="w-3.5 h-3.5 rounded-full bg-lava-red shrink-0" />
                <span className="font-medium text-text-primary">Issue</span>
                <span className="text-[10px] text-text-muted ml-auto font-mono">Red Circle</span>
              </div>
              <div className="flex items-center space-x-2 p-2 rounded-lg bg-surface border border-lava-orange/40">
                <span className="w-3.5 h-3.5 rounded-full bg-gradient-to-r from-lava-yellow to-lava-red shadow-[0_0_8px_#FF7A1A] shrink-0" />
                <span className="font-semibold text-text-primary">Recommended</span>
                <span className="text-[10px] text-lava-orange ml-auto font-mono font-bold">Halo</span>
              </div>
            </div>

            {/* Edge line styles */}
            <div className="pt-2 border-t border-border-subtle space-y-2">
              <span className="text-[10px] font-mono uppercase text-text-muted block">Edge Relationships</span>
              <div className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between text-text-secondary">
                  <span className="font-mono text-[11px]">DEPENDS_ON</span>
                  <span className="h-0.5 w-32 bg-ice-300 dark:bg-steel-500 rounded" />
                  <span className="text-[10px] text-text-muted">Solid ice line</span>
                </div>
                <div className="flex items-center justify-between text-text-secondary">
                  <span className="font-mono text-[11px] text-lava-red">BLOCKED_BY</span>
                  <span className="h-0.5 w-32 border-b-2 border-dashed border-lava-red" />
                  <span className="text-[10px] text-lava-red">Dashed lava line</span>
                </div>
                <div className="flex items-center justify-between text-text-secondary">
                  <span className="font-mono text-[11px]">REQUIRES</span>
                  <span className="h-0.5 w-32 border-b-2 border-dotted border-steel-500" />
                  <span className="text-[10px] text-text-muted">Dotted steel line</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

interface SwatchProps {
  label: string;
  token: string;
  hex: string;
  textColor: string;
  onCopy: (text: string, id: string) => void;
  copied: string | null;
}

function Swatch({ label, token, hex, textColor, onCopy, copied }: SwatchProps) {
  const isCopied = copied === token;

  return (
    <div
      onClick={() => onCopy(hex, token)}
      className="group relative cursor-pointer rounded-xl p-3 border border-border-subtle transition-all duration-150 hover:shadow-md flex flex-col justify-between min-h-[80px]"
      style={{ backgroundColor: hex, color: textColor }}
    >
      <div className="flex items-center justify-between">
        <span className="font-heading font-semibold text-xs tracking-tight">{label}</span>
        {isCopied ? (
          <Check className="w-3.5 h-3.5 text-white bg-black/40 rounded p-0.5" />
        ) : (
          <Copy className="w-3 h-3 opacity-0 group-hover:opacity-80 transition-opacity" />
        )}
      </div>
      <div className="space-y-0.5">
        <div className="text-[10px] font-mono font-bold opacity-90">{hex}</div>
        <div className="text-[9px] font-mono opacity-70">{token}</div>
      </div>
    </div>
  );
}
