import { useState } from "react";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Boxes,
  CheckCircle,
  ChevronRight,
  Code2,
  Database,
  ExternalLink,
  FileJson,
  Layers,
  Radio,
  Search,
  Server,
  Sparkles,
  Star,
  Wrench,
} from "lucide-react";
import pipelineData from "../../../data/output.json";

const ACCENT_GOLD = "#fbbf24";
const REPOS = pipelineData.repos ?? [];
const MODELS = pipelineData.models ?? [];
const TOOLS_SERVICES = pipelineData.toolsServices ?? [];
const PAPERS = pipelineData.papers ?? [];
const HEALTH = pipelineData.health ?? [];

const SIGNAL_COLORS = {
  High: { dot: "#34d399", text: "#6ee7b7" },
  Medium: { dot: "#fbbf24", text: "#fde68a" },
  Low: { dot: "#64748b", text: "#94a3b8" },
};

function getIsoWeekLabel(value) {
  const input = value ? new Date(value) : new Date();
  if (Number.isNaN(input.getTime())) return "WEEK —";
  const date = new Date(Date.UTC(input.getFullYear(), input.getMonth(), input.getDate()));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
  return `WEEK ${String(week).padStart(2, "0")} · ${date.getUTCFullYear()}`;
}

function Tag({ children }) {
  return (
    <span
      className="ai-mono inline-flex items-center px-2 py-0.5 border"
      style={{
        fontSize: 9,
        letterSpacing: "0.12em",
        color: "#94a3b8",
        borderColor: "rgba(51,65,85,0.6)",
      }}
    >
      {children}
    </span>
  );
}

function SectionHeader({ title, sub, action }) {
  return (
    <div className="flex items-center justify-between mb-4 gap-3">
      <div>
        <h2
          className="ai-mono"
          style={{ fontSize: 12, letterSpacing: "0.2em", color: "#cbd5e1", fontWeight: 600 }}
        >
          {title}
        </h2>
        {sub && (
          <div className="ai-mono mt-1" style={{ fontSize: 9, letterSpacing: "0.16em", color: "#475569" }}>
            {sub}
          </div>
        )}
      </div>
      {action}
    </div>
  );
}

function TextButton({ children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="ai-mono inline-flex items-center gap-1.5 transition-colors"
      style={{ fontSize: 10, letterSpacing: "0.12em", color: ACCENT_GOLD }}
    >
      {children}
      <ArrowRight size={12} />
    </button>
  );
}

function CircularScore({ score }) {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="relative" style={{ width: 52, height: 52 }}>
      <svg width="52" height="52" viewBox="0 0 52 52" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="26" cy="26" r={radius} fill="none" stroke="#1c1f3f" strokeWidth="3" />
        <circle
          cx="26"
          cy="26"
          r={radius}
          fill="none"
          stroke={ACCENT_GOLD}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (circumference * score) / 100}
        />
      </svg>
      <div
        className="ai-mono absolute inset-0 flex items-center justify-center"
        style={{ fontSize: 12, color: ACCENT_GOLD }}
      >
        {score}
      </div>
    </div>
  );
}

function TakeawayList({ takeaways, limit }) {
  return (
    <ul className="space-y-1.5">
      {(takeaways ?? []).slice(0, limit).map((takeaway) => (
        <li key={takeaway} className="flex items-start gap-2">
          <ChevronRight size={10} className="shrink-0 mt-1" style={{ color: ACCENT_GOLD }} />
          <span style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.5 }}>{takeaway}</span>
        </li>
      ))}
    </ul>
  );
}

function StatsBar() {
  return (
    <div className="grid grid-cols-4 border mb-8" style={{ borderColor: "#1c1f3f", backgroundColor: "#0c0e26" }}>
      {(pipelineData.stats ?? []).map((stat, index) => (
        <div
          key={stat.label}
          className="px-6 py-5"
          style={{ borderRight: index < 3 ? "1px solid #1c1f3f" : "none" }}
        >
          <div className="ai-mono mb-2" style={{ fontSize: 10, letterSpacing: "0.18em", color: "#64748b" }}>
            {stat.label}
          </div>
          <div
            className="ai-mono mb-0.5"
            style={{ fontSize: 30, color: stat.accent ? ACCENT_GOLD : "#f1f5f9", fontWeight: 500 }}
          >
            {stat.value}
          </div>
          <div style={{ fontSize: 11, color: "#64748b" }}>{stat.sub}</div>
        </div>
      ))}
    </div>
  );
}

