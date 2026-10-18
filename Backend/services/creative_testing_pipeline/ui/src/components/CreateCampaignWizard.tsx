import { useState } from "react";
import { ChevronRight, ChevronLeft, Check, X } from "lucide-react";

const API = "/api/actp";

interface Props {
  onDone: () => void;
  onCancel: () => void;
}

const STEPS = ["Basic Info", "Targeting", "Creative Setup", "Review"];

const MODES = [
  { value: "organic_only", label: "Organic Only", desc: "Test on TikTok/YouTube before spending on ads" },
  { value: "ad_only", label: "Ads Only", desc: "Deploy directly to paid ads" },
  { value: "full_pipeline", label: "Full Pipeline", desc: "Organic test → winner → paid scale" },
];

const PLATFORMS = ["tiktok", "youtube_shorts", "instagram_reels"];
const SOURCES = ["sora", "veo3", "remotion", "nano_banana"];

export function CreateCampaignWizard({ onDone, onCancel }: Props) {
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    offer_name: "",
    offer_url: "",
    mode: "full_pipeline",
    platforms: ["tiktok", "youtube_shorts"] as string[],
    generation_sources: ["sora"] as string[],
    target_audience: { age_min: 18, age_max: 45, interests: [] as string[] },
    max_rounds: 5,
    creatives_per_round: 5,
    organic_budget_days: 3,
    ad_budget_cents: 500,
  });

  const set = (key: string, value: any) => setForm((f) => ({ ...f, [key]: value }));

  const toggleArr = (key: "platforms" | "generation_sources", val: string) => {
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(val) ? f[key].filter((x) => x !== val) : [...f[key], val],
    }));
  };

  const canNext = () => {
    if (step === 0) return form.name.trim().length > 0;
    if (step === 1) return form.platforms.length > 0;
    if (step === 2) return form.generation_sources.length > 0;
    return true;
  };

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API}/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      onDone();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-white">New Campaign</h1>
        <button onClick={onCancel} className="text-gray-500 hover:text-white transition-colors">
          <X size={20} />
        </button>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-2 flex-1">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-colors ${
              i < step ? "bg-indigo-600 text-white" : i === step ? "bg-indigo-500 text-white" : "bg-gray-800 text-gray-500"
            }`}>
              {i < step ? <Check size={12} /> : i + 1}
            </div>
            <span className={`text-sm hidden sm:block ${i === step ? "text-white font-medium" : "text-gray-500"}`}>{s}</span>
            {i < STEPS.length - 1 && <div className={`flex-1 h-px ${i < step ? "bg-indigo-600" : "bg-gray-800"}`} />}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">

        {/* Step 0: Basic Info */}
        {step === 0 && (
          <>
            <Field label="Campaign Name" required>
              <input
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. Summer Sale Hook Test"
                className="input"
              />
            </Field>
            <Field label="Offer Name">
              <input
                value={form.offer_name}
                onChange={(e) => set("offer_name", e.target.value)}
                placeholder="e.g. 30-Day Free Trial"
                className="input"
              />
            </Field>
            <Field label="Offer URL">
              <input
                value={form.offer_url}
                onChange={(e) => set("offer_url", e.target.value)}
                placeholder="https://..."
                className="input"
                type="url"
              />
            </Field>
            <Field label="Pipeline Mode">
              <div className="space-y-2">
                {MODES.map((m) => (
                  <label key={m.value} className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    form.mode === m.value ? "border-indigo-500 bg-indigo-500/10" : "border-gray-700 hover:border-gray-600"
                  }`}>
                    <input
                      type="radio"
                      name="mode"
                      value={m.value}
                      checked={form.mode === m.value}
                      onChange={() => set("mode", m.value)}
                      className="mt-0.5"
                    />
                    <div>
                      <div className="text-sm font-medium text-white">{m.label}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{m.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </Field>
          </>
        )}

        {/* Step 1: Targeting */}
        {step === 1 && (
          <>
            <Field label="Publish Platforms" required>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    key={p}
                    type="button"
                    onClick={() => toggleArr("platforms", p)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      form.platforms.includes(p) ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {p.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Age Min">
                <input
                  type="number"
                  value={form.target_audience.age_min}
                  onChange={(e) => set("target_audience", { ...form.target_audience, age_min: +e.target.value })}
                  className="input"
                  min={13} max={65}
                />
              </Field>
              <Field label="Age Max">
                <input
                  type="number"
                  value={form.target_audience.age_max}
                  onChange={(e) => set("target_audience", { ...form.target_audience, age_max: +e.target.value })}
                  className="input"
                  min={13} max={65}
                />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Max Rounds">
                <input type="number" value={form.max_rounds} onChange={(e) => set("max_rounds", +e.target.value)} className="input" min={1} max={20} />
              </Field>
              <Field label="Creatives per Round">
                <input type="number" value={form.creatives_per_round} onChange={(e) => set("creatives_per_round", +e.target.value)} className="input" min={1} max={20} />
              </Field>
            </div>
          </>
        )}

        {/* Step 2: Creative Setup */}
        {step === 2 && (
          <>
            <Field label="Video Generation Sources" required>
              <div className="flex flex-wrap gap-2">
                {SOURCES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleArr("generation_sources", s)}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      form.generation_sources.includes(s) ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {s.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Organic Test Days">
                <input type="number" value={form.organic_budget_days} onChange={(e) => set("organic_budget_days", +e.target.value)} className="input" min={1} max={14} />
              </Field>
              <Field label="Ad Budget (cents)">
                <input type="number" value={form.ad_budget_cents} onChange={(e) => set("ad_budget_cents", +e.target.value)} className="input" min={100} step={100} />
              </Field>
            </div>
          </>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <div className="space-y-3 text-sm">
            <ReviewRow label="Name" value={form.name} />
            <ReviewRow label="Mode" value={form.mode.replace(/_/g, " ")} />
            <ReviewRow label="Platforms" value={form.platforms.join(", ")} />
            <ReviewRow label="Sources" value={form.generation_sources.join(", ")} />
            <ReviewRow label="Rounds" value={`${form.max_rounds} rounds × ${form.creatives_per_round} creatives`} />
            <ReviewRow label="Ad Budget" value={`$${(form.ad_budget_cents / 100).toFixed(2)}`} />
            {error && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-400 text-xs">{error}</div>
            )}
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-6">
        <button
          onClick={() => step > 0 ? setStep(step - 1) : onCancel()}
          className="flex items-center gap-2 text-gray-400 hover:text-white px-4 py-2 rounded-lg transition-colors"
        >
          <ChevronLeft size={16} /> {step === 0 ? "Cancel" : "Back"}
        </button>
        {step < STEPS.length - 1 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canNext()}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-2 rounded-lg font-medium transition-colors"
          >
            Next <ChevronRight size={16} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-40 text-white px-5 py-2 rounded-lg font-medium transition-colors"
          >
            {submitting ? "Creating..." : "Create Campaign"} <Check size={16} />
          </button>
        )}
      </div>
    </div>
  );
}

function Field({ label, children, required }: { label: string; children: React.ReactNode; required?: boolean }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-300 mb-1.5">
        {label}{required && <span className="text-red-400 ml-1">*</span>}
      </label>
      {children}
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-2 border-b border-gray-800">
      <span className="text-gray-500">{label}</span>
      <span className="text-white font-medium capitalize">{value}</span>
    </div>
  );
}
