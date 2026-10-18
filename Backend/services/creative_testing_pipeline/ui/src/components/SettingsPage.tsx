import { useState, useEffect } from "react";
import { Save, RefreshCw, CheckCircle, XCircle, Key, Globe, Bell } from "lucide-react";

const API = "/api/actp";

interface ProviderStatus {
  [key: string]: boolean;
}

interface CredentialStatus {
  [key: string]: boolean;
}

export function SettingsPage() {
  const [providers, setProviders] = useState<ProviderStatus>({});
  const [credentials, setCredentials] = useState<CredentialStatus>({});
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"providers" | "webhooks" | "monitoring">("providers");
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [newWebhook, setNewWebhook] = useState({ url: "", events: [] as string[] });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const WEBHOOK_EVENTS = [
    "winner.selected", "round.completed", "metric.anomaly",
    "campaign.paused", "campaign.completed", "ad.approved",
  ];

  useEffect(() => {
    Promise.all([
      fetch(`${API}/security/providers`).then((r) => r.json()).catch(() => ({})),
      fetch(`${API}/publisher/credentials`).then((r) => r.json()).catch(() => ({ credentials: {} })),
      fetch(`${API}/health`).then((r) => r.json()).catch(() => null),
      fetch(`${API}/webhooks`).then((r) => r.json()).catch(() => ({ webhooks: [] })),
    ]).then(([prov, creds, hlth, whs]) => {
      setProviders(prov.providers || prov || {});
      setCredentials(creds.credentials || {});
      setHealth(hlth);
      setWebhooks(whs.webhooks || []);
      setLoading(false);
    });
  }, []);

  async function addWebhook() {
    if (!newWebhook.url || newWebhook.events.length === 0) return;
    setSaving(true);
    const res = await fetch(`${API}/webhooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newWebhook),
    });
    const data = await res.json();
    if (data.created) {
      setWebhooks((w) => [...w, data.webhook]);
      setNewWebhook({ url: "", events: [] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }
    setSaving(false);
  }

  async function deleteWebhook(id: string) {
    await fetch(`${API}/webhooks/${id}`, { method: "DELETE" });
    setWebhooks((w) => w.filter((x) => x.id !== id));
  }

  const toggleEvent = (event: string) => {
    setNewWebhook((w) => ({
      ...w,
      events: w.events.includes(event) ? w.events.filter((e) => e !== event) : [...w.events, event],
    }));
  };

  if (loading) return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <div className="h-8 w-32 bg-gray-800 rounded animate-pulse" />
      <div className="h-64 bg-gray-800 rounded-xl animate-pulse" />
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800">
        {(["providers", "webhooks", "monitoring"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${
              activeTab === tab ? "border-indigo-500 text-white" : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Providers Tab */}
      {activeTab === "providers" && (
        <div className="space-y-4">
          <Section title="Video Generation Providers" icon={<Key size={16} />}>
            {Object.entries(providers).length === 0 && (
              <p className="text-sm text-gray-500">No provider status available</p>
            )}
            {Object.entries(providers).map(([name, available]) => (
              <StatusRow key={name} label={name.replace(/_/g, " ")} ok={available as boolean} />
            ))}
          </Section>

          <Section title="Publishing Credentials" icon={<Globe size={16} />}>
            {Object.entries(credentials).length === 0 && (
              <p className="text-sm text-gray-500">No credentials configured</p>
            )}
            {Object.entries(credentials).map(([platform, ok]) => (
              <StatusRow key={platform} label={platform.replace(/_/g, " ")} ok={ok as boolean} />
            ))}
          </Section>
        </div>
      )}

      {/* Webhooks Tab */}
      {activeTab === "webhooks" && (
        <div className="space-y-4">
          <Section title="Registered Webhooks" icon={<Bell size={16} />}>
            {webhooks.length === 0 && (
              <p className="text-sm text-gray-500">No webhooks configured</p>
            )}
            {webhooks.map((wh: any) => (
              <div key={wh.id} className="flex items-center justify-between py-2 border-b border-gray-800">
                <div className="min-w-0">
                  <p className="text-sm text-white truncate">{wh.url}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{(wh.events || []).join(", ")}</p>
                </div>
                <button
                  onClick={() => deleteWebhook(wh.id)}
                  className="text-gray-600 hover:text-red-400 transition-colors ml-3 flex-shrink-0 text-xs"
                >
                  Remove
                </button>
              </div>
            ))}
          </Section>

          <Section title="Add Webhook" icon={<Bell size={16} />}>
            <div className="space-y-3">
              <input
                value={newWebhook.url}
                onChange={(e) => setNewWebhook((w) => ({ ...w, url: e.target.value }))}
                placeholder="https://your-endpoint.com/webhook"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />
              <div className="flex flex-wrap gap-2">
                {WEBHOOK_EVENTS.map((event) => (
                  <button
                    key={event}
                    type="button"
                    onClick={() => toggleEvent(event)}
                    className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                      newWebhook.events.includes(event) ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
                    }`}
                  >
                    {event}
                  </button>
                ))}
              </div>
              <button
                onClick={addWebhook}
                disabled={saving || !newWebhook.url || newWebhook.events.length === 0}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {saving ? <RefreshCw size={14} className="animate-spin" /> : <Save size={14} />}
                {saved ? "Saved!" : "Add Webhook"}
              </button>
            </div>
          </Section>
        </div>
      )}

      {/* Monitoring Tab */}
      {activeTab === "monitoring" && (
        <div className="space-y-4">
          <Section title="System Health" icon={<RefreshCw size={16} />}>
            {!health && <p className="text-sm text-gray-500">Health data unavailable</p>}
            {health && (
              <>
                <StatusRow label="Database" ok={health.database === "healthy"} />
                <StatusRow label="Pipeline" ok={health.pipeline !== "error"} />
                {health.latency_ms != null && (
                  <div className="flex items-center justify-between py-2">
                    <span className="text-sm text-gray-400">API Latency</span>
                    <span className={`text-sm font-medium ${health.latency_ms < 200 ? "text-green-400" : "text-yellow-400"}`}>
                      {health.latency_ms}ms
                    </span>
                  </div>
                )}
              </>
            )}
          </Section>

          <Section title="Keyboard Shortcuts" icon={<Key size={16} />}>
            {[
              ["⌘N", "New Campaign"],
              ["⌘S", "Settings"],
              ["Esc", "Go Back"],
              ["?", "Campaign List"],
            ].map(([key, desc]) => (
              <div key={key} className="flex items-center justify-between py-1.5">
                <span className="text-sm text-gray-400">{desc}</span>
                <kbd className="bg-gray-800 border border-gray-700 text-gray-300 text-xs px-2 py-0.5 rounded font-mono">{key}</kbd>
              </div>
            ))}
          </Section>
        </div>
      )}
    </div>
  );
}

function Section({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-gray-500">{icon}</span>
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

function StatusRow({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800/50 last:border-0">
      <span className="text-sm text-gray-300 capitalize">{label}</span>
      <div className="flex items-center gap-1.5">
        {ok ? (
          <><CheckCircle size={14} className="text-green-400" /><span className="text-xs text-green-400">Connected</span></>
        ) : (
          <><XCircle size={14} className="text-red-400" /><span className="text-xs text-red-400">Not configured</span></>
        )}
      </div>
    </div>
  );
}
