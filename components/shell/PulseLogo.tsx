export function PulseLogo({
  size = 26,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      <circle cx="32" cy="32" r="29" stroke="currentColor" strokeOpacity="0.18" strokeWidth="1.5" />
      <circle cx="32" cy="32" r="20" stroke="currentColor" strokeOpacity="0.45" strokeWidth="1.5" />
      <circle cx="32" cy="32" r="11" fill="currentColor" />
      <circle cx="32" cy="32" r="5" fill="#ffffff" />
      <circle cx="32" cy="32" r="2.2" fill="oklch(0.62 0.21 27)" />
    </svg>
  );
}