function SnapshotList({ title, icon: Icon, items, getTitle, getMeta, getSummary, onNavigate }) {
  return (
    <div className="border p-4 h-full" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
      <div className="flex items-center justify-between mb-3">
        <div className="ai-mono flex items-center gap-2" style={{ fontSize: 11, color: "#cbd5e1", letterSpacing: "0.14em" }}>
          <Icon size={14} style={{ color: "#67e8f9" }} />
          {title}
        </div>
        <TextButton onClick={onNavigate}>VIEW ALL</TextButton>
      </div>
      <div className="space-y-2.5">
        {items.slice(0, 3).map((item) => (
          <div key={getTitle(item)} className="border-t pt-2.5" style={{ borderColor: "rgba(28,31,63,0.8)" }}>
            <div className="truncate" style={{ fontSize: 12, color: "#e2e8f0" }}>{getTitle(item)}</div>
            {getSummary && <div className="truncate mt-1" style={{ fontSize: 10, color: "#94a3b8" }}>{getSummary(item)}</div>}
            <div className="ai-mono truncate mt-1" style={{ fontSize: 9, color: "#64748b" }}>{getMeta(item)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FeaturedResearch({ paper, onNavigate }) {
  if (!paper) return null;
  return (
    <div className="border p-6 mb-4" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
      <div className="grid grid-cols-4 gap-6 items-center">
        <div className="col-span-3 min-w-0">
          <div className="ai-mono mb-3" style={{ fontSize: 10, color: ACCENT_GOLD, letterSpacing: "0.18em" }}>
            FEATURED RESEARCH PICK
          </div>
          <h3 className="leading-snug mb-2" style={{ fontSize: 18, color: "#f1f5f9", fontWeight: 600 }}>{paper.title}</h3>
          <div className="ai-mono mb-3" style={{ fontSize: 10, color: "#64748b" }}>{paper.date} · {paper.org}</div>
          <TakeawayList takeaways={paper.takeaways} limit={2} />
          <div className="flex flex-wrap items-center gap-2 mt-4">
            {paper.priority && <Tag>{paper.priority}</Tag>}
            {(paper.tags ?? []).slice(0, 2).map((tag) => <Tag key={tag}>{tag.toUpperCase()}</Tag>)}
          </div>
        </div>
        <div className="h-full pl-6 border-l flex flex-col items-center justify-center text-center" style={{ borderColor: "rgba(28,31,63,0.8)" }}>
          <CircularScore score={paper.researchScore} />
          <div className="ai-mono mt-2" style={{ fontSize: 8, color: "#475569", letterSpacing: "0.12em" }}>RESEARCH SCORE</div>
          <div className="mt-5 flex flex-col gap-3 items-center">
            <TextButton onClick={onNavigate}>EXPLORE RESEARCH</TextButton>
            {paper.url && (
              <a href={paper.url} target="_blank" rel="noreferrer" className="ai-mono inline-flex items-center gap-1" style={{ fontSize: 10, color: "#67e8f9" }}>
                OPEN PAPER <ExternalLink size={11} />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function WeeklySnapshot({ onNavigate }) {
  return (
    <div>
      <StatsBar />
      <SectionHeader title="THIS WEEK" sub="A DECISION-FIRST VIEW OF THE SIGNALS WORTH OPENING" />
      <FeaturedResearch paper={PAPERS[0]} onNavigate={() => onNavigate("research")} />
      <div className="grid grid-cols-3 gap-4">
        <SnapshotList title="TRENDING REPOS" icon={Boxes} items={REPOS} getTitle={(item) => item.name} getSummary={(item) => item.desc} getMeta={(item) => `${item.stars} stars · ${item.bestFor}`} onNavigate={() => onNavigate("repos")} />
        <SnapshotList title="MODEL RELEASES" icon={Sparkles} items={MODELS} getTitle={(item) => item.name} getMeta={(item) => `${item.org} · ${item.date}`} onNavigate={() => onNavigate("releases")} />
        <SnapshotList title="TOOLS & SERVICES" icon={Wrench} items={TOOLS_SERVICES} getTitle={(item) => item.name} getMeta={(item) => `${item.org} · ${item.date}`} onNavigate={() => onNavigate("releases")} />
      </div>
    </div>
  );
}

function PaperCard({ paper }) {
  const [open, setOpen] = useState(false);
  const priorityColors = {
    READ: "#67e8f9",
    EXPERIMENT: "#f8c74e",
    SHARE: "#c084fc",
    WATCH: "#94a3b8",
  };
  const priorityColor = priorityColors[paper.priority] ?? priorityColors.READ;
  return (
    <div className="border" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
      <button type="button" onClick={() => setOpen(!open)} className="w-full text-left px-6 py-5">
        <div className="flex items-start gap-5">
          <div className="flex-1 min-w-0">
            <h3 className="leading-snug mb-2" style={{ fontSize: 15, color: "#f1f5f9", fontWeight: 500 }}>{paper.title}</h3>
            <div className="ai-mono mb-3" style={{ fontSize: 10, color: "#64748b" }}>{paper.authors} · {paper.org} · {paper.date}</div>
            <TakeawayList takeaways={paper.takeaways} />
            <div className="flex items-center gap-2 flex-wrap mt-3">
              {paper.priority && <Tag>{paper.priority}</Tag>}
              {paper.hasCode && <Tag><Code2 size={10} className="mr-1" />CODE</Tag>}
              {(paper.tags ?? []).map((tag) => <Tag key={tag}>{tag.toUpperCase()}</Tag>)}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <CircularScore score={paper.researchScore} />
            <ChevronRight size={16} style={{ color: "#475569", transform: open ? "rotate(90deg)" : "none" }} />
          </div>
        </div>
      </button>
      {open && (
        <div className="px-6 pb-6 pt-5 border-t" style={{ borderColor: "rgba(28,31,63,0.7)" }}>
          <div className="ai-mono mb-2" style={{ fontSize: 10, color: "#475569", letterSpacing: "0.18em" }}>ABSTRACT</div>
          <p className="mb-6" style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.65 }}>{paper.abstract}</p>
          <div className="ai-mono mb-3" style={{ fontSize: 10, color: "#475569", letterSpacing: "0.18em" }}>RESEARCH SIGNALS</div>
          <div className="grid grid-cols-4 gap-3">
            {Object.entries(paper.researchSignals ?? {}).map(([label, level]) => {
              const style = SIGNAL_COLORS[level] ?? SIGNAL_COLORS.Low;
              return (
                <div key={label} className="border p-3" style={{ borderColor: "#1c1f3f" }}>
                  <div className="ai-mono mb-2" style={{ fontSize: 9, color: "#64748b", textTransform: "uppercase" }}>{label}</div>
                  <div className="flex items-center gap-2"><span className="rounded-full" style={{ width: 8, height: 8, backgroundColor: style.dot }} /><span style={{ fontSize: 12, color: style.text }}>{level}</span></div>
                </div>
              );
            })}
          </div>
          {(paper.actionItems ?? []).length > 0 && (
            <div className="mt-6">
              <div className="ai-mono mb-3" style={{ fontSize: 10, color: "#475569", letterSpacing: "0.18em" }}>RECOMMENDED ACTIONS</div>
              <TakeawayList takeaways={paper.actionItems} />
            </div>
          )}
          {paper.url && <a href={paper.url} target="_blank" rel="noreferrer" className="ai-mono inline-flex items-center gap-2 mt-5 px-3 py-2 border" style={{ fontSize: 11, color: "#0a0a1a", backgroundColor: ACCENT_GOLD, borderColor: ACCENT_GOLD, fontWeight: 700 }}>OPEN PAPER <ExternalLink size={12} /></a>}
        </div>
      )}
    </div>
  );
}

function ResearchTab({ weekLabel }) {
  return (
    <div>
      <SectionHeader title="RESEARCH" sub={`7-DAY WINDOW · 14-DAY BACKFILL ONLY IF NEEDED · ${weekLabel}`} />
      <div className="space-y-3">{PAPERS.map((paper) => <PaperCard key={paper.title} paper={paper} />)}</div>
    </div>
  );
}

function RepoList({ items = REPOS }) {
  const [openRepo, setOpenRepo] = useState(items[0]?.name ?? "");
  return (
    <div className="border" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
      {items.map((repo, index) => (
        <div key={repo.name} className="px-4 py-3" style={{ borderBottom: index < items.length - 1 ? "1px solid #1c1f3f" : "none" }}>
          <button type="button" onClick={() => setOpenRepo(openRepo === repo.name ? "" : repo.name)} className="w-full text-left">
            <div className="flex justify-between gap-3"><div className="ai-mono truncate" style={{ fontSize: 12, color: "#e2e8f0" }}>{repo.name}</div><div className="ai-mono shrink-0" style={{ fontSize: 10, color: "#64748b" }}><Star size={10} className="inline mr-1" />{repo.stars}</div></div>
            <div className="truncate mt-1" style={{ fontSize: 11, color: "#64748b" }}>{repo.desc}</div>
          </button>
          {openRepo === repo.name && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(28,31,63,0.7)" }}>
              <div className="flex flex-wrap gap-2 mb-3">{repo.language && <Tag>{repo.language.toUpperCase()}</Tag>}{repo.lastUpdated && <Tag>UPDATED {repo.lastUpdated.toUpperCase()}</Tag>}{repo.license && <Tag>{repo.license.toUpperCase()}</Tag>}</div>
              <TakeawayList takeaways={repo.bullets ?? [repo.desc]} limit={3} />
              <div className="flex flex-wrap gap-4 mt-4">{repo.latestReleaseUrl && <a href={repo.latestReleaseUrl} target="_blank" rel="noreferrer" className="ai-mono" style={{ fontSize: 10, color: "#67e8f9" }}>RELEASE <ExternalLink size={11} className="inline" /></a>}{repo.url && <a href={repo.url} target="_blank" rel="noreferrer" className="ai-mono" style={{ fontSize: 10, color: ACCENT_GOLD }}>OPEN REPO <ExternalLink size={11} className="inline" /></a>}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ReposTab() {
  return <div><SectionHeader title="REPOS" sub="TRENDING OPEN-SOURCE PROJECTS · EXPAND FOR WHY THEY MATTER" /><RepoList /></div>;
}

function ReleaseList({ items, accentColor, emptyLabel }) {
  const [openItem, setOpenItem] = useState(items[0]?.name ?? "");
  if (!items.length) return <div className="border p-4" style={{ borderColor: "#1c1f3f", color: "#64748b" }}>{emptyLabel}</div>;
  return (
    <div className="border" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
      {items.map((item, index) => (
        <div key={`${item.name}-${item.url}`} className="px-4 py-3" style={{ borderBottom: index < items.length - 1 ? "1px solid #1c1f3f" : "none" }}>
          <button type="button" onClick={() => setOpenItem(openItem === item.name ? "" : item.name)} className="w-full text-left">
            <div className="flex justify-between gap-3"><div className="truncate" style={{ fontSize: 13, color: "#f1f5f9" }}>{item.name}</div><div className="ai-mono shrink-0" style={{ fontSize: 10, color: "#64748b" }}>{item.date}</div></div>
            <div className="truncate mt-1" style={{ fontSize: 11, color: "#64748b" }}>{item.note}</div>
          </button>
          {openItem === item.name && <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(28,31,63,0.7)" }}><div className="flex gap-2 mb-3"><Tag>{item.org.toUpperCase()}</Tag><Tag>{item.tag}</Tag></div><div style={{ fontSize: 12, color: "#94a3b8" }}>{item.note}</div><div className="flex flex-wrap gap-3 mt-3">{(item.links ?? []).map((link) => <a key={`${item.name}-${link.url}`} href={link.url} target="_blank" rel="noreferrer" className="ai-mono" style={{ fontSize: 10, color: accentColor }}>{link.label.toUpperCase()} <ExternalLink size={11} className="inline" /></a>)}</div></div>}
        </div>
      ))}
    </div>
  );
}

function ReleasesTab() {
  return (
    <div className="grid grid-cols-2 gap-6">
      <div><SectionHeader title="MODEL RELEASES" sub="RECENT TRUSTED ANNOUNCEMENTS" /><ReleaseList items={MODELS} accentColor={ACCENT_GOLD} emptyLabel="No recent model releases found." /></div>
      <div><SectionHeader title="TOOLS & SERVICES" sub="RECENT TRUSTED ANNOUNCEMENTS" /><ReleaseList items={TOOLS_SERVICES} accentColor="#67e8f9" emptyLabel="No recent tool or service releases found." /></div>
    </div>
  );
}

function ComingSoonPanel({ title, icon: Icon, copy }) {
  return (
    <div className="border p-6" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
      <Icon size={20} style={{ color: "#67e8f9" }} />
      <div className="ai-mono mt-5 mb-2" style={{ fontSize: 12, color: "#e2e8f0", letterSpacing: "0.16em" }}>{title}</div>
      <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.6 }}>{copy}</div>
      <div className="ai-mono mt-6" style={{ fontSize: 10, color: ACCENT_GOLD, letterSpacing: "0.14em" }}>COMING SOON</div>
    </div>
  );
}

function SignalsTab() {
  return (
    <div>
      <SectionHeader title="SIGNALS" sub="PLACEHOLDERS FOR FUTURE CURATED SIGNAL STREAMS" />
      <div className="grid grid-cols-2 gap-4">
        <ComingSoonPanel title="AI PULSE" icon={Radio} copy="A curated enterprise AI news stream will surface credible engineering, product, and applied-AI updates after source quality and ranking are tuned." />
        <ComingSoonPanel title="SOCIAL PULSE" icon={Activity} copy="A verified-source social signal stream will highlight high-value conversations after the collection and credibility workflow is ready." />
      </div>
    </div>
  );
}

function healthDetail(entry) {
  if (entry.source === "papers") return `${entry.fetch_diagnostics?.displayed_count ?? 0} displayed · ${entry.fetch_diagnostics?.retry_count ?? 0} retries`;
  if (entry.source === "rss") return `${entry.fetch_diagnostics?.feeds_requested ?? 0} feeds · round-robin selection`;
  if (entry.source === "github") return `${entry.search_diagnostics?.total_unique_candidates ?? 0} candidates reviewed`;
  if (entry.source === "model_tools") return `${entry.extraction_diagnostics?.classified ?? 0} classified · ${entry.extraction_diagnostics?.selection_diagnostics?.rejected_near_duplicate ?? 0} collapsed`;
  return "latest run";
}

function PipelineTab() {
  const fetchers = [
    { name: "Papers", sub: "arXiv · ranked research", icon: BookOpen },
    { name: "Repos", sub: "GitHub · dynamic discovery", icon: Boxes },
    { name: "RSS", sub: "official feeds · round robin", icon: Radio },
    { name: "Releases", sub: "models · tools · services", icon: Sparkles },
  ];
  const shared = [
    { name: "Collect", icon: Database },
    { name: "Normalize", icon: Search },
    { name: "Score & gate", icon: Layers },
    { name: "Write JSON", icon: FileJson },
    { name: "Render", icon: Server },
  ];
  return (
    <div className="space-y-8">
      <div>
        <SectionHeader title="PIPELINE" sub="CURRENT MULTI-SOURCE ARTIFACT FLOW" />
        <div className="border p-5" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
          <div className="grid grid-cols-4 gap-3">
            {fetchers.map(({ name, sub, icon: Icon }) => <div key={name} className="border p-4" style={{ borderColor: "#1c1f3f" }}><Icon size={16} style={{ color: "#67e8f9" }} /><div className="mt-3" style={{ color: "#f1f5f9", fontSize: 13 }}>{name}</div><div className="ai-mono mt-1" style={{ color: "#64748b", fontSize: 9 }}>{sub.toUpperCase()}</div></div>)}
          </div>
          <div className="ai-mono text-center my-4" style={{ fontSize: 10, color: "#475569" }}>PARALLEL FETCH · SPECIALIZED WORKFLOWS · SHARED ARTIFACT CONTRACT</div>
          <div className="flex items-center gap-2">
            {shared.map(({ name, icon: Icon }, index) => <div key={name} className="contents"><div className="flex-1 border px-3 py-3 text-center" style={{ borderColor: "#1c1f3f" }}><Icon size={14} className="mx-auto" style={{ color: index === shared.length - 1 ? "#6ee7b7" : ACCENT_GOLD }} /><div className="ai-mono mt-2" style={{ fontSize: 9, color: "#94a3b8" }}>{name.toUpperCase()}</div></div>{index < shared.length - 1 && <ArrowRight size={13} style={{ color: "#334155" }} />}</div>)}
          </div>
        </div>
      </div>
      <div>
        <SectionHeader title="LATEST SOURCE HEALTH" sub="LIVE DATA FROM DATA/HEALTH.JSON" />
        <div className="grid grid-cols-4 gap-3">
          {HEALTH.map((entry) => <div key={entry.source} className="border p-4" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}><div className="flex items-center justify-between"><div className="ai-mono" style={{ fontSize: 11, color: "#cbd5e1" }}>{entry.source.toUpperCase()}</div><CheckCircle size={13} style={{ color: entry.status === "ok" ? "#34d399" : "#f87171" }} /></div><div className="ai-mono mt-4" style={{ fontSize: 24, color: "#f1f5f9" }}>{entry.item_count}</div><div className="ai-mono mt-1" style={{ fontSize: 9, color: "#64748b" }}>{healthDetail(entry)}</div><div className="ai-mono mt-3" style={{ fontSize: 9, color: "#475569" }}>{entry.duration_ms} MS</div></div>)}
        </div>
      </div>
      <div className="border p-4 flex items-center gap-3" style={{ borderColor: "#1c1f3f", backgroundColor: "#0e1130" }}><FileJson size={16} style={{ color: ACCENT_GOLD }} /><div><div style={{ fontSize: 13, color: "#e2e8f0" }}>Stable frontend contract</div><div className="ai-mono mt-1" style={{ fontSize: 9, color: "#64748b" }}>DATA/OUTPUT.JSON · PAPERS · REPOS · MODELS · TOOLSERVICES · BLOGS · SOCIALPOSTS</div></div></div>
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState("snapshot");
  const generatedAt = pipelineData.generatedAt;
  const refreshedAt = generatedAt
    ? new Date(generatedAt).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "NOT YET GENERATED";
  const weekLabel = getIsoWeekLabel(generatedAt);
  const tabs = [
    { id: "snapshot", label: "Weekly Snapshot" },
    { id: "research", label: "Research" },
    { id: "repos", label: "Repos" },
    { id: "releases", label: "Releases" },
    { id: "signals", label: "Signals" },
    { id: "pipeline", label: "Pipeline" },
  ];
  return (
    <div className="ai-root min-h-screen" style={{ backgroundColor: "#0a0a1a", color: "#cbd5e1", fontFamily: "'DM Sans', system-ui, sans-serif" }}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap'); .ai-root,.ai-root button{font-family:'DM Sans',system-ui,sans-serif}.ai-root .ai-mono,.ai-root .ai-mono *{font-family:'JetBrains Mono',ui-monospace,monospace}`}</style>
      <header className="border-b sticky top-0 z-20" style={{ borderColor: "#1c1f3f", backgroundColor: "rgba(10,10,26,0.96)", backdropFilter: "blur(8px)" }}>
        <div className="max-w-[1400px] mx-auto px-8 pt-6">
          <div className="flex items-center justify-between mb-6">
            <div><div style={{ fontSize: 18, color: "#f1f5f9", fontWeight: 600 }}>AI Intelligence Brief</div><div className="ai-mono mt-1" style={{ fontSize: 10, color: "#64748b", letterSpacing: "0.18em" }}>WEEKLY ENTERPRISE AI SIGNALS</div></div>
            <div className="flex items-center gap-6">
              <button type="button" disabled className="ai-mono px-3 py-2 border" style={{ borderColor: "#1c1f3f", color: "#64748b", fontSize: 10, letterSpacing: "0.12em" }}>ENTERPRISE FOCUS · COMING SOON</button>
              <div className="text-right"><div className="ai-mono" style={{ fontSize: 11, color: "#94a3b8", letterSpacing: "0.16em" }}>{weekLabel}</div><div className="ai-mono mt-1" style={{ fontSize: 9, color: "#475569" }}>REFRESHED {refreshedAt}</div></div>
            </div>
          </div>
          <nav className="flex items-center gap-1" style={{ marginBottom: -1 }}>
            {tabs.map((item) => <button type="button" key={item.id} onClick={() => setTab(item.id)} className="ai-mono px-4 py-3" style={{ fontSize: 11, letterSpacing: "0.16em", color: tab === item.id ? "#fef3c7" : "#64748b", borderBottom: tab === item.id ? `2px solid ${ACCENT_GOLD}` : "2px solid transparent" }}>{item.label.toUpperCase()}</button>)}
            <div className="ai-mono ml-auto flex items-center gap-2 pb-3" style={{ fontSize: 10, color: "#475569", letterSpacing: "0.16em" }}><Activity size={11} style={{ color: "#34d399" }} />ARTIFACT · LIVE</div>
          </nav>
        </div>
      </header>
      <main className="max-w-[1400px] mx-auto px-8 py-10">
        {tab === "snapshot" && <WeeklySnapshot onNavigate={setTab} />}
        {tab === "research" && <ResearchTab weekLabel={weekLabel} />}
        {tab === "repos" && <ReposTab />}
        {tab === "releases" && <ReleasesTab />}
        {tab === "signals" && <SignalsTab />}
        {tab === "pipeline" && <PipelineTab />}
      </main>
      <footer className="border-t mt-20" style={{ borderColor: "#1c1f3f" }}><div className="ai-mono max-w-[1400px] mx-auto px-8 py-5 flex justify-between" style={{ fontSize: 9, color: "#475569", letterSpacing: "0.14em" }}><div>AI INTELLIGENCE BRIEF · LOCAL ARTIFACT</div><div>{weekLabel} · GENERATED {refreshedAt}</div></div></footer>
    </div>
  );
}
