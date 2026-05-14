'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { PulseLogo } from '@/components/shell/PulseLogo';
import type { ForecastResponse } from '@/lib/types';

const COOKIE = 'gc_onboarding_done';
const STEP_KEY = 'gc_tutorial_step';
const TOTAL_STEPS = 8;

function markSeen() {
  document.cookie = `${COOKIE}=1; max-age=31536000; path=/; SameSite=Lax`;
}

function fmtMw(mw: number): string {
  return mw >= 1000 ? `${Math.round(mw / 1000)}k` : `${Math.round(mw)}`;
}

// ─── Step bodies ──────────────────────────────────────────────────────────────

function Step0() {
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 18 }}>
        GridCast monitors US electricity transmission nodes in real time, giving
        co-located AI data centres a 10-day ahead view of grid stress and the
        optimal power-allocation % to draw safely.
      </p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 9 }}>
        {[
          'Forecast grid stress up to 10 days ahead',
          'Prevent costly curtailments before they hit',
          'Optimise your power-allocation % automatically',
          'Balance demand against available supply in real time',
        ].map((item) => (
          <li key={item} style={{ display: 'flex', alignItems: 'flex-start', gap: 9, fontSize: 12, color: '#6B7280' }}>
            <span style={{
              marginTop: 4, width: 5, height: 5, borderRadius: '50%',
              background: '#0F3D56', flexShrink: 0, display: 'block',
            }} />
            {item}
          </li>
        ))}
      </ul>
    </>
  );
}

function Step1() {
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 16 }}>
        You&apos;re currently seeing every US transmission node tracked by EIA.
        GridCast actively forecasts four high-priority hubs for AI data-centre operators.
      </p>
      <div style={{
        background: 'oklch(0.97 0.01 230)',
        border: '1px solid rgba(15,61,86,0.18)',
        borderRadius: 8,
        padding: '10px 14px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 10,
      }}>
        <span style={{ fontSize: 16, marginTop: 1, flexShrink: 0 }}>↗</span>
        <p style={{ margin: 0, fontSize: 12, color: '#0F3D56', lineHeight: 1.6 }}>
          Click <strong>Target Grids → On</strong> in the top-right header,
          or hit <strong>Show me</strong> below and we&apos;ll do it for you.
        </p>
      </div>
    </>
  );
}

function Step2() {
  const nodes = [
    { name: 'ERCOT Houston', iso: 'ERCOT', region: 'Texas' },
    { name: 'Dominion Hub', iso: 'PJM', region: 'Mid-Atlantic' },
    { name: 'CAISO SP15', iso: 'CAISO', region: 'S. California' },
    { name: 'CAISO NP15', iso: 'CAISO', region: 'N. California' },
  ];
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 14 }}>
        These four hubs sit at the intersection of high grid stress and major AI
        infrastructure build-out. GridCast provides each with a 10-day stress
        forecast and a recommended power-allocation %.
      </p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {nodes.map((n) => (
          <li key={n.name} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '7px 10px', borderRadius: 6,
            background: '#F7F8FA', border: '1px solid #ECEEF2',
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#0B0F19' }}>{n.name}</span>
            <span style={{
              fontSize: 10, color: '#6B7280',
              fontFamily: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
            }}>
              {n.iso} · {n.region}
            </span>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 12, lineHeight: 1.6 }}>
        Click any of the four nodes on the map to explore its forecast.
        Or hit <strong style={{ color: '#6B7280' }}>Continue</strong> and we&apos;ll open ERCOT Houston for you.
      </p>
    </>
  );
}

function StepAllocation({ forecast }: { forecast: ForecastResponse | null }) {
  if (!forecast) return null;
  const { pct, pct_p50, pct_p10, p90_stress_fraction } = forecast.allocation;
  const stressFrac = Math.round(p90_stress_fraction * 100);
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 14 }}>
        GridCast currently recommends drawing{' '}
        <strong style={{ color: '#0B0F19' }}>{pct}%</strong> of available capacity —
        constrained by a <strong style={{ color: '#0B0F19' }}>{stressFrac}% P90 stress fraction</strong> at this node.
      </p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 7 }}>
        {([
          ['P50 — median scenario', `${pct_p50}% safe to draw`],
          ['P10 — best-case scenario', `up to ${pct_p10}% available`],
        ] as [string, string][]).map(([label, value]) => (
          <li key={label} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 10px', borderRadius: 6,
            background: '#F7F8FA', border: '1px solid #ECEEF2',
          }}>
            <span style={{ fontSize: 11.5, color: '#6B7280' }}>{label}</span>
            <span style={{
              fontSize: 12, fontWeight: 600, color: '#0B0F19',
              fontFamily: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
            }}>{value}</span>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 10, lineHeight: 1.6 }}>
        Use this range to schedule loads across the 10-day horizon.
      </p>
    </>
  );
}

