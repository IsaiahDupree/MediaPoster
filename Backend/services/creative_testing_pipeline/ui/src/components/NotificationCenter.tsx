import { useState, useEffect } from "react";
import { Bell, CheckCheck, AlertTriangle, TrendingUp, Award, X } from "lucide-react";

const API = "/api/actp";

interface Notification {
  id: string;
  type: "winner" | "anomaly" | "round_complete" | "error" | "info";
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  campaign_id?: string;
}

const TYPE_CONFIG = {
  winner: { icon: Award, color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20" },
  anomaly: { icon: AlertTriangle, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
  round_complete: { icon: TrendingUp, color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" },
  error: { icon: X, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
  info: { icon: Bell, color: "text-gray-400", bg: "bg-gray-800 border-gray-700" },
};

export function NotificationCenter() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  useEffect(() => {
    // Load DLQ items and stale campaigns as notification sources
    Promise.all([
      fetch(`${API}/monitoring/dlq`).then((r) => r.json()).catch(() => ({ items: [] })),
      fetch(`${API}/monitoring/stale`).then((r) => r.json()).catch(() => ({ campaigns: [] })),
    ]).then(([dlq, stale]) => {
      const notifs: Notification[] = [];

      for (const item of (dlq.items || [])) {
        notifs.push({
          id: item.id || Math.random().toString(),
          type: "error",
          title: "Failed Job",
          message: `${item.job_type}: ${item.error}`,
          timestamp: item.created_at || new Date().toISOString(),
          read: false,
        });
      }

      for (const camp of (stale.campaigns || [])) {
        notifs.push({
          id: `stale-${camp.id}`,
          type: "anomaly",
          title: "Stale Campaign",
          message: `"${camp.name}" hasn't progressed in 72+ hours`,
          timestamp: camp.updated_at || new Date().toISOString(),
          read: false,
          campaign_id: camp.id,
        });
      }

      setNotifications(notifs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()));
      setLoading(false);
    });
  }, []);

  const markAllRead = () => setNotifications((n) => n.map((x) => ({ ...x, read: true })));
  const dismiss = (id: string) => setNotifications((n) => n.filter((x) => x.id !== id));

  const filtered = filter === "unread" ? notifications.filter((n) => !n.read) : notifications;
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Notifications</h1>
          {unreadCount > 0 && (
            <span className="bg-indigo-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {(["all", "unread"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors capitalize ${
                filter === f ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {f}
            </button>
          ))}
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white bg-gray-800 transition-colors"
            >
              <CheckCheck size={14} /> Mark all read
            </button>
          )}
        </div>
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-gray-800 rounded-xl animate-pulse" />)}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <Bell size={40} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium text-gray-400">No notifications</p>
          <p className="text-sm mt-1">You're all caught up</p>
        </div>
      )}

      <div className="space-y-2">
        {filtered.map((notif) => {
          const cfg = TYPE_CONFIG[notif.type] || TYPE_CONFIG.info;
          const Icon = cfg.icon;
          return (
            <div
              key={notif.id}
              className={`flex items-start gap-3 p-4 rounded-xl border transition-all ${cfg.bg} ${!notif.read ? "opacity-100" : "opacity-60"}`}
            >
              <Icon size={18} className={`${cfg.color} flex-shrink-0 mt-0.5`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium text-white">{notif.title}</p>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {new Date(notif.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">{notif.message}</p>
              </div>
              <button
                onClick={() => dismiss(notif.id)}
                className="text-gray-600 hover:text-gray-400 transition-colors flex-shrink-0"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
