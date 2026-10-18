import { useState } from "react";
import { CampaignList } from "./components/CampaignList";
import { CampaignDetail } from "./components/CampaignDetail";
import { CreativeComparison } from "./components/CreativeComparison";
import { CreateCampaignWizard } from "./components/CreateCampaignWizard";
import { NotificationCenter } from "./components/NotificationCenter";
import { SettingsPage } from "./components/SettingsPage";

type View = "list" | "detail" | "compare" | "create" | "settings" | "notifications";

export default function App() {
  const [view, setView] = useState<View>("list");
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);

  const handleSelectCampaign = (id: string) => {
    setSelectedCampaignId(id);
    setView("detail");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "?" && !e.shiftKey) setView("list");
    if (e.key === "n" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setView("create"); }
    if (e.key === "s" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); setView("settings"); }
    if (e.key === "Escape") setView("list");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100" onKeyDown={handleKeyDown} tabIndex={0}>
      <nav className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-lg text-white tracking-tight">ACTP</span>
          <div className="flex gap-1">
            {(["list", "create", "settings", "notifications"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  view === v ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                {v === "list" ? "Campaigns" : v === "create" ? "New Campaign" : v === "notifications" ? "Notifications" : "Settings"}
              </button>
            ))}
          </div>
        </div>
        <div className="text-xs text-gray-500">⌘N new · ⌘S settings · Esc back</div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {view === "list" && <CampaignList onSelect={handleSelectCampaign} onNew={() => setView("create")} />}
        {view === "detail" && selectedCampaignId && (
          <CampaignDetail
            campaignId={selectedCampaignId}
            onBack={() => setView("list")}
            onCompare={() => setView("compare")}
          />
        )}
        {view === "compare" && selectedCampaignId && (
          <CreativeComparison campaignId={selectedCampaignId} onBack={() => setView("detail")} />
        )}
        {view === "create" && <CreateCampaignWizard onDone={() => setView("list")} onCancel={() => setView("list")} />}
        {view === "settings" && <SettingsPage />}
        {view === "notifications" && <NotificationCenter />}
      </main>
    </div>
  );
}