function StepFanChart({ forecast }: { forecast: ForecastResponse | null }) {
  if (!forecast) return null;
  const threshold = forecast.stress_threshold_demand_mw;
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 14 }}>
        7 days of history + a 10-day TFT demand forecast in megawatts. The fan widens
        further out as forecast uncertainty grows.
      </p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {([
          ['Dark line', 'P50 median — the most likely demand outcome'],
          ['Shaded bands', 'P10–P90 uncertainty cone — wider = less certain'],
          [`Dashed line · ${fmtMw(threshold)} MW`, 'Stress threshold — demand above this raises curtailment risk'],
          ['"now" divider', 'History (left) vs 10-day forecast (right)'],
        ] as [string, string][]).map(([label, desc]) => (
          <li key={label} style={{
            padding: '6px 10px', borderRadius: 6,
            background: '#F7F8FA', border: '1px solid #ECEEF2',
          }}>
            <div style={{ fontSize: 11.5, fontWeight: 600, color: '#0B0F19', marginBottom: 2 }}>{label}</div>
            <div style={{ fontSize: 11, color: '#6B7280' }}>{desc}</div>
          </li>
        ))}
      </ul>
    </>
  );
}

function StepStress({ forecast }: { forecast: ForecastResponse | null }) {
  if (!forecast) return null;
  const highRisk = forecast.stress_timeline.filter((p) => p.stress_probability >= 0.5).length;
  const threshold = forecast.stress_threshold_demand_mw;
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 14 }}>
        240 hourly cells spanning 10 days. Each shows the probability of demand
        crossing the{' '}
        <strong style={{ color: '#0B0F19' }}>{fmtMw(threshold)} MW</strong> threshold —
        the same dashed line in the chart above.
      </p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {([
          ['Green', '< 20%', 'Low stress'],
          ['Amber', '20–50%', 'Moderate risk'],
          ['Red', '> 50%', 'High curtailment risk'],
        ] as [string, string, string][]).map(([label, value, desc]) => (
          <li key={label} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '5px 10px', borderRadius: 6,
            background: '#F7F8FA', border: '1px solid #ECEEF2',
          }}>
            <span style={{ fontSize: 11.5, color: '#6B7280', minWidth: 38 }}>{label}</span>
            <span style={{
              fontSize: 11.5, fontWeight: 600, color: '#0B0F19', minWidth: 40,
              fontFamily: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
            }}>{value}</span>
            <span style={{ fontSize: 11, color: '#9CA3AF' }}>{desc}</span>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 10, lineHeight: 1.6 }}>
        <strong style={{ color: '#6B7280' }}>{highRisk}</strong> of the next 240 h show &gt;50% risk — hover any cell to inspect.
      </p>
    </>
  );
}

