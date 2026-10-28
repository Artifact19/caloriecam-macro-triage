import { useEffect, useRef, useState } from 'react';
import { animate, useReducedMotion } from 'framer-motion';

interface CountUpProps {
  value: number;
  /** Format function for the displayed number. */
  format?: (v: number) => string;
  duration?: number;
  className?: string;
  testId?: string;
}

/** Animated count-up. The final value is always exposed to assistive tech and tests. */
export function CountUp({
  value,
  format = (v) => String(Math.round(v)),
  duration = 0.8,
  className = '',
  testId,
}: CountUpProps) {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);

  useEffect(() => {
    if (reduceMotion) {
      fromRef.current = value;
      setDisplay(value);
      return;
    }
    const controls = animate(fromRef.current, value, {
      duration,
      ease: 'easeOut',
      onUpdate: (v) => {
        fromRef.current = v;
        setDisplay(v);
      },
    });
    return () => controls.stop();
  }, [value, duration, reduceMotion]);

  return (
    <>
      <span aria-hidden="true" className={`tabular ${className}`}>
        {format(display)}
      </span>
      <span className="sr-only" data-testid={testId}>
        {format(value)}
      </span>
    </>
  );
}
