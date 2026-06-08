import { createContext, useContext, useEffect, useRef, useState } from "react";
import Activity from "lucide-react/dist/esm/icons/activity.js";
import ArrowRight from "lucide-react/dist/esm/icons/arrow-right.js";
import BookOpen from "lucide-react/dist/esm/icons/book-open.js";
import Boxes from "lucide-react/dist/esm/icons/boxes.js";
import CheckCircle from "lucide-react/dist/esm/icons/check-circle.js";
import ChevronRight from "lucide-react/dist/esm/icons/chevron-right.js";
import Code2 from "lucide-react/dist/esm/icons/code-2.js";
import Database from "lucide-react/dist/esm/icons/database.js";
import ExternalLink from "lucide-react/dist/esm/icons/external-link.js";
import FileJson from "lucide-react/dist/esm/icons/file-json.js";
import Layers from "lucide-react/dist/esm/icons/layers.js";
import Radio from "lucide-react/dist/esm/icons/radio.js";
import Search from "lucide-react/dist/esm/icons/search.js";
import Server from "lucide-react/dist/esm/icons/server.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";
import Star from "lucide-react/dist/esm/icons/star.js";
import Wrench from "lucide-react/dist/esm/icons/wrench.js";
import archiveIndex from "../../../data/archive/index.json";
import currentData from "../../../data/output.json";

const BriefDataContext = createContext(currentData);

const THEME = {
  bg: "#f7f8fb",
  shell: "#ffffff",
  surface: "#ffffff",
  surfaceSoft: "#f3f6fa",
  surfaceWarm: "#fffaf0",
  border: "#d8dee8",
  borderSoft: "#e7ebf2",
  text: "#182235",
  heading: "#0f172a",
  muted: "#667085",
  faint: "#98a2b3",
  accent: "#b45309",
  accentSoft: "#fef3c7",
  blue: "#2563eb",
  teal: "#0f766e",
  green: "#15803d",
  red: "#b42318",
  purple: "#7c3aed",
};
const ACCENT_GOLD = THEME.accent;

const TYPE = {
  appTitle: { fontSize: 20, lineHeight: 1.2, fontWeight: 650, color: THEME.heading, letterSpacing: "-0.01em" },
  sectionTitle: { fontSize: 16, lineHeight: 1.25, fontWeight: 650, color: THEME.heading, letterSpacing: "-0.01em" },
  cardTitle: { fontSize: 17, lineHeight: 1.35, fontWeight: 560, color: THEME.heading, letterSpacing: "-0.005em" },
  compactTitle: { fontSize: 13, lineHeight: 1.45, fontWeight: 560, color: THEME.text },
  body: { fontSize: 13, lineHeight: 1.65, color: THEME.muted },
  reading: { fontSize: 15, lineHeight: 1.85, color: "#24324a" },
  meta: { fontSize: 11, lineHeight: 1.45, color: THEME.muted, letterSpacing: "0.02em" },
  label: { fontSize: 10, lineHeight: 1.2, color: THEME.faint, letterSpacing: "0.08em", textTransform: "uppercase" },
  nav: { fontSize: 12, lineHeight: 1, letterSpacing: "0.04em", fontWeight: 500 },
};

const DEFAULT_MODEL_BENCHMARK_URL = "https://artificialanalysis.ai/evaluations";
const ARTIFICIAL_ANALYSIS_MODELS_URL = "https://artificialanalysis.ai/models";
const KNOWN_MODEL_BENCHMARK_URLS = {
  "claude opus 4 8": "https://artificialanalysis.ai/models/claude-opus-4-8",
  "gemini 3 5 flash": "https://artificialanalysis.ai/models/gemini-3-5-flash",
  "step 3 7 flash": "https://artificialanalysis.ai/models/step-3-7-flash",
};

