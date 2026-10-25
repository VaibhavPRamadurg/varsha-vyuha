import { useEffect, useState } from "react";

const INTRO_DURATION_MS = 2600;

export function LaunchIntro() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setVisible(false);
      return undefined;
    }
    const timer = window.setTimeout(() => setVisible(false), INTRO_DURATION_MS);
    return () => window.clearTimeout(timer);
  }, []);

  if (!visible) return null;
  return <section className="launch-intro" aria-label="VarshaVyuha launch introduction">
    <div className="launch-ripple" aria-hidden="true"><i /><i /><i /></div>
    <div className="launch-grid" aria-hidden="true" />
    <div className="launch-lockup">
      <svg className="launch-mark" viewBox="0 0 72 72" aria-hidden="true"><path d="M36 8C28 20 17 31 17 43a19 19 0 0 0 38 0C55 31 44 20 36 8Z" /><path d="M24 45c7-7 17-8 25-2" /><path d="M29 52h6v6h-6zm9 0h6v6h-6z" /></svg>
      <p className="launch-name">VarshaVyuha</p>
      <p className="launch-subtitle">Urban Flood Resilience Lab</p>
    </div>
    <button type="button" className="launch-skip" onClick={() => setVisible(false)}>Skip intro</button>
  </section>;
}
