import { useEffect, useRef, useState } from "react";

const STORAGE_KEY = "floodshift-ai-tour-completed-v1";

const STEPS = [
  { title: "Welcome to VarshaVyuha", body: "Urban Flood Resilience Lab. Explore how simulated rainfall and drainage conditions could change scenario-based risk across this study area." },
  { title: "Scenario Lab", body: "Use this tab for synthetic what-if scenarios. It is not a flood forecast or official warning." },
  { title: "Historical Evidence", body: "Use this tab to view real 2023 IMD gridded rainfall and OpenStreetMap reference context. It does not show flood extent or risk." },
  { title: "Adjust the scenario", body: "Rainfall multiplier compares simulated rainfall with the baseline. Drainage blockage simulates reduced drainage capacity for this scenario." },
  { title: "Inspect the map", body: "Run a scenario, then click a grid cell to see its score and the drivers behind it." }
] as const;

function completed() {
  try { return window.localStorage.getItem(STORAGE_KEY) === "true"; } catch { return false; }
}

export function OnboardingTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const dialog = useRef<HTMLDivElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);

  useEffect(() => { if (!completed()) setOpen(true); }, []);
  useEffect(() => {
    if (!open) return;
    dialog.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") finish(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [open]);

  const finish = () => {
    try { window.localStorage.setItem(STORAGE_KEY, "true"); } catch { /* local storage may be unavailable */ }
    setOpen(false); setStep(0); window.setTimeout(() => returnFocus.current?.focus(), 0);
  };
  const replay = () => { returnFocus.current = document.activeElement as HTMLElement; setStep(0); setOpen(true); };
  const current = STEPS[step];
  return <>
    <button type="button" className="tour-trigger" onClick={replay}>How it works</button>
    {open && <div className="tour-backdrop"><section className="tour-dialog" role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-description" tabIndex={-1} ref={dialog}><p className="tour-progress">Step {step + 1} of {STEPS.length}</p><h2 id="tour-title">{current.title}</h2><p id="tour-description">{current.body}</p><div className="tour-actions"><button type="button" className="tour-skip" onClick={finish}>Skip</button><span /><button type="button" className="tour-back" onClick={() => setStep((value) => Math.max(0, value - 1))} disabled={step === 0}>Back</button>{step === STEPS.length - 1 ? <button type="button" className="tour-primary" onClick={finish}>Finish</button> : <button type="button" className="tour-primary" onClick={() => setStep((value) => value + 1)}>Next</button>}</div></section></div>}
  </>;
}

export function InfoTip({ label, children }: { label: string; children: string }) {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<{ left: number; top: number; transform: string; width: number }>();
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open || !trigger.current) return undefined;
    const place = () => {
      const rect = trigger.current!.getBoundingClientRect();
      const width = Math.min(288, window.innerWidth - 24);
      const preferAbove = rect.top > 120;
      const left = Math.max(12, Math.min(window.innerWidth - width - 12, rect.left + rect.width / 2 - width / 2));
      setPlacement({ left, top: preferAbove ? rect.top - 10 : rect.bottom + 10, transform: preferAbove ? "translateY(-100%)" : "none", width });
    };
    place(); window.addEventListener("resize", place); window.addEventListener("scroll", place, true);
    return () => { window.removeEventListener("resize", place); window.removeEventListener("scroll", place, true); };
  }, [open]);
  return <span className="info-tip"><button ref={trigger} type="button" aria-label={`Help: ${label}`} aria-expanded={open} onClick={() => setOpen((value) => !value)}>?</button>{open && <span role="tooltip" style={placement}>{children}</span>}</span>;
}