const SIGNAL_COLORS = {
  High: { dot: THEME.green, text: "#166534", bg: "#ecfdf3" },
  Medium: { dot: THEME.accent, text: "#92400e", bg: "#fffbeb" },
  Low: { dot: THEME.muted, text: THEME.muted, bg: "#f8fafc" },
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

function getPublicationMonday(value) {
  const input = new Date(value);
  if (Number.isNaN(input.getTime())) return "";
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(input);
  const values = Object.fromEntries(parts.map(({ type, value: partValue }) => [type, partValue]));
  const localDate = new Date(`${values.year}-${values.month}-${values.day}T12:00:00Z`);
  const day = localDate.getUTCDay() || 7;
  localDate.setUTCDate(localDate.getUTCDate() - day + 1);
  return localDate.toISOString().slice(0, 10);
}

function formatEditionDate(value) {
  return new Date(`${value}T12:00:00Z`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

function useBriefData() {
  return useContext(BriefDataContext);
}

function Tag({ children, color = THEME.muted, backgroundColor = "transparent" }) {
  return (
    <span
      className="ai-mono inline-flex items-center px-2 py-0.5 border"
      style={{
        ...TYPE.label,
        fontSize: 9,
        color,
        backgroundColor,
        borderColor: "#d8dee8",
      }}
    >
      {children}
    </span>
  );
}

function SectionHeader({ title, sub, action }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3">
      <div>
        <h2
          style={TYPE.sectionTitle}
        >
          {title}
        </h2>
        {sub && (
          <div className="ai-mono mt-1" style={TYPE.label}>
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
      style={{ ...TYPE.nav, fontSize: 11, color: ACCENT_GOLD }}
    >
      {children}
      <ArrowRight size={12} />
    </button>
  );
}

function CtaLink({ href, children, color = ACCENT_GOLD }) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="ai-mono inline-flex items-center gap-1.5 px-2.5 py-1.5 border"
      style={{ fontSize: 10.5, lineHeight: 1.1, color: "#ffffff", backgroundColor: color, borderColor: color, fontWeight: 700 }}
    >
      {children}
      <ExternalLink size={11} />
    </a>
  );
}

function artificialAnalysisModelUrl(item) {
  const normalized = (item?.name ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  return KNOWN_MODEL_BENCHMARK_URLS[normalized] ?? ARTIFICIAL_ANALYSIS_MODELS_URL;
}

function CircularScore({ score }) {
  const radius = 20;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="relative" style={{ width: 52, height: 52 }}>
      <svg width="52" height="52" viewBox="0 0 52 52" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="26" cy="26" r={radius} fill="none" stroke="#d8dee8" strokeWidth="3" />
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
        style={{ fontSize: 12, color: ACCENT_GOLD, fontWeight: 600 }}
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
          <span style={TYPE.body}>{takeaway}</span>
        </li>
      ))}
    </ul>
  );
}

function ActionList({ actions }) {
  return (
    <ol className="space-y-2">
      {(actions ?? []).map((action, index) => (
        <li
          key={action}
          className="flex items-start gap-3 border px-3 py-3"
          style={{ backgroundColor: "#ffffff", borderColor: THEME.borderSoft }}
        >
          <span
            className="ai-mono shrink-0 inline-flex items-center justify-center"
            style={{
              width: 22,
              height: 22,
              fontSize: 10,
              color: ACCENT_GOLD,
              backgroundColor: THEME.accentSoft,
              border: `1px solid #fde68a`,
            }}
          >
            {index + 1}
          </span>
          <span style={{ ...TYPE.body, fontSize: 13.5, color: THEME.text }}>{action}</span>
        </li>
      ))}
    </ol>
  );
}

function StatsBar() {
  const pipelineData = useBriefData();
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px border mb-8" style={{ borderColor: "#d8dee8", backgroundColor: "#d8dee8" }}>
      {(pipelineData.stats ?? []).map((stat) => (
        <div
          key={stat.label}
          className="px-5 sm:px-6 py-5"
          style={{ backgroundColor: "#ffffff" }}
        >
          <div className="ai-mono mb-2" style={TYPE.label}>
            {stat.label}
          </div>
          <div
            className="mb-0.5"
            style={{ fontSize: 32, lineHeight: 1, color: stat.accent ? ACCENT_GOLD : THEME.heading, fontWeight: 650, letterSpacing: "-0.04em" }}
          >
            {stat.value}
          </div>
          <div style={{ ...TYPE.body, fontSize: 12 }}>{stat.sub}</div>
        </div>
      ))}
    </div>
  );
}

