import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { MitigationComparison, MitigationIntervention, MitigationScenarios } from "./types";

const interventionOrder: MitigationIntervention[] = ["clean_drains", "deploy_pumps", "upgrade_drainage"];

function CompactComparisonChart({ comparison }: { comparison: MitigationComparison }) {
  const baseline = comparison.baseline.total_modeled_accumulation_m3;
  const intervention = comparison.with_interventions.total_modeled_accumulation_m3;
  const max = Math.max(1, baseline, intervention);
  const baselineHeight = 112 * baseline / max;
  const interventionHeight = 112 * intervention / max;
  return <figure className="mitigation-chart" aria-label="Modeled accumulation before and after interventions"><figcaption>Modeled accumulation · m³</figcaption><svg viewBox="0 0 260 154" role="img" aria-label={`Baseline ${baseline.toFixed(0)} cubic metres; after interventions ${intervention.toFixed(0)} cubic metres`}><line x1="22" y1="126" x2="246" y2="126" stroke="#3a5471" /><rect x="55" y={126 - baselineHeight} width="54" height={baselineHeight} rx="5" fill="#e5874a" /><rect x="153" y={126 - interventionHeight} width="54" height={interventionHeight} rx="5" fill="#52c7a3" /><text x="82" y="145" textAnchor="middle">Baseline</text><text x="180" y="145" textAnchor="middle">After</text><text x="82" y={Math.max(14, 120 - baselineHeight)} textAnchor="middle">{Math.round(baseline).toLocaleString()}</text><text x="180" y={Math.max(14, 120 - interventionHeight)} textAnchor="middle">{Math.round(intervention).toLocaleString()}</text></svg></figure>;
}

export function MitigationSimulator() {
  const [catalogue, setCatalogue] = useState<MitigationScenarios>();
  const [catchmentCount, setCatchmentCount] = useState(10);
  const [intensity, setIntensity] = useState(50);
  const [duration, setDuration] = useState(3);
  const [blockage, setBlockage] = useState(0);
  const [selected, setSelected] = useState<MitigationIntervention[]>([]);
  const [comparison, setComparison] = useState<MitigationComparison>();
  const [status, setStatus] = useState<string>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const hasInterventions = selected.length > 0;

  useEffect(() => { void Promise.all([api.mitigationScenarios(), api.mitigationCatchments()]).then(([scenarios, catchments]) => { setCatalogue(scenarios); setIntensity(scenarios.default_inputs.rainfall_intensity_mm_per_hour); setDuration(scenarios.default_inputs.rainfall_duration_hours); setBlockage(scenarios.default_inputs.drain_blockage_percent); setCatchmentCount(catchments.catchments.features.length); }).catch(() => setError("Unable to load the local mitigation simulator.")); }, []);
  const selectedLabels = useMemo(() => (catalogue?.interventions.filter((item) => selected.includes(item.id)).map((item) => item.label) ?? []), [catalogue, selected]);
  const invalidate = () => { setComparison(undefined); setStatus(undefined); };
  const compare = async () => { setLoading(true); setError(undefined); try { setComparison(await api.mitigationCompare({ rainfall_intensity_mm_per_hour: intensity, rainfall_duration_hours: duration, drain_blockage_percent: blockage, selected_interventions: selected })); setStatus(`Simulation updated for ${intensity} mm/hour · ${duration} hours · ${blockage}% blockage.`); } catch { setError("Unable to calculate the modeled comparison."); } finally { setLoading(false); } };
  const toggle = (id: MitigationIntervention) => { invalidate(); setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]); };
  const updateIntensity = (value: number) => { invalidate(); setIntensity(value); };
  const updateDuration = (value: number) => { invalidate(); setDuration(value); };
  const updateBlockage = (value: number) => { invalidate(); setBlockage(value); };

  return <section className="mitigation-simulator" aria-labelledby="mitigation-title"><div className="mitigation-heading"><div><p className="eyebrow">SYNTHETIC DEMO CATCHMENTS · {catchmentCount}</p><h2 id="mitigation-title">Mitigation Simulator</h2><p>Transparent water-balance demonstration assumptions—not surveyed drainage boundaries, live conditions, or official advice.</p></div><span className="synthetic-badge">◆ DEMONSTRATION ASSUMPTIONS</span></div><div className="mitigation-controls"><label>Rainfall intensity <b>{intensity} mm/hour</b><input aria-label="Mitigation rainfall intensity" type="range" min="0" max="150" step="5" value={intensity} onChange={(event) => updateIntensity(Number(event.target.value))} /></label><label>Rainfall duration <b>{duration} hours</b><input aria-label="Mitigation rainfall duration" type="range" min="1" max="12" step="1" value={duration} onChange={(event) => updateDuration(Number(event.target.value))} /></label><label>Drain blockage <b>{blockage}%</b><input aria-label="Mitigation drain blockage" type="range" min="0" max="100" step="5" value={blockage} onChange={(event) => updateBlockage(Number(event.target.value))} /></label></div><div className="intervention-cards" aria-label="Mitigation interventions">{(catalogue?.interventions ?? []).sort((a, b) => interventionOrder.indexOf(a.id) - interventionOrder.indexOf(b.id)).map((item) => <label key={item.id} className={`intervention-card ${selected.includes(item.id) ? "selected" : ""}`}><input type="checkbox" checked={selected.includes(item.id)} onChange={() => toggle(item.id)} /><span><b>{item.label}</b><small>{item.description}</small></span><em>DEMO</em></label>)}</div><div className="mitigation-action"><button type="button" onClick={() => void compare()} disabled={loading}>{loading ? "Calculating…" : hasInterventions ? "Compare with baseline" : "View baseline"}</button>{error && <p role="alert">{error}</p>}</div>{comparison && <div className="mitigation-results"><p className="mitigation-comparison-note">Baseline and after use the same rainfall, duration, and blockage inputs. The difference comes only from selected mitigation actions.</p>{status && <p className="mitigation-status" role="status">{status}</p>}<div className="mitigation-metrics"><article><small>Baseline modeled accumulation</small><strong>{comparison.baseline.total_modeled_accumulation_m3.toLocaleString()} m³</strong><span>{comparison.baseline.affected_catchment_count} affected catchments</span></article>{hasInterventions ? <><article><small>After interventions</small><strong>{comparison.with_interventions.total_modeled_accumulation_m3.toLocaleString()} m³</strong><span>{comparison.with_interventions.affected_catchment_count} affected catchments</span></article><article><small>Modeled reduction</small><strong>{comparison.percentage_modeled_reduction_vs_baseline.toFixed(1)}%</strong><span>versus baseline</span></article></> : <article className="mitigation-empty-result"><small>After mitigation</small><span>Select one or more interventions to calculate an after-mitigation result.</span></article>}</div>{hasInterventions && <CompactComparisonChart comparison={comparison} />}<p className="mitigation-explanation">{hasInterventions ? `${selectedLabels.join(", ")} change the assumed blockage or drainage capacity, so the model removes more runoff during each time step. ` : "This baseline run uses no mitigation action. "}This is modeled accumulation and a modeled ponding-depth equivalent only—not actual flood depth or a prediction.</p><p className="fine-print">{comparison.disclaimer}</p></div>}</section>;
}
