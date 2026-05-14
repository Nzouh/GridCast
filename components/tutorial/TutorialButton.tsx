'use client';

export function TutorialButton() {
  return (
    <button
      type="button"
      aria-label="Open tutorial guide"
      onClick={() => window.dispatchEvent(new CustomEvent('gc:open-tutorial'))}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded border border-black/10 text-[12px] text-text-secondary hover:text-text-primary hover:border-black/20 transition-colors bg-white"
    >
      <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full border border-current text-[9px] font-bold leading-none">
        ?
      </span>
      Guide
    </button>
  );
}
