import type { CSSProperties } from 'react';

interface ShapeProps {
  className?: string;
  size?: number;
  color?: string;
  style?: CSSProperties;
}

/** Decorative shapes (aria-hidden). Fill color is a Tailwind-independent CSS color. */

export function StarShape({ className = '', size = 24, color = '#DC903C', style }: ShapeProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
    >
      <path
        d="M12 2.5l2.8 6.2 6.7.7-5 4.6 1.4 6.6L12 17.2 6.1 20.6l1.4-6.6-5-4.6 6.7-.7z"
        fill={color}
        stroke="#1C1917"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function TriangleShape({
  className = '',
  size = 22,
  color = '#8C9B7A',
  style,
  rotate = 0,
}: ShapeProps & { rotate?: number }) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={className}
      style={{ ...style, transform: rotate ? `rotate(${rotate}deg)` : undefined }}
      width={size}
      height={size}
      viewBox="0 0 24 24"
    >
      <polygon points="12,3 22,21 2,21" fill={color} stroke="#1C1917" strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}

export function SquareShape({ className = '', size = 20, color = '#ECC1B8', style }: ShapeProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
    >
      <rect x="3" y="3" width="18" height="18" rx="3" fill={color} stroke="#1C1917" strokeWidth="2.5" />
    </svg>
  );
}

export function DiamondShape({ className = '', size = 20, color = '#8C9B7A', style }: ShapeProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
    >
      <path d="M12 2.5L21.5 12 12 21.5 2.5 12z" fill={color} stroke="#1C1917" strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}

export function CircleShape({ className = '', size = 20, color = '#EBB058', style }: ShapeProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
    >
      <circle cx="12" cy="12" r="9" fill={color} stroke="#1C1917" strokeWidth="2.5" />
    </svg>
  );
}

export function SparkleShape({ className = '', size = 24, color = '#1C1917', style }: ShapeProps) {
  return (
    <svg
      aria-hidden="true"
      focusable="false"
      className={className}
      style={style}
      width={size}
      height={size}
      viewBox="0 0 24 24"
    >
      <path d="M12 1l2.2 8.8L23 12l-8.8 2.2L12 23l-2.2-8.8L1 12l8.8-2.2z" fill={color} />
    </svg>
  );
}
