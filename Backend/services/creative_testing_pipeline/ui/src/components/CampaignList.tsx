import { useState, useEffect } from "react";
import { Search, Plus, Play, Pause, Archive, ChevronRight, TrendingUp } from "lucide-react";

const API = "/api/actp";

interface Campaign {
  id: string;
  name: string;
  status: string;
  mode: string;
  offer_name?: string;
  current_round?: number;
  created_at: string;
}

interface Props {
  onSelect: (id: string) => void;
  onNew: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-500/20 text-green-400 border border-green-500/30",
  paused: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  draft: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
  completed: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  failed: "bg-red-500/20 text-red-400 border border-red-500/30",
};

export function CampaignList({ onSelect, onNew }: Props) {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCampaigns();
  }, [statusFilter]);

  async function fetchCampaigns() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "50", offset: "0" });
      if (statusFilter !== "all") params.set("status", statusFilter);
      const res = await fetch(`${API}/campaigns?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setCampaigns(data.campaigns || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function bulkAction(action: "pause" | "resume" | "archive", ids: string[]) {
    await fetch(`${API}/campaigns/bulk/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ campaign_ids: ids }),
    });
    fetchCampaigns();
  }

  const filtered = campaigns.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    (c.offer_name || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Campaigns</h1>
          <p className="text-sm text-gray-400 mt-1">{campaigns.length} total</p>
        </div>
        <button
          onClick={onNew}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Campaign
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search campaigns..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        {["all", "active", "paused", "draft", "completed"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              statusFilter === s ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
            }`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Loading / Error */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}
      {error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 text-red-400 text-sm">
          Failed to load campaigns: {error}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filtered.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <TrendingUp size={40} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium text-gray-400">No campaigns yet</p>
          <p className="text-sm mt-1">Create your first campaign to start testing creatives</p>
          <button
            onClick={onNew}
            className="mt-4 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Create Campaign
          </button>
        </div>
      )}

      {/* Campaign List */}
      {!loading && !error && filtered.length > 0 && (
        <div className="space-y-2">
          {filtered.map((campaign) => (
            <button
              key={campaign.id}
              onClick={() => onSelect(campaign.id)}
              className="w-full text-left bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-gray-700 rounded-xl p-4 transition-all group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-white truncate">{campaign.name}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[campaign.status] || STATUS_COLORS.draft}`}>
                        {campaign.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      {campaign.offer_name && <span>{campaign.offer_name}</span>}
                      <span className="capitalize">{campaign.mode}</span>
                      {campaign.current_round && <span>Round {campaign.current_round}</span>}
                      <span>{new Date(campaign.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                </div>
                <ChevronRight size={16} className="text-gray-600 group-hover:text-gray-400 transition-colors flex-shrink-0" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