function StepEnsemble({ forecast }: { forecast: ForecastResponse | null }) {
  if (!forecast) return null;
  const temps = forecast.ensemble_spread.members.flat();
  const tMin = Math.round(Math.min(...temps));
  const tMax = Math.round(Math.max(...temps));
  const nMembers = forecast.ensemble_spread.members.length;
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 14 }}>
        <strong style={{ color: '#0B0F19' }}>{nMembers} GFS atmospheric model</strong> runs for
        near-surface temperature near this hub. Member spread directly drives the width
        of the demand fan above.
      </p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        {([
          ['Min modelled', `${tMin}°C`],
          ['Max modelled', `${tMax}°C`],
          ['Range', `${tMax - tMin}°C`],
        ] as [string, string][]).map(([label, value]) => (
          <div key={label} style={{
            flex: 1, padding: '8px 6px', borderRadius: 6, textAlign: 'center',
            background: '#F7F8FA', border: '1px solid #ECEEF2',
          }}>
            <div style={{
              fontSize: 15, fontWeight: 700, color: '#0B0F19',
              fontFamily: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
            }}>{value}</div>
            <div style={{ fontSize: 10, color: '#9CA3AF', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>
      <p style={{ fontSize: 12, color: '#9CA3AF', lineHeight: 1.6 }}>
        Bold line = ensemble mean. Wider spread at D+5–D+8 explains why the fan chart flares further out.
      </p>
    </>
  );
}

function StepDataCenters({ forecast }: { forecast: ForecastResponse | null }) {
  if (!forecast) return null;
  const dcs = forecast.data_centers;
  const totalCap = dcs.reduce((sum, dc) => sum + dc.capacity_mw, 0);
  return (
    <>
      <p style={{ fontSize: 13, color: '#6B7280', lineHeight: 1.65, marginBottom: 14 }}>
        <strong style={{ color: '#0B0F19' }}>{dcs.length} AI data centres</strong> share this
        grid with a combined <strong style={{ color: '#0B0F19' }}>{fmtMw(totalCap)} MW</strong> of
        capacity. GridCast&apos;s allocation ceiling is coordinated across all sites to
        prevent any single operator from forcing a curtailment.
      </p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
        {dcs.map((dc) => (
          <li key={dc.id} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '6px 10px', borderRadius: 6,
            background: '#F7F8FA', border: '1px solid #ECEEF2',
          }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#0B0F19' }}>{dc.name}</span>
            <span style={{
              fontSize: 11, color: '#6B7280',
              fontFamily: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
            }}>{dc.capacity_mw} MW</span>
          </li>
        ))}
      </ul>
      <p style={{ fontSize: 12, color: '#9CA3AF', marginTop: 10, lineHeight: 1.6 }}>
        Forecasts update every hour. Reopen this guide anytime via the{' '}
        <strong style={{ color: '#6B7280' }}>? Guide</strong> button.
      </p>
    </>
  );
}

// ─── Config ───────────────────────────────────────────────────────────────────

const STEP_META: { title: string; cta: string; target?: string }[] = [
  { title: 'Welcome to GridCast', cta: 'Continue' },
  { title: 'Explore the Grid', cta: 'Show me' },
  { title: 'Pick a Target Node', cta: 'Continue' },
  { title: 'Recommended Allocation', cta: 'Continue', target: 'allocation' },
  { title: 'Demand Forecast', cta: 'Continue', target: 'fanchart' },
  { title: 'Stress Timeline', cta: 'Continue', target: 'stress' },
  { title: 'Weather Ensemble', cta: 'Continue', target: 'ensemble' },
  { title: 'Co-located Data Centres', cta: 'Done', target: 'datacenters' },
];

function renderBody(step: number, forecast: ForecastResponse | null) {
  switch (step) {
    case 0: return <Step0 />;
    case 1: return <Step1 />;
    case 2: return <Step2 />;
    case 3: return <StepAllocation forecast={forecast} />;
    case 4: return <StepFanChart forecast={forecast} />;
    case 5: return <StepStress forecast={forecast} />;
    case 6: return <StepEnsemble forecast={forecast} />;
    case 7: return <StepDataCenters forecast={forecast} />;
    default: return <Step0 />;
  }
}

// ─── Arrow ────────────────────────────────────────────────────────────────────

type ArrowCoords = { x1: number; y1: number; x2: number; y2: number };

// ─── Main component ───────────────────────────────────────────────────────────

export function TutorialPanel({
  defaultOpen,
  forecast,
}: {
  defaultOpen: boolean;
  forecast: ForecastResponse | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);
  const [arrowCoords, setArrowCoords] = useState<ArrowCoords | null>(null);
  const [panelPosPx, setPanelPosPx] = useState<{ top: number; left: number } | null>(null);

  // Mount: initialize from sessionStorage or defaultOpen
  useEffect(() => {
    const stored = sessionStorage.getItem(STEP_KEY);
    let initialStep: number | null = null;

    if (stored !== null) {
      initialStep = parseInt(stored, 10);
    } else if (defaultOpen) {
      initialStep = 0;
    }

    if (initialStep === null) return;

    const params = new URLSearchParams(window.location.search);

    if (initialStep === 1 && params.get('filter') === 'target') {
      initialStep = 2;
    }

    // User clicked a node during step 2 (manually) → advance to step 3
    if (initialStep === 2 && params.get('node')) {
      initialStep = 3;
    }

    // Steps 3-7 require a node to be open; close gracefully if not
    if (initialStep >= 3 && !params.get('node')) {
      sessionStorage.removeItem(STEP_KEY);
      markSeen();
      return;
    }

    sessionStorage.setItem(STEP_KEY, String(initialStep));
    setStep(initialStep);
    setOpen(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Drive the filter-button glow while on step 1
  useEffect(() => {
    const el = document.documentElement;
    if (open && step === 1) {
      el.classList.add('gc-tutorial-filter');
    } else {
      el.classList.remove('gc-tutorial-filter');
    }
    return () => el.classList.remove('gc-tutorial-filter');
  }, [open, step]);

  // Advance from step 1 to step 2 when filter=target is applied (covers both
  // "Show me" button and manually clicking the glowing filter toggle)
  const filterParam = searchParams.get('filter');
  useEffect(() => {
    if (open && step === 1 && filterParam === 'target') {
      sessionStorage.setItem(STEP_KEY, '2');
      setStep(2);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterParam]);

  // Advance from step 2 to step 3 when a node is selected (manual click or Continue).
  // Intentionally omits `open` from deps — advance() sets open=false before navigating,
  // so we must not gate on it here; setOpen(true) re-opens at step 3.
  const nodeParam = searchParams.get('node');
  useEffect(() => {
    if (step === 2 && nodeParam) {
      sessionStorage.setItem(STEP_KEY, '3');
      setStep(3);
      setOpen(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeParam]);

  // Close gracefully if node panel is closed while on steps 3-7
  useEffect(() => {
    if (open && step >= 3 && !nodeParam) {
      markSeen();
      sessionStorage.removeItem(STEP_KEY);
      setOpen(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodeParam]);

  // Re-open via Guide button
  useEffect(() => {
    const handler = () => {
      sessionStorage.setItem(STEP_KEY, '0');
      setStep(0);
      setOpen(true);
    };
    window.addEventListener('gc:open-tutorial', handler);
    return () => window.removeEventListener('gc:open-tutorial', handler);
  }, []);

  // Compute panel position and arrow for steps 3-7
  const computePositions = useCallback(() => {
    const meta = STEP_META[step];
    if (!meta?.target || !panelRef.current) {
      setArrowCoords(null);
      setPanelPosPx(null);
      return;
    }
    const targetEl = document.querySelector(`[data-gc-tutorial="${meta.target}"]`);
    if (!targetEl) {
      setArrowCoords(null);
      setPanelPosPx(null);
      return;
    }

    const PANEL_W = 340;
    const GAP = 64;
    const panelH = panelRef.current.getBoundingClientRect().height;
    const targetRect = targetEl.getBoundingClientRect();
    const targetMidY = (targetRect.top + targetRect.bottom) / 2;

    // Position panel just to the left of the target section
    const panelLeft = Math.max(16, targetRect.left - GAP - PANEL_W);
    const desiredTop = targetMidY - panelH / 2;
    const top = Math.max(16, Math.min(window.innerHeight - panelH - 16, desiredTop));

    setPanelPosPx({ top, left: panelLeft });
    setArrowCoords({
      x1: panelLeft + PANEL_W,
      y1: top + panelH / 2,
      x2: targetRect.left,
      y2: Math.max(targetRect.top + 20, Math.min(targetRect.bottom - 20, targetMidY)),
    });
  }, [step]);

  // Scroll target into view then compute positions
  useEffect(() => {
    const meta = STEP_META[step];
    if (!meta?.target || !open) {
      setArrowCoords(null);
      setPanelPosPx(null);
      return;
    }
    const el = document.querySelector(`[data-gc-tutorial="${meta.target}"]`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    const timer = setTimeout(computePositions, 380);
    return () => clearTimeout(timer);
  }, [step, open, computePositions]);

  // Keep arrow in sync when user manually scrolls the node panel
  useEffect(() => {
    const meta = STEP_META[step];
    if (!meta?.target || !open) return;
    const aside = document.querySelector('[data-gc-panel="node"]');
    if (!aside) return;
    aside.addEventListener('scroll', computePositions, { passive: true });
    return () => aside.removeEventListener('scroll', computePositions);
  }, [step, open, computePositions]);

  function close() {
    setOpen(false);
    markSeen();
    sessionStorage.removeItem(STEP_KEY);
  }

  function advance() {
    const nextStep = step + 1;

    if (step === 1) {
      sessionStorage.setItem(STEP_KEY, '2');
      if (filterParam === 'target') {
        // Filter already active — advance directly; filterParam won't change so the effect won't fire
        setStep(2);
      } else {
        // Navigate to apply the filter; filterParam effect will advance the step
        const params = new URLSearchParams(searchParams.toString());
        params.set('filter', 'target');
        params.delete('node');
        router.push(`/?${params.toString()}`);
      }
      return;
    }

    if (step === 2) {
      // "Continue": auto-navigate to ERCOT Houston; step 3 picks up on reload
      sessionStorage.setItem(STEP_KEY, '3');
      setOpen(false);
      const params = new URLSearchParams(searchParams.toString());
      params.set('node', 'ercot-houston');
      router.push(`/?${params.toString()}`);
      return;
    }

    if (step === TOTAL_STEPS - 1) {
      markSeen();
      sessionStorage.removeItem(STEP_KEY);
      setOpen(false);
      return;
    }

    sessionStorage.setItem(STEP_KEY, String(nextStep));
    setStep(nextStep);
  }

  if (!open) return null;

  const meta = STEP_META[step];
  const isRight = step === 2;
  const hasPanelTarget = !!meta.target;

  // Positioning: near the NodePanel for steps 3-7, centered otherwise
  const positionStyle: React.CSSProperties = hasPanelTarget && panelPosPx !== null
    ? { top: panelPosPx.top, left: panelPosPx.left }
    : isRight
      ? { top: '50%', right: 32, transform: 'translateY(-50%)' }
      : { top: '50%', left: 32, transform: 'translateY(-50%)' };

  return (
    <>
      {/* SVG dashed arrow for steps 3-7 */}
      {arrowCoords && (
        <svg
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            pointerEvents: 'none',
            zIndex: 49,
            overflow: 'visible',
          }}
        >
          <defs>
            <marker
              id="gc-arrowhead"
              markerWidth="8"
              markerHeight="6"
              refX="7"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#0F3D56" fillOpacity="0.6" />
            </marker>
          </defs>
          <path
            d={`M ${arrowCoords.x1} ${arrowCoords.y1} C ${arrowCoords.x1 + (arrowCoords.x2 - arrowCoords.x1) * 0.55} ${arrowCoords.y1}, ${arrowCoords.x1 + (arrowCoords.x2 - arrowCoords.x1) * 0.55} ${arrowCoords.y2}, ${arrowCoords.x2} ${arrowCoords.y2}`}
            stroke="#0F3D56"
            strokeOpacity="0.55"
            strokeWidth="1.8"
            fill="none"
            markerEnd="url(#gc-arrowhead)"
          />
        </svg>
      )}

      {/* Tutorial dialog */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="false"
        aria-label="GridCast tutorial"
        style={{
          position: 'fixed',
          ...positionStyle,
          width: 340,
          zIndex: 50,
          background: '#fff',
          border: '1px solid #ECEEF2',
          borderRadius: 12,
          boxShadow: '0 8px 40px rgba(11,15,25,0.12), 0 1px 4px rgba(11,15,25,0.06)',
          transition: 'top 300ms cubic-bezier(.2,.7,.3,1)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 16px 12px',
          borderBottom: '1px solid #ECEEF2',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#0F3D56' }}>
            <PulseLogo size={18} className="shrink-0" />
            <span style={{ fontSize: 13, fontWeight: 600, letterSpacing: '-0.02em' }}>GridCast</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              fontSize: 11, color: '#9CA3AF',
              fontFamily: 'var(--font-jbmono), "JetBrains Mono", ui-monospace, monospace',
            }}>
              {step + 1} / {TOTAL_STEPS}
            </span>
            <button
              onClick={close}
              aria-label="Close tutorial"
              style={{
                width: 22, height: 22, borderRadius: 6, display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                background: 'transparent', border: 'none', cursor: 'pointer',
                color: '#9CA3AF', fontSize: 17, lineHeight: 1, padding: 0,
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '20px 20px 0' }}>
          <h2 style={{
            fontSize: 16, fontWeight: 700, color: '#0B0F19',
            marginBottom: 12, letterSpacing: '-0.025em',
          }}>
            {meta.title}
          </h2>
          {renderBody(step, forecast)}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 20px',
          marginTop: 20,
          borderTop: '1px solid #ECEEF2',
        }}>
          <button
            onClick={close}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 12, color: '#9CA3AF', padding: 0,
            }}
          >
            Skip tutorial
          </button>
          <button
            onClick={advance}
            style={{
              background: '#0F3D56', color: '#fff',
              border: 'none', borderRadius: 8, cursor: 'pointer',
              fontSize: 12, fontWeight: 600, padding: '7px 16px',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {meta.cta} <span style={{ fontSize: 14, lineHeight: 1 }}>&#8594;</span>
          </button>
        </div>
      </div>
    </>
  );
}
