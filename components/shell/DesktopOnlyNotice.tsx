import { PulseLogo } from './PulseLogo';

export function DesktopOnlyNotice() {
  return (
    <div className="lg:hidden fixed inset-0 flex items-center justify-center bg-white z-50 px-8 text-center">
      <div className="max-w-sm">
        <div className="mb-2 flex items-center justify-center gap-2 text-brand">
          <PulseLogo size={28} />
          <div className="text-[20px] font-semibold tracking-[-0.028em]">GridCast</div>
        </div>
        <p className="text-text-secondary text-[14px] leading-relaxed">
          GridCast is best viewed on desktop. Please open this page in a browser
          window at least 1024 pixels wide.
        </p>
      </div>
    </div>
  );
}
