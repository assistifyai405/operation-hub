import { useEffect, useRef, useState } from "react";

export function useCountUp(target, duration = 900) {
  const [val, setVal] = useState(0);
  const ref = useRef();
  useEffect(() => {
    const to = Number(target) || 0;
    const start = performance.now();
    cancelAnimationFrame(ref.current);
    const tick = (now) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setVal(to * eased);
      if (p < 1) ref.current = requestAnimationFrame(tick);
      else setVal(to);
    };
    ref.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(ref.current);
  }, [target, duration]);
  return val;
}
