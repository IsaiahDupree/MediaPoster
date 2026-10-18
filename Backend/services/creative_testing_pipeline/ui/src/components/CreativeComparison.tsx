import { useState, useEffect } from "react";
import { ArrowLeft, Award, TrendingUp, Eye } from "lucide-react";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";

const API = "/api/actp";

interface Props {
  campaignId: string;
  onBack: () => void;
}

const METRIC_LABELS: Record<string, string> = {
  organic_score: "Organic Score",
  ad_score: "Ad Score",
  views: "Views",
  likes: "Likes",
  shares: "Shares",
  comments: "Comments",
};

export function CreativeComparison({ campaignId, onBack }: Props) {
  const [creatives, setCreatives] = useState<any[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/campaigns/${campaignId}/creatives`)
      .then((r) => r.json())
      .then((data) => {
        const all = data.creatives || [];
        setCreatives(all);
        // Pre-select top 3 by organic_score
        const top = [...all]
          .sort((a: any, b: any) => (b.organic_score || 0) - (a.organic_score || 0))
          .slice(0, 3)
          .map((c: any) => c.id);
        setSelected(top);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [campaignId]);

  const toggleSelect = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 4 ? [...prev, id] : prev
    );
  };

  const selectedCreatives = creatives.filter((c: any) => selected.includes(c.id));

  const radarData = ["organic_score", "ad_score"].map((metric) => ({
    metric: METRIC_LABELS[metric] || metric,
    ...Object.fromEntries(
      selectedCreatives.map((c: any) => [c.id.slice(0, 8), Math.min(c[metric] || 0, 100)])
    ),
  }));

  const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444"];

  if (loading) return (
    <div className="space-y-4">
      <div className="h-8 w-48 bg-gray-800 rounded animate-pulse" />
      <div className="h-64 bg-gray-800 rounded-xl animate-pulse" />
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button onClick={onBack} className="text-gray-400 hover:text-white transition-colors">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Creative Comparison</h1>
          <p className="text-sm text-gray-400 mt-0.5">Select up to 4 creatives to compare</p>
        </div>
      </div>

      {/* Creative Selector */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
        {creatives.map((c: any, i: number) => {
          const isSelected = selected.includes(c.id);
          const colorIdx = selected.indexOf(c.id);
          return (
            <button
              key={c.id}
              onClick={() => toggleSelect(c.id)}
              className={`text-left p-3 rounded-xl border transition-all ${
                isSelected
                  ? "border-indigo-500 bg-indigo-500/10"
                  : "border-gray-800 bg-gray-900 hover:border-gray-600"
              }`}
            >
              <div className="flex items-start justify-between gap-1">
                <span className="text-xs font-medium text-white line-clamp-2">{c.hook || `Creative ${i + 1}`}</span>
                {c.is_winner && <Award size={12} className="text-yellow-400 flex-shrink-0 mt-0.5" />}
              </div>
              {c.organic_score != null && (
                <div className="mt-2 flex items-center gap-1">
                  <TrendingUp size={11} className="text-indigo-400" />
                  <span className="text-xs font-bold text-indigo-400">{c.organic_score.toFixed(1)}</span>
                </div>
              )}
              {isSelected && (
                <div
                  className="mt-1 h-1 rounded-full"
                  style={{ backgroundColor: COLORS[colorIdx] || "#6366f1" }}
                />
              )}
            </button>
          );
        })}
      </div>

      {selectedCreatives.length === 0 && (
        <div className="text-center py-12 text-gray-500 text-sm">Select creatives above to compare</div>
      )}

      {selectedCreatives.length > 0 && (
        <>
          {/* Score Comparison Table */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <div className="p-4 border-b border-gray-800">
              <h3 className="text-sm font-medium text-white">Score Comparison</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left p-3 text-gray-500 font-medium">Metric</th>
                    {selectedCreatives.map((c: any, i: number) => (
                      <th key={c.id} className="text-right p-3 font-medium" style={{ color: COLORS[i] }}>
                        {c.hook?.slice(0, 20) || c.id.slice(0, 8)}
                        {c.is_winner && " 🏆"}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {["organic_score", "ad_score", "generation_source", "angle"].map((metric) => (
                    <tr key={metric} className="border-b border-gray-800/50">
                      <td className="p-3 text-gray-400">{METRIC_LABELS[metric] || metric.replace(/_/g, " ")}</td>
                      {selectedCreatives.map((c: any) => (
                        <td key={c.id} className="p-3 text-right text-white">
                          {typeof c[metric] === "number" ? c[metric].toFixed(1) : (c[metric] || "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Radar Chart */}
          {selectedCreatives.length >= 2 && radarData.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <h3 className="text-sm font-medium text-gray-400 mb-4">Performance Radar</h3>
              <ResponsiveContainer width="100%" height={240}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis dataKey="metric" tick={{ fill: "#9ca3af", fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8 }} />
                  {selectedCreatives.map((c: any, i: number) => (
                    <Radar
                      key={c.id}
                      name={c.hook?.slice(0, 15) || c.id.slice(0, 8)}
                      dataKey={c.id.slice(0, 8)}
                      stroke={COLORS[i]}
                      fill={COLORS[i]}
                      fillOpacity={0.1}
                    />
                  ))}
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Winner Badge */}
          {selectedCreatives.some((c: any) => c.is_winner) && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 flex items-center gap-3">
              <Award size={20} className="text-yellow-400" />
              <div>
                <p className="text-sm font-medium text-yellow-300">Winner Identified</p>
                <p className="text-xs text-yellow-500 mt-0.5">
                  {selectedCreatives.filter((c: any) => c.is_winner).map((c: any) => c.hook?.slice(0, 40)).join(", ")}
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
