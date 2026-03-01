import { useState, useEffect } from "react";
import { ArrowLeft, BarChart2, GitBranch, Play, Pause, Copy, TrendingUp, Award } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";

const API = "/api/actp";

interface Props {
  campaignId: string;
  onBack: () => void;
  onCompare: () => void;
}

export function CampaignDetail({ campaignId, onBack, onCompare }: Props) {
  const [campaign, setCampaign] = useState<any>(null);
  const [rounds, setRounds] = useState<any[]>([]);
  const [creatives, setCreatives] = useState<any[]>([]);
  const [progress, setProgress] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"overview" | "rounds" | "creatives" | "analytics">("overview");

  useEffect(() => {
    Promise.all([
      fetch(`${API}/campaigns/${campaignId}`).then((r) => r.json()),
      fetch(`${API}/campaigns/${campaignId}/rounds`).then((r) => r.json()),
      fetch(`${API}/campaigns/${campaignId}/creatives`).then((r) => r.json()),
      fetch(`${API}/campaigns/${campaignId}/progress`).then((r) => r.json()),
    ]).then(([camp, rds, crs, prog]) => {
      setCampaign(camp);
      setRounds(rds.rounds || []);
      setCreatives(crs.creatives || []);
      setProgress(prog);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [campaignId]);

  async function handlePause() {
    await fetch(`${API}/campaigns/${campaignId}/pause`, { method: "POST" });
    setCampaign((c: any) => ({ ...c, status: "paused" }));
  }

  async function handleResume() {
    await fetch(`${API}/campaigns/${campaignId}/resume`, { method: "POST" });
    setCampaign((c: any) => ({ ...c, status: "active" }));
  }

  async function handleClone() {
    const res = await fetch(`${API}/campaigns/${campaignId}/clone`, { method: "POST" });
    const data = await res.json();
    if (data.campaign?.id) alert(`Cloned as: ${data.campaign.name}`);
  }

  if (loading) return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-gray-800 rounded animate-pulse" />
      <div className="h-40 bg-gray-800 rounded-xl animate-pulse" />
    </div>
  );

  if (!campaign) return (
    <div className="text-center py-20 text-gray-500">Campaign not found</div>
  );

  const winners = creatives.filter((c: any) => c.is_winner);
  const roundScores = rounds.map((r: any, i: number) => ({
    round: `R${r.round_number || i + 1}`,
    top_score: Math.max(...(creatives.filter((c: any) => c.round_id === r.id).map((c: any) => c.organic_score || 0)), 0),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white">{campaign.name}</h1>
            <div className="flex items-center gap-2 mt-1 text-sm text-gray-400">
              <span className="capitalize">{campaign.status}</span>
              <span>·</span>
              <span className="capitalize">{campaign.mode}</span>
              {campaign.offer_name && <><span>·</span><span>{campaign.offer_name}</span></>}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={onCompare} className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-2 rounded-lg text-sm transition-colors">
            <BarChart2 size={14} /> Compare
          </button>
          <button onClick={handleClone} className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 px-3 py-2 rounded-lg text-sm transition-colors">
            <Copy size={14} /> Clone
          </button>
          {campaign.status === "active" ? (
            <button onClick={handlePause} className="flex items-center gap-1.5 bg-yellow-600 hover:bg-yellow-500 text-white px-3 py-2 rounded-lg text-sm transition-colors">
              <Pause size={14} /> Pause
            </button>
          ) : (
            <button onClick={handleResume} className="flex items-center gap-1.5 bg-green-600 hover:bg-green-500 text-white px-3 py-2 rounded-lg text-sm transition-colors">
              <Play size={14} /> Resume
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      {progress && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex justify-between text-sm mb-2">
            <span className="text-gray-400">Campaign Progress</span>
            <span className="text-white font-medium">{progress.progress_pct || 0}%</span>
          </div>
          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${progress.progress_pct || 0}%` }}
            />
          </div>
          <div className="flex gap-6 mt-3 text-xs text-gray-500">
            <span>Round {progress.current_round || 1} of {progress.max_rounds || "?"}</span>
            <span>{progress.creatives_generated || 0} creatives</span>
            <span>{progress.winners_found || 0} winners</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800">
        {(["overview", "rounds", "creatives", "analytics"] as const).map((tab) => (
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

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard label="Total Rounds" value={rounds.length} icon={<GitBranch size={18} />} />
          <StatCard label="Total Creatives" value={creatives.length} icon={<BarChart2 size={18} />} />
          <StatCard label="Winners Found" value={winners.length} icon={<Award size={18} />} color="text-yellow-400" />

          {roundScores.length > 1 && (
            <div className="col-span-3 bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Score Trend by Round</h3>
              <ResponsiveContainer width="100%" height={160}>
                <LineChart data={roundScores}>
                  <XAxis dataKey="round" stroke="#6b7280" tick={{ fontSize: 12 }} />
                  <YAxis stroke="#6b7280" tick={{ fontSize: 12 }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
                  <Line type="monotone" dataKey="top_score" stroke="#6366f1" strokeWidth={2} dot={{ fill: "#6366f1" }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Rounds Tab */}
      {activeTab === "rounds" && (
        <div className="space-y-2">
          {rounds.length === 0 && <EmptyState message="No rounds yet" />}
          {rounds.map((round: any) => (
            <div key={round.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium text-white">Round {round.round_number}</span>
                  <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${round.status === "completed" ? "bg-blue-500/20 text-blue-400" : "bg-green-500/20 text-green-400"}`}>
                    {round.status}
                  </span>
                </div>
                <span className="text-xs text-gray-500">{new Date(round.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Creatives Tab */}
      {activeTab === "creatives" && (
        <div className="space-y-2">
          {creatives.length === 0 && <EmptyState message="No creatives yet" />}
          {creatives.map((creative: any) => (
            <div key={creative.id} className={`bg-gray-900 border rounded-xl p-4 ${creative.is_winner ? "border-yellow-500/40" : "border-gray-800"}`}>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {creative.is_winner && <Award size={14} className="text-yellow-400 flex-shrink-0" />}
                    <span className="text-sm font-medium text-white truncate">{creative.hook || "Untitled"}</span>
                  </div>
                  {creative.angle && <p className="text-xs text-gray-500 mt-0.5">{creative.angle}</p>}
                </div>
                <div className="text-right flex-shrink-0">
                  {creative.organic_score != null && (
                    <div className="text-sm font-bold text-indigo-400">{creative.organic_score.toFixed(1)}</div>
                  )}
                  <div className="text-xs text-gray-600">{creative.generation_source}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === "analytics" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {creatives.filter((c: any) => c.organic_score != null).slice(0, 8).map((c: any) => (
              <div key={c.id} className="bg-gray-900 border border-gray-800 rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-indigo-400">{c.organic_score?.toFixed(1)}</div>
                <div className="text-xs text-gray-500 mt-1 truncate">{c.hook?.slice(0, 20) || c.id.slice(0, 8)}</div>
              </div>
            ))}
          </div>
          {creatives.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Score Distribution</h3>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={creatives.filter((c: any) => c.organic_score != null).map((c: any, i: number) => ({ name: `C${i + 1}`, score: c.organic_score }))}>
                  <XAxis dataKey="name" stroke="#6b7280" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
                  <Bar dataKey="score" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color = "text-white" }: { label: string; value: number; icon: React.ReactNode; color?: string }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-3">
      <div className="text-gray-500">{icon}</div>
      <div>
        <div className={`text-2xl font-bold ${color}`}>{value}</div>
        <div className="text-xs text-gray-500">{label}</div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="text-center py-12 text-gray-500 text-sm">{message}</div>;
}