function SnapshotList({ title, icon: Icon, items, getTitle, getMeta, getSummary, onNavigate }) {
  return (
    <div className="border p-4 h-full min-w-0" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}>
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="ai-mono flex items-center gap-2 min-w-0" style={{ ...TYPE.nav, color: THEME.text }}>
          <Icon size={14} style={{ color: "#2563eb" }} />
          <span className="truncate">{title}</span>
        </div>
        <TextButton onClick={onNavigate}>VIEW ALL</TextButton>
      </div>
      <div className="space-y-2.5">
        {items.slice(0, 3).map((item) => (
          <div key={getTitle(item)} className="border-t pt-2.5" style={{ borderColor: "#e7ebf2" }}>
            <div className="truncate" style={TYPE.compactTitle}>{getTitle(item)}</div>
            {getSummary && <div className="truncate mt-1" style={{ ...TYPE.body, fontSize: 12 }}>{getSummary(item)}</div>}
            <div className="ai-mono truncate mt-1" style={{ ...TYPE.meta, fontSize: 10 }}>{getMeta(item)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FeaturedResearch({ paper, onNavigate }) {
  if (!paper) return null;
  return (
    <div className="border p-4 sm:p-6 mb-4" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5 md:gap-6 items-center">
        <div className="md:col-span-3 min-w-0">
          <div className="ai-mono mb-3" style={{ ...TYPE.label, color: ACCENT_GOLD }}>
            FEATURED RESEARCH PICK
          </div>
          <h3 className="mb-2" style={{ ...TYPE.cardTitle, fontSize: 22 }}>{paper.title}</h3>
          <div className="ai-mono mb-3" style={TYPE.meta}>{paper.date} · {paper.org}</div>
          <TakeawayList takeaways={paper.takeaways} limit={2} />
          <div className="flex flex-wrap items-center gap-2 mt-4">
            {paper.priority && <Tag>{paper.priority}</Tag>}
            {(paper.tags ?? []).slice(0, 2).map((tag) => <Tag key={tag}>{tag.toUpperCase()}</Tag>)}
          </div>
        </div>
        <div className="h-full pt-5 md:pt-0 md:pl-6 border-t md:border-t-0 md:border-l flex flex-row md:flex-col items-center justify-between md:justify-center gap-4 text-center" style={{ borderColor: "#e7ebf2" }}>
          <CircularScore score={paper.researchScore} />
          <div className="ai-mono mt-2" style={{ ...TYPE.label, fontSize: 9 }}>RESEARCH SCORE</div>
          <div className="md:mt-5 flex flex-col gap-3 items-center">
            <TextButton onClick={onNavigate}>EXPLORE RESEARCH</TextButton>
            {paper.url && (
              <a href={paper.url} target="_blank" rel="noreferrer" className="ai-mono inline-flex items-center gap-1" style={{ fontSize: 10, color: "#2563eb" }}>
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
  const pipelineData = useBriefData();
  const repos = pipelineData.repos ?? [];
  const models = pipelineData.models ?? [];
  const toolsServices = pipelineData.toolsServices ?? [];
  const papers = pipelineData.papers ?? [];
  return (
    <div>
      <StatsBar />
      <SectionHeader title="THIS WEEK" sub="A DECISION-FIRST VIEW OF THE SIGNALS WORTH OPENING" />
      <FeaturedResearch paper={papers[0]} onNavigate={() => onNavigate("research")} />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SnapshotList title="TRENDING REPOS" icon={Boxes} items={repos} getTitle={(item) => item.name} getSummary={(item) => item.desc} getMeta={(item) => `${item.stars} stars · ${item.bestFor}`} onNavigate={() => onNavigate("repos")} />
        <SnapshotList title="MODEL RELEASES" icon={Sparkles} items={models} getTitle={(item) => item.name} getMeta={(item) => `${item.org} · ${item.date}`} onNavigate={() => onNavigate("releases")} />
        <SnapshotList title="TOOLS & SERVICES" icon={Wrench} items={toolsServices} getTitle={(item) => item.name} getMeta={(item) => `${item.org} · ${item.date}`} onNavigate={() => onNavigate("releases")} />
      </div>
    </div>
  );
}

function PaperCard({ paper }) {
  const [open, setOpen] = useState(false);
  const priorityColors = {
    READ: "#2563eb",
    EXPERIMENT: "#b45309",
    SHARE: "#7c3aed",
    WATCH: "#667085",
  };
  const priorityColor = priorityColors[paper.priority] ?? priorityColors.READ;
  return (
    <div className="border" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8", boxShadow: open ? "0 10px 30px rgba(15, 23, 42, 0.06)" : "none" }}>
      <button type="button" onClick={() => setOpen(!open)} className="w-full text-left px-4 sm:px-6 py-5">
        <div className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-5">
          <div className="flex-1 min-w-0">
            <h3 className="mb-2" style={TYPE.cardTitle}>{paper.title}</h3>
            <div className="ai-mono mb-3" style={TYPE.meta}>{paper.authors} · {paper.org} · {paper.date}</div>
            <TakeawayList takeaways={paper.takeaways} />
            <div className="flex items-center gap-2 flex-wrap mt-3">
              {paper.priority && <Tag color={priorityColor} backgroundColor={priorityColor === THEME.accent ? THEME.accentSoft : "#f8fafc"}>{paper.priority}</Tag>}
              {paper.hasCode && <Tag><Code2 size={10} className="mr-1" />CODE</Tag>}
              {(paper.tags ?? []).map((tag) => <Tag key={tag}>{tag.toUpperCase()}</Tag>)}
            </div>
          </div>
          <div className="flex flex-row sm:flex-col items-center sm:items-end gap-2 shrink-0">
            <CircularScore score={paper.researchScore} />
            <ChevronRight size={16} style={{ color: "#98a2b3", transform: open ? "rotate(90deg)" : "none" }} />
          </div>
        </div>
      </button>
      {open && (
        <div className="px-4 sm:px-6 pb-6 pt-5 border-t" style={{ borderColor: "#e7ebf2", backgroundColor: THEME.surfaceSoft }}>
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-5">
            <div className="min-w-0">
              <div className="ai-mono mb-2" style={TYPE.label}>ABSTRACT</div>
              <div style={{ backgroundColor: "#ffffff", borderLeft: `3px solid ${ACCENT_GOLD}`, padding: "14px 16px" }}>
                <p style={TYPE.reading}>{paper.abstract}</p>
              </div>
              <div className="ai-mono mt-5 mb-3" style={TYPE.label}>RESEARCH SIGNALS</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(paper.researchSignals ?? {}).map(([label, level]) => {
                  const style = SIGNAL_COLORS[level] ?? SIGNAL_COLORS.Low;
                  return (
                    <div key={label} className="flex items-center justify-between gap-3 border px-3 py-2" style={{ borderColor: "#e7ebf2", backgroundColor: style.bg }}>
                      <div className="ai-mono truncate" style={{ ...TYPE.label, fontSize: 9 }}>{label}</div>
                      <div className="flex items-center gap-2 shrink-0"><span className="rounded-full" style={{ width: 8, height: 8, backgroundColor: style.dot }} /><span style={{ fontSize: 12, color: style.text, fontWeight: 600 }}>{level}</span></div>
                    </div>
                  );
                })}
              </div>
            </div>
            <aside className="min-w-0">
              {(paper.actionItems ?? []).length > 0 && (
                <div className="border p-4" style={{ backgroundColor: "#fffaf0", borderColor: "#fde68a" }}>
                  <div className="ai-mono mb-3" style={{ ...TYPE.label, color: "#92400e" }}>RECOMMENDED ACTIONS</div>
                  <ActionList actions={paper.actionItems} />
                </div>
              )}
              <div className="mt-4">
                <CtaLink href={paper.url}>OPEN PAPER</CtaLink>
              </div>
            </aside>
          </div>
        </div>
      )}
    </div>
  );
}

function ResearchTab({ weekLabel }) {
  const papers = useBriefData().papers ?? [];
  return (
    <div>
      <SectionHeader title="RESEARCH" sub={`7-DAY WINDOW · 14-DAY BACKFILL ONLY IF NEEDED · ${weekLabel}`} />
      <div className="space-y-3">{papers.map((paper) => <PaperCard key={paper.title} paper={paper} />)}</div>
    </div>
  );
}

function repoActionItems(repo) {
  const generated = (repo.actionItems ?? []).filter(Boolean);
  if (generated.length >= 3) return generated.slice(0, 3);
  const focus = repo.bestFor || "AI Engineering";
  const release = repo.latestRelease || "recent commits";
  const license = repo.license || "license terms";
  return [
    `Clone ${repo.name} and run the README quickstart against a small local sample.`,
    `Map one ${focus} workflow to the repo APIs, inputs, and required integrations.`,
    `Review ${release}, open issues, and ${license} before a deeper benchmark or pilot.`,
  ];
}

function RepoList({ items }) {
  const [openRepo, setOpenRepo] = useState(items[0]?.name ?? "");
  return (
    <div className="border" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}>
      {items.map((repo, index) => (
        <div key={repo.name} className="px-4 py-3" style={{ borderBottom: index < items.length - 1 ? "1px solid #d8dee8" : "none" }}>
          <button type="button" onClick={() => setOpenRepo(openRepo === repo.name ? "" : repo.name)} className="w-full text-left">
            <div className="flex justify-between gap-3"><div className="ai-mono truncate min-w-0" style={{ ...TYPE.compactTitle, fontFamily: "var(--ai-font-mono)" }}>{repo.name}</div><div className="ai-mono shrink-0" style={{ ...TYPE.meta, fontSize: 10 }}><Star size={10} className="inline mr-1" />{repo.stars}</div></div>
            <div className="mt-1 break-words" style={{ ...TYPE.body, fontSize: 12, lineHeight: 1.55 }}>{repo.desc}</div>
          </button>
          {openRepo === repo.name && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "#e7ebf2" }}>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col xl:flex-row xl:items-start xl:justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    {repo.bestFor && <Tag>{repo.bestFor.toUpperCase()}</Tag>}
                    {repo.language && <Tag>{repo.language.toUpperCase()}</Tag>}
                    {repo.lastUpdated && <Tag>UPDATED {repo.lastUpdated.toUpperCase()}</Tag>}
                    {repo.license && <Tag>{repo.license.toUpperCase()}</Tag>}
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <CtaLink href={repo.latestReleaseUrl} color={THEME.blue}>RELEASE</CtaLink>
                    <CtaLink href={repo.url}>OPEN REPO</CtaLink>
                  </div>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)] gap-4">
                  <div className="min-w-0">
                    <TakeawayList takeaways={repo.bullets ?? [repo.desc]} limit={3} />
                  </div>
                  <aside className="min-w-0">
                    <div className="border p-4" style={{ backgroundColor: "#fffaf0", borderColor: "#fde68a" }}>
                      <div className="ai-mono mb-3" style={{ ...TYPE.label, color: "#92400e" }}>RECOMMENDED ACTIONS</div>
                      <ActionList actions={repoActionItems(repo)} />
                    </div>
                  </aside>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ReposTab() {
  const repos = useBriefData().repos ?? [];
  return <div><SectionHeader title="REPOS" sub="TRENDING OPEN-SOURCE PROJECTS · EXPAND FOR WHY THEY MATTER" /><RepoList items={repos} /></div>;
}

function releaseLinksForItem(item, kind) {
  const links = item.links ?? [];
  const readRelease = links.find((link) => link.label?.toLowerCase() === "read release") ?? (item.url ? { label: "Read release", url: item.url } : null);
  const visibleLinks = [];
  if (readRelease?.url) visibleLinks.push({ ...readRelease, color: ACCENT_GOLD });
  if (kind === "model") {
    const benchmark = links.find((link) => link.label?.toLowerCase() === "benchmark") ?? {
      label: "Benchmark",
      url: item.benchmarkUrl || DEFAULT_MODEL_BENCHMARK_URL,
    };
    const benchmarkUrl = benchmark.url === DEFAULT_MODEL_BENCHMARK_URL ? artificialAnalysisModelUrl(item) : benchmark.url;
    const benchmarkLabel = benchmarkUrl === ARTIFICIAL_ANALYSIS_MODELS_URL ? "Benchmarks" : benchmark.label;
    if (benchmarkUrl) visibleLinks.push({ ...benchmark, label: benchmarkLabel, url: benchmarkUrl, color: THEME.blue });
  }
  return visibleLinks;
}

function ReleaseList({ items, kind, emptyLabel }) {
  const [openItem, setOpenItem] = useState(items[0]?.name ?? "");
  if (!items.length) return <div className="border p-4" style={{ borderColor: "#d8dee8", color: "#667085" }}>{emptyLabel}</div>;
  return (
    <div className="border" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}>
      {items.map((item, index) => (
        <div key={`${item.name}-${item.url}`} className="px-4 py-3" style={{ borderBottom: index < items.length - 1 ? "1px solid #d8dee8" : "none" }}>
          <button type="button" onClick={() => setOpenItem(openItem === item.name ? "" : item.name)} className="w-full text-left">
            <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-3"><div className="truncate min-w-0" style={TYPE.compactTitle}>{item.name}</div><div className="ai-mono shrink-0" style={{ ...TYPE.meta, fontSize: 10 }}>{item.date}</div></div>
            <div className="truncate mt-1" style={{ ...TYPE.body, fontSize: 12 }}>{item.note}</div>
          </button>
          {openItem === item.name && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "#e7ebf2" }}>
              <div className="flex gap-2 mb-3"><Tag>{item.org.toUpperCase()}</Tag><Tag>{item.tag}</Tag></div>
              <div style={TYPE.body}>{item.note}</div>
              <div className="flex flex-wrap gap-3 mt-3">
                {releaseLinksForItem(item, kind).map((link) => (
                  <CtaLink key={`${item.name}-${link.label}-${link.url}`} href={link.url} color={link.color}>
                    {link.label.toUpperCase()}
                  </CtaLink>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ReleasesTab() {
  const pipelineData = useBriefData();
  const models = pipelineData.models ?? [];
  const toolsServices = pipelineData.toolsServices ?? [];
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div><SectionHeader title="MODEL RELEASES" sub="RECENT TRUSTED ANNOUNCEMENTS" /><ReleaseList items={models} kind="model" emptyLabel="No recent model releases found." /></div>
      <div><SectionHeader title="TOOLS & SERVICES" sub="RECENT TRUSTED ANNOUNCEMENTS" /><ReleaseList items={toolsServices} kind="tool" emptyLabel="No recent tool or service releases found." /></div>
    </div>
  );
}

function ComingSoonPanel({ title, icon: Icon, copy }) {
  return (
    <div className="border p-6" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}>
      <Icon size={20} style={{ color: "#2563eb" }} />
      <div className="mt-5 mb-2" style={TYPE.compactTitle}>{title}</div>
      <div style={TYPE.body}>{copy}</div>
      <div className="ai-mono mt-6" style={{ ...TYPE.label, color: ACCENT_GOLD }}>COMING SOON</div>
    </div>
  );
}

function SignalsTab() {
  return (
    <div>
      <SectionHeader title="SIGNALS" sub="PLACEHOLDERS FOR FUTURE CURATED SIGNAL STREAMS" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
  const health = useBriefData().health ?? [];
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
        <div className="border p-5" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {fetchers.map(({ name, sub, icon: Icon }) => <div key={name} className="border p-4" style={{ borderColor: "#d8dee8" }}><Icon size={16} style={{ color: "#2563eb" }} /><div className="mt-3" style={TYPE.compactTitle}>{name}</div><div className="ai-mono mt-1" style={{ ...TYPE.label, fontSize: 9 }}>{sub.toUpperCase()}</div></div>)}
          </div>
          <div className="ai-mono text-center my-4" style={TYPE.label}>PARALLEL FETCH · SPECIALIZED WORKFLOWS · SHARED ARTIFACT CONTRACT</div>
          <div className="flex flex-col md:flex-row items-stretch md:items-center gap-2">
            {shared.map(({ name, icon: Icon }, index) => <div key={name} className="flex flex-col md:flex-row md:contents items-center gap-2"><div className="w-full md:flex-1 border px-3 py-3 text-center" style={{ borderColor: "#d8dee8" }}><Icon size={14} className="mx-auto" style={{ color: index === shared.length - 1 ? "#15803d" : ACCENT_GOLD }} /><div className="ai-mono mt-2" style={{ ...TYPE.label, fontSize: 9 }}>{name.toUpperCase()}</div></div>{index < shared.length - 1 && <ArrowRight size={13} className="rotate-90 md:rotate-0" style={{ color: "#cbd5e1" }} />}</div>)}
          </div>
        </div>
      </div>
      <div>
        <SectionHeader title="LATEST SOURCE HEALTH" sub="LIVE DATA FROM DATA/HEALTH.JSON" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {health.map((entry) => <div key={entry.source} className="border p-4" style={{ backgroundColor: "#ffffff", borderColor: "#d8dee8" }}><div className="flex items-center justify-between"><div className="ai-mono" style={{ ...TYPE.nav, color: THEME.text }}>{entry.source.toUpperCase()}</div><CheckCircle size={13} style={{ color: entry.status === "ok" ? "#15803d" : "#b42318" }} /></div><div className="mt-4" style={{ fontSize: 26, lineHeight: 1, color: THEME.heading, fontWeight: 650, letterSpacing: "-0.03em" }}>{entry.item_count}</div><div className="ai-mono mt-1" style={{ ...TYPE.meta, fontSize: 10 }}>{healthDetail(entry)}</div><div className="ai-mono mt-3" style={{ ...TYPE.label, fontSize: 9 }}>{entry.duration_ms} MS</div></div>)}
        </div>
      </div>
      <div className="border p-4 flex items-start gap-3 min-w-0" style={{ borderColor: "#d8dee8", backgroundColor: "#ffffff" }}><FileJson size={16} className="shrink-0 mt-0.5" style={{ color: ACCENT_GOLD }} /><div className="min-w-0"><div style={TYPE.compactTitle}>Stable frontend contract</div><div className="ai-mono mt-1 break-words" style={{ ...TYPE.label, fontSize: 9 }}>DATA/OUTPUT.JSON · PAPERS · REPOS · MODELS · TOOLSERVICES · BLOGS · SOCIALPOSTS</div></div></div>
    </div>
  );
}

export default function Dashboard() {
  const [tab, setTab] = useState("snapshot");
  const [edition, setEdition] = useState("current");
  const [pipelineData, setPipelineData] = useState(currentData);
  const [editionLoading, setEditionLoading] = useState(false);
  const [editionNotice, setEditionNotice] = useState("");
  const archiveCache = useRef(new Map());
  const currentEditionDate = getPublicationMonday(currentData.generatedAt);
  const previousEditions = (archiveIndex.editions ?? [])
    .filter((entry) => entry.date !== currentEditionDate)
    .slice(0, 3);
  useEffect(() => {
    if (edition === "current") {
      setPipelineData(currentData);
      setEditionLoading(false);
      return undefined;
    }

    const selected = previousEditions.find((entry) => entry.date === edition);
    if (!selected) {
      setEdition("current");
      return undefined;
    }

    const cached = archiveCache.current.get(edition);
    if (cached) {
      setPipelineData(cached);
      setEditionLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    setEditionLoading(true);
    fetch(`${import.meta.env.BASE_URL}${selected.outputPath}`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`Archive request failed with ${response.status}`);
        return response.json();
      })
      .then((data) => {
        if (!data?.generatedAt) throw new Error("Archive payload is invalid");
        archiveCache.current.set(edition, data);
        setPipelineData(data);
        setEditionLoading(false);
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setPipelineData(currentData);
        setEditionLoading(false);
        setEditionNotice("ARCHIVE UNAVAILABLE · SHOWING CURRENT WEEK");
        setEdition("current");
      });

    return () => controller.abort();
  }, [edition]);
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
    <div className="ai-root min-h-screen" style={{ backgroundColor: "#f7f8fb", color: "#344054", fontFamily: "var(--ai-font-sans)" }}>
      <style>{`.ai-root,.ai-root button{font-family:var(--ai-font-sans);font-feature-settings:'rlig' 1,'calt' 1}.ai-root .ai-mono,.ai-root .ai-mono *{font-family:var(--ai-font-mono);font-feature-settings:'ss09' 1,'calt' 1}`}</style>
      <header className="border-b sticky top-0 z-20" style={{ borderColor: "#d8dee8", backgroundColor: "rgba(255,255,255,0.94)", backdropFilter: "blur(10px)" }}>
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 pt-5 sm:pt-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-5 sm:mb-6">
            <div><div style={TYPE.appTitle}>AI Intelligence Brief</div><div className="ai-mono mt-1" style={TYPE.label}>WEEKLY ENTERPRISE AI SIGNALS</div></div>
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-6">
              <label className="edition-select">
                <span className="ai-mono" style={{ ...TYPE.label, fontSize: 9 }}>EDITION</span>
                <select
                  aria-label="Select weekly edition"
                  value={edition}
                  onChange={(event) => {
                    setEditionNotice("");
                    setEdition(event.target.value);
                  }}
                  disabled={previousEditions.length === 0 || editionLoading}
                >
                  <option value="current">Current week</option>
                  {previousEditions.map((entry) => (
                    <option key={entry.date} value={entry.date}>Week of {formatEditionDate(entry.date)}</option>
                  ))}
                </select>
                {(editionLoading || editionNotice) && (
                  <span className="ai-mono edition-status">
                    {editionLoading ? "LOADING EDITION" : editionNotice}
                  </span>
                )}
              </label>
              <div className="sm:text-right"><div className="ai-mono" style={{ ...TYPE.nav, color: THEME.muted }}>{weekLabel}</div><div className="ai-mono mt-1" style={{ ...TYPE.label, fontSize: 9 }}>REFRESHED {refreshedAt}</div></div>
            </div>
          </div>
          <nav className="flex flex-wrap items-center gap-1" style={{ marginBottom: -1 }}>
            {tabs.map((item) => <button type="button" key={item.id} onClick={() => setTab(item.id)} className="ai-mono px-3 sm:px-4 py-3" style={{ ...TYPE.nav, color: tab === item.id ? "#92400e" : "#667085", borderBottom: tab === item.id ? `2px solid ${ACCENT_GOLD}` : "2px solid transparent" }}>{item.label.toUpperCase()}</button>)}
            <div className="ai-mono ml-auto hidden md:flex items-center gap-2 pb-3 flex-shrink-0" style={{ ...TYPE.nav, fontSize: 10, color: THEME.faint }}><Activity size={11} style={{ color: "#15803d" }} />ARTIFACT · LIVE</div>
          </nav>
        </div>
      </header>
      <BriefDataContext.Provider value={pipelineData}>
        <main key={edition} className="max-w-[1400px] mx-auto px-4 sm:px-8 py-6 sm:py-10">
          {tab === "snapshot" && <WeeklySnapshot onNavigate={setTab} />}
          {tab === "research" && <ResearchTab weekLabel={weekLabel} />}
          {tab === "repos" && <ReposTab />}
          {tab === "releases" && <ReleasesTab />}
          {tab === "signals" && <SignalsTab />}
          {tab === "pipeline" && <PipelineTab />}
        </main>
      </BriefDataContext.Provider>
      <footer className="border-t mt-16 sm:mt-20" style={{ borderColor: "#d8dee8" }}><div className="ai-mono max-w-[1400px] mx-auto px-4 sm:px-8 py-5 flex flex-col sm:flex-row gap-2 sm:justify-between" style={{ ...TYPE.label, fontSize: 9 }}><div>AI INTELLIGENCE BRIEF · LOCAL ARTIFACT</div><div>{weekLabel} · GENERATED {refreshedAt}</div></div></footer>
    </div>
  );
}
