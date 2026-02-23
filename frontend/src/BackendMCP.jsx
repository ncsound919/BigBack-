import { useState, useCallback, useMemo } from "react";

// ── Data ──────────────────────────────────────────────────────────────────────

const INFRA = [
  { id: "aws",    label: "AWS",        icon: "☁️",  regions: ["us-east-1","eu-central-1","ap-southeast-1"] },
  { id: "gcp",    label: "GCP",        icon: "🌐",  regions: ["us-central1","europe-west1","asia-east1"] },
  { id: "azure",  label: "Azure",      icon: "🔷",  regions: ["eastus","westeurope","southeastasia"] },
  { id: "on-prem",label: "Bare Metal", icon: "🏢",  regions: ["local","datacenter-a","datacenter-b"] },
];

const FRAMEWORKS = [
  { id: "fastapi",  label: "FastAPI",    lang: "Python", color: "#63b3ed", icon: "🚀", perf: "Ultra" },
  { id: "express",  label: "Express.js", lang: "Node",   color: "#68d391", icon: "⚡", perf: "High" },
  { id: "nestjs",   label: "NestJS",     lang: "Node",   color: "#fc8181", icon: "🏗️", perf: "Enterprise" },
  { id: "gin",      label: "Gin",        lang: "Go",     color: "#76e4f7", icon: "🍸", perf: "Extreme" },
  { id: "django",   label: "Django",     lang: "Python", color: "#fbd38d", icon: "🎸", perf: "Solid" },
];

const DATABASES = [
  { id: "postgres",  label: "PostgreSQL", color: "#63b3ed", icon: "🐘" },
  { id: "mongo",     label: "MongoDB",    color: "#68d391", icon: "🍃" },
  { id: "mysql",     label: "MySQL",      color: "#fbd38d", icon: "🐬" },
  { id: "sqlite",    label: "SQLite",     color: "#b794f4", icon: "📦" },
  { id: "planetscale",label:"PlanetScale",color: "#f687b3", icon: "🌍" },
];

const CACHES = [
  { id: "redis",     label: "Redis",     icon: "🔴" },
  { id: "memcached", label: "Memcached", icon: "🗃️" },
  { id: "dragonfly", label: "Dragonfly", icon: "🐉" },
  { id: "none",      label: "None",      icon: "∅" },
];

const DEFAULTS = {
  project: "my-service",
  env: "production",
  infra: "aws",
  region: "us-east-1",
  framework: "fastapi",
  database: "postgres",
  cache: "redis",
  port: 8000,
  rateLimit: 100,
  poolSize: 20,
  cacheTTL: 300,
  timeout: 30,
  replicas: 2,
  features: {
    auth: true,
    cors: true,
    logging: true,
    docker: true,
    swagger: true,
    rateLimiting: true,
    compression: true,
    prometheus: true,
    healthChecks: true,
    tracing: false,
    ci: false,
    tests: true,
  },
  auth: "jwt",
};

const PRESETS = [
  { id: "saas-starter",  label: "SaaS Starter",  icon: "🏢",
    config: { ...DEFAULTS, framework:"nestjs",  database:"postgres", replicas:3, poolSize:25, features:{...DEFAULTS.features, ci:true, tests:true} } },
  { id: "ml-api",        label: "ML API",         icon: "🤖",
    config: { ...DEFAULTS, framework:"fastapi", database:"postgres", cache:"redis", port:8000, timeout:120, poolSize:5, rateLimit:50, features:{...DEFAULTS.features, swagger:true, tracing:true} } },
  { id: "realtime",      label: "Realtime App",   icon: "⚡",
    config: { ...DEFAULTS, framework:"express", database:"mongo",    cache:"redis", replicas:4, rateLimit:500, cacheTTL:60 } },
  { id: "microservice",  label: "Microservice",   icon: "🔬",
    config: { ...DEFAULTS, framework:"gin",     database:"postgres", replicas:6, poolSize:50, rateLimit:1000, timeout:5 } },
  { id: "edge-minimal",  label: "Edge Minimal",   icon: "🌊",
    config: { ...DEFAULTS, framework:"express", database:"sqlite",   cache:"none", replicas:1, poolSize:2, features:{...DEFAULTS.features, prometheus:false, swagger:false, tracing:false, ci:false} } },
  { id: "graphql-api",   label: "GraphQL API",    icon: "◈",
    config: { ...DEFAULTS, framework:"nestjs",  database:"postgres", cache:"redis", replicas:3, poolSize:30, rateLimit:200, features:{...DEFAULTS.features, swagger:false, tracing:true, ci:true, tests:true} } },
  { id: "event-stream",  label: "Event Streaming",icon: "📡",
    config: { ...DEFAULTS, framework:"fastapi", database:"postgres", cache:"redis", replicas:4, poolSize:40, rateLimit:5000, cacheTTL:10, timeout:60, features:{...DEFAULTS.features, tracing:true, prometheus:true, compression:false} } },
  { id: "cqrs",          label: "CQRS Service",   icon: "⇄",
    config: { ...DEFAULTS, framework:"nestjs",  database:"postgres", cache:"redis", replicas:4, poolSize:30, rateLimit:800, timeout:20, features:{...DEFAULTS.features, tracing:true, ci:true, tests:true} } },
];

const CODE_SNIPPETS = {
  fastapi: `@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(
    payload: ItemCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = Item(id=str(uuid4()), name=payload.name,
                owner=current_user.sub)
    db.add(item); await db.commit()
    return item`,
  express: `router.post('/items', authMiddleware, async (req, res, next) => {
  try {
    const item = await Item.create(
      { ...req.body, userId: req.user.id }
    );
    res.status(201).json(item);
  } catch (err) { next(err); }
});`,
  nestjs: `@Post()
@HttpCode(201)
@UseGuards(JwtAuthGuard)
create(
  @Body() dto: CreateItemDto,
  @CurrentUser() user: User,
) {
  return this.itemsService.create(dto, user.id);
}`,
  gin: `r.POST("/items", authMiddleware(), func(c *gin.Context) {
  var input ItemInput
  if err := c.ShouldBindJSON(&input); err != nil {
    c.JSON(400, gin.H{"error": err.Error()}); return
  }
  item := Item{Name: input.Name,
               OwnerID: c.GetString("userID")}
  db.Create(&item)
  c.JSON(201, item)
})`,
  django: `class ItemViewSet(ModelViewSet):
  serializer_class = ItemSerializer
  permission_classes = [IsAuthenticated]

  def get_queryset(self):
    return Item.objects.filter(
      owner=self.request.user)

  def perform_create(self, serializer):
    serializer.save(owner=self.request.user)`,
};

// ── Micro-components ──────────────────────────────────────────────────────────

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #030712; }
  ::-webkit-scrollbar { width: 3px; height: 3px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(99,179,237,.35); border-radius: 2px; }
  input[type=range] { -webkit-appearance: none; appearance: none; background: transparent; cursor: pointer; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 14px; height: 14px; border-radius: 50%; background: #fff; box-shadow: 0 0 6px rgba(99,179,237,.6); margin-top: -4px; }
  input[type=range]::-webkit-slider-runnable-track { height: 6px; border-radius: 3px; background: transparent; }
  input[type=range]::-moz-range-thumb { width: 14px; height: 14px; border-radius: 50%; background: #fff; border: none; box-shadow: 0 0 6px rgba(99,179,237,.6); }
  input[type=text] { outline: none; }
  @keyframes fadeUp { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
  @keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:.4;} }
  .card { animation: fadeUp .35s ease both; }
  .chip:hover { border-color: rgba(99,179,237,.5) !important; background: rgba(99,179,237,.08) !important; }
  .row-btn:hover { background: rgba(255,255,255,.07) !important; }
  .copy-btn:hover { filter: brightness(1.15); }
`;

function Glass({ children, style = {}, className = "", onClick }) {
  return (
    <div className={`card ${className}`} onClick={onClick} style={{
      background: "rgba(255,255,255,0.04)",
      backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
      border: "1px solid rgba(255,255,255,0.09)",
      borderRadius: 14,
      ...style,
    }}>{children}</div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, fontWeight: 600,
      color: "rgba(255,255,255,0.28)", textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 12 }}>
      {children}
    </div>
  );
}

function Slider({ label, value, min, max, step = 1, unit = "", onChange, accent = "#63b3ed" }) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 7 }}>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.07em" }}>{label}</span>
        <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, fontWeight: 600, color: accent }}>{value}{unit}</span>
      </div>
      <div style={{ position: "relative", height: 6, borderRadius: 3, background: "rgba(255,255,255,0.08)" }}>
        <div style={{ position:"absolute", left:0, top:0, height:"100%", width:`${pct}%`, borderRadius:3,
          background: `linear-gradient(90deg, ${accent}99, ${accent})` }} />
        <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(+e.target.value)}
          style={{ position:"absolute", inset:0, width:"100%", height:"100%", opacity:0, cursor:"pointer" }} />
      </div>
    </div>
  );
}

function Toggle({ label, value, onChange }) {
  return (
    <div className="row-btn" onClick={() => onChange(!value)} style={{
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding: "9px 0", borderBottom: "1px solid rgba(255,255,255,0.05)", cursor:"pointer",
    }}>
      <span style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:12, textTransform:"uppercase", letterSpacing:"0.04em",
        color: value ? "rgba(255,255,255,.85)" : "rgba(255,255,255,.3)", transition:"color .2s" }}>{label}</span>
      <div style={{ width:36, height:20, borderRadius:10, position:"relative", transition:"background .25s",
        background: value ? "linear-gradient(90deg,#2563eb,#63b3ed)" : "rgba(255,255,255,.08)",
        border:"1px solid rgba(255,255,255,.12)", flexShrink:0 }}>
        <div style={{ position:"absolute", top:2, left: value ? 17 : 2, width:14, height:14,
          borderRadius:"50%", background:"white", transition:"left .25s", boxShadow:"0 1px 3px rgba(0,0,0,.4)" }} />
      </div>
    </div>
  );
}

function SelectRow({ item, active, color, onClick }) {
  return (
    <div className="row-btn" onClick={onClick} style={{
      display:"flex", alignItems:"center", gap:10, padding:"10px 12px", borderRadius:10, cursor:"pointer",
      transition:"all .18s",
      background: active ? `${color}14` : "rgba(255,255,255,.025)",
      border: active ? `1px solid ${color}45` : "1px solid transparent",
    }}>
      <span style={{ fontSize:16 }}>{item.icon}</span>
      <div style={{ flex:1, minWidth:0 }}>
        <div style={{ fontSize:13, fontWeight:500, color: active ? "#fff" : "rgba(255,255,255,.55)", fontFamily:"'Syne',sans-serif" }}>{item.label}</div>
        {item.lang && <div style={{ fontSize:10, fontFamily:"'JetBrains Mono',monospace", color:"rgba(255,255,255,.25)", marginTop:1 }}>{item.lang} · {item.perf}</div>}
      </div>
      {active && <div style={{ width:5, height:5, borderRadius:"50%", background:color, flexShrink:0, boxShadow:`0 0 6px ${color}` }} />}
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function BackendMCP() {
  const [config, setConfig] = useState(DEFAULTS);
  const [activePreset, setActivePreset] = useState(null);
  const [customPresets, setCustomPresets] = useState([]);
  const [copied, setCopied] = useState(false);
  const [showSave, setShowSave] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [jsonTab, setJsonTab] = useState("full"); // full | spec | meta
  const [snippetCopied, setSnippetCopied] = useState(false);

  const update = useCallback((k, v) => { setConfig(c => ({...c,[k]:v})); setActivePreset(null); }, []);
  const updateF = useCallback((k, v) => { setConfig(c => ({...c,features:{...c.features,[k]:v}})); setActivePreset(null); }, []);

  const fw  = FRAMEWORKS.find(f => f.id === config.framework);
  const db  = DATABASES.find(d => d.id === config.database);
  const inf = INFRA.find(i => i.id === config.infra);

  const outputJSON = useMemo(() => ({
    metadata: {
      project: config.project,
      version: "2.0.0",
      env: config.env,
      generated: new Date().toISOString().split("T")[0],
    },
    spec: {
      runtime: { id: fw?.id, label: fw?.label, lang: fw?.lang, perf: fw?.perf },
      infrastructure: { provider: inf?.id, label: inf?.label, region: config.region },
      deployment: {
        replicas: config.replicas,
        port: config.port,
        timeout: `${config.timeout}s`,
        resources: { db_pool_max: config.poolSize, db_pool_min: 2 },
      },
      stack: {
        database: config.database,
        cache: config.cache,
        auth_strategy: config.auth,
      },
      performance: {
        rate_limit: { requests: config.rateLimit, window: "1m" },
        cache_ttl: config.cacheTTL,
      },
      monitoring: {
        prometheus: config.features.prometheus,
        tracing: config.features.tracing,
        health_path: "/health",
        log_level: config.features.logging ? "info" : "error",
      },
      features: config.features,
    },
  }), [config, fw, inf]);

  const displayJSON = jsonTab === "meta" ? outputJSON.metadata
    : jsonTab === "spec" ? outputJSON.spec
    : outputJSON;

  const copyJSON = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(outputJSON, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard unavailable (e.g. non-secure context) – no-op
    }
  };

  const activeSnippet = CODE_SNIPPETS[config.framework] || "";

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(activeSnippet);
      setSnippetCopied(true);
      setTimeout(() => setSnippetCopied(false), 2000);
    } catch {
      // clipboard unavailable – no-op
    }
  };

  const savePreset = () => {
    if (!saveName.trim()) return;
    const emojis = ["🎯","🌊","🔥","💫","🛸","🎪","🧬"];
    setCustomPresets(p => [...p, {
      id: `custom-${Date.now()}`,
      label: saveName.trim(),
      icon: emojis[Math.floor(Math.random()*emojis.length)],
      config: {...config},
    }]);
    setSaveName(""); setShowSave(false);
  };

  const allPresets = [...PRESETS, ...customPresets];

  return (
    <div style={{ minHeight:"100vh", background:"linear-gradient(145deg,#020b18 0%,#030a1a 40%,#02080f 100%)", padding:22, position:"relative", overflow:"hidden" }}>
      <style>{css}</style>

      {/* Ambient glow */}
      {[
        { top:-80, right:-60, w:420, h:420, color:"rgba(37,99,235,.12)" },
        { bottom:-100, left:-80, w:500, h:500, color:"rgba(6,78,59,.1)" },
        { top:"35%", left:"45%", w:280, h:280, color:"rgba(99,179,237,.06)" },
      ].map((o,i) => (
        <div key={i} style={{ position:"fixed", top:o.top, bottom:o.bottom, left:o.left, right:o.right,
          width:o.w, height:o.h, borderRadius:"50%",
          background:`radial-gradient(circle,${o.color} 0%,transparent 70%)`, pointerEvents:"none", zIndex:0 }} />
      ))}

      <div style={{ position:"relative", zIndex:1 }}>

        {/* ── Header ── */}
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:22 }}>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <div style={{ width:36, height:36, borderRadius:10, background:"linear-gradient(135deg,#1d4ed8,#0891b2)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, boxShadow:"0 0 18px rgba(8,145,178,.35)" }}>⬡</div>
            <div>
              <div style={{ display:"flex", alignItems:"center", gap:8 }}>
                <h1 style={{ fontFamily:"'Syne',sans-serif", fontSize:20, fontWeight:800, color:"#fff", letterSpacing:"-0.02em" }}>BackendMCP</h1>
                <span style={{ background:"rgba(8,145,178,.2)", border:"1px solid rgba(8,145,178,.4)", borderRadius:5, padding:"2px 7px", fontSize:10, fontFamily:"'JetBrains Mono',monospace", fontWeight:600, color:"#67e8f9", letterSpacing:"0.05em" }}>v2.0</span>
              </div>
              {/* Editable project name */}
              <div style={{ display:"flex", alignItems:"center", gap:6, marginTop:2 }}>
                <span style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:11, color:"rgba(255,255,255,.25)" }}>project /</span>
                <input
                  value={config.project}
                  onChange={e => update("project", e.target.value)}
                  style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:11, color:"rgba(99,179,237,.8)", background:"transparent", border:"none", width:160, outline:"none" }}
                />
              </div>
            </div>
          </div>

          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            {/* Env badge */}
            {["development","staging","production"].map(e => (
              <button key={e} onClick={() => update("env",e)} style={{
                padding:"6px 12px", borderRadius:7, fontSize:11, fontFamily:"'JetBrains Mono',monospace",
                cursor:"pointer", fontWeight:600, letterSpacing:"0.04em", transition:"all .2s",
                background: config.env===e ? (e==="production"?"rgba(220,38,38,.25)":e==="staging"?"rgba(217,119,6,.2)":"rgba(22,163,74,.2)") : "rgba(255,255,255,.04)",
                border: config.env===e ? (e==="production"?"1px solid rgba(248,113,113,.4)":e==="staging"?"1px solid rgba(251,191,36,.35)":"1px solid rgba(74,222,128,.35)") : "1px solid rgba(255,255,255,.08)",
                color: config.env===e ? (e==="production"?"#fca5a5":e==="staging"?"#fcd34d":"#86efac") : "rgba(255,255,255,.35)",
              }}>{e}</button>
            ))}
            <button onClick={() => setShowSave(true)} style={{ padding:"8px 16px", borderRadius:8, border:"1px solid rgba(255,255,255,.14)", background:"rgba(255,255,255,.05)", color:"rgba(255,255,255,.6)", fontSize:12, cursor:"pointer", fontFamily:"'JetBrains Mono',monospace" }}>+ Template</button>
            <button className="copy-btn" onClick={copyJSON} style={{ padding:"8px 18px", borderRadius:8, border:"1px solid rgba(8,145,178,.5)", background: copied?"rgba(8,145,178,.25)":"linear-gradient(135deg,rgba(37,99,235,.5),rgba(8,145,178,.4))", color:"#fff", fontSize:12, cursor:"pointer", fontWeight:600, fontFamily:"'JetBrains Mono',monospace", transition:"all .2s" }}>
              {copied ? "✓ Copied" : "⬇ Export"}
            </button>
          </div>
        </div>

        {/* ── Main grid ── */}
        <div style={{ display:"grid", gridTemplateColumns:"220px 220px 1fr 1fr", gap:16, alignItems:"start" }}>

          {/* ── Col 1: Infra + Framework ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>

            <Glass style={{ padding:"15px 14px" }}>
              <SectionLabel>Cloud / Infra</SectionLabel>
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {INFRA.map(i => (
                  <SelectRow key={i.id} item={i} active={config.infra===i.id} color="#63b3ed" onClick={() => { update("infra",i.id); update("region",i.regions[0]); }} />
                ))}
              </div>
              {/* Region selector */}
              <div style={{ marginTop:12 }}>
                <SectionLabel>Region</SectionLabel>
                <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                  {(inf?.regions||[]).map(r => (
                    <button key={r} className="chip" onClick={() => update("region",r)} style={{
                      padding:"5px 9px", borderRadius:6, fontSize:11, fontFamily:"'JetBrains Mono',monospace", cursor:"pointer", transition:"all .18s",
                      background: config.region===r?"rgba(99,179,237,.12)":"rgba(255,255,255,.04)",
                      border: config.region===r?"1px solid rgba(99,179,237,.45)":"1px solid rgba(255,255,255,.08)",
                      color: config.region===r?"#67e8f9":"rgba(255,255,255,.4)",
                    }}>{r}</button>
                  ))}
                </div>
              </div>
            </Glass>

            <Glass style={{ padding:"15px 14px" }}>
              <SectionLabel>Framework</SectionLabel>
              <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
                {FRAMEWORKS.map(f => (
                  <SelectRow key={f.id} item={f} active={config.framework===f.id} color={f.color} onClick={() => update("framework",f.id)} />
                ))}
              </div>
            </Glass>

          </div>

          {/* ── Col 2: DB + Cache + Auth ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>

            <Glass style={{ padding:"15px 14px" }}>
              <SectionLabel>Database</SectionLabel>
              <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
                {DATABASES.map(d => (
                  <SelectRow key={d.id} item={d} active={config.database===d.id} color={d.color} onClick={() => update("database",d.id)} />
                ))}
              </div>
            </Glass>

            <Glass style={{ padding:"15px 14px" }}>
              <SectionLabel>Cache</SectionLabel>
              <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
                {CACHES.map(c => (
                  <SelectRow key={c.id} item={c} active={config.cache===c.id} color="#a78bfa" onClick={() => update("cache",c.id)} />
                ))}
              </div>
            </Glass>

            <Glass style={{ padding:"15px 14px" }}>
              <SectionLabel>Auth Strategy</SectionLabel>
              <div style={{ display:"flex", flexWrap:"wrap", gap:7 }}>
                {["jwt","session","oauth","apikey","none"].map(a => (
                  <button key={a} className="chip" onClick={() => update("auth",a)} style={{
                    padding:"7px 12px", borderRadius:8, fontSize:11, fontFamily:"'JetBrains Mono',monospace",
                    textTransform:"uppercase", letterSpacing:"0.05em", cursor:"pointer", transition:"all .18s", fontWeight:500,
                    background: config.auth===a?"linear-gradient(135deg,rgba(37,99,235,.5),rgba(8,145,178,.4))":"rgba(255,255,255,.05)",
                    border: config.auth===a?"1px solid rgba(8,145,178,.5)":"1px solid rgba(255,255,255,.09)",
                    color: config.auth===a?"#fff":"rgba(255,255,255,.45)",
                  }}>{a}</button>
                ))}
              </div>
            </Glass>

          </div>

          {/* ── Col 3: Sliders + Toggles ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>

            <Glass style={{ padding:"16px 18px" }}>
              <SectionLabel>Deployment & Scaling</SectionLabel>
              <Slider label="Replicas"      value={config.replicas}  min={1}   max={20}    accent="#67e8f9"  onChange={v => update("replicas",v)} />
              <Slider label="Port"          value={config.port}      min={1000} max={9999}  accent="#63b3ed"  onChange={v => update("port",v)} />
              <Slider label="Timeout"       value={config.timeout}   min={1}   max={300}   unit="s" accent="#86efac" onChange={v => update("timeout",v)} />
            </Glass>

            <Glass style={{ padding:"16px 18px" }}>
              <SectionLabel>Performance Tuning</SectionLabel>
              <Slider label="Rate Limit"    value={config.rateLimit} min={10}  max={10000} step={10} unit=" req/m" accent="#fcd34d" onChange={v => update("rateLimit",v)} />
              <Slider label="DB Pool Size"  value={config.poolSize}  min={1}   max={100}   unit=" conn"            accent="#c084fc" onChange={v => update("poolSize",v)} />
              <Slider label="Cache TTL"     value={config.cacheTTL}  min={0}   max={3600}  step={30} unit="s"      accent="#f9a8d4" onChange={v => update("cacheTTL",v)} />
            </Glass>

            <Glass style={{ padding:"16px 18px" }}>
              <SectionLabel>Feature Flags</SectionLabel>
              {Object.entries(config.features).map(([k,v]) => (
                <Toggle key={k} label={k.replace(/([A-Z])/g,' $1').trim()} value={v} onChange={val => updateF(k,val)} />
              ))}
            </Glass>

          </div>

          {/* ── Col 4: Templates + JSON Preview ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:14 }}>

            {/* Templates */}
            <Glass style={{ padding:"15px 14px" }}>
              <SectionLabel>Templates</SectionLabel>
              <div style={{ display:"flex", flexDirection:"column", gap:7 }}>
                {allPresets.map(p => (
                  <div key={p.id} className="row-btn" onClick={() => { setConfig(p.config); setActivePreset(p.id); }} style={{
                    display:"flex", alignItems:"center", gap:10, padding:"10px 12px", borderRadius:10, cursor:"pointer", transition:"all .18s",
                    background: activePreset===p.id?"rgba(37,99,235,.18)":"rgba(255,255,255,.03)",
                    border: activePreset===p.id?"1px solid rgba(37,99,235,.45)":"1px solid rgba(255,255,255,.07)",
                  }}>
                    <span style={{ fontSize:16 }}>{p.icon}</span>
                    <span style={{ fontFamily:"'Syne',sans-serif", fontSize:13, fontWeight:500, color: activePreset===p.id?"#fff":"rgba(255,255,255,.6)", flex:1 }}>{p.label}</span>
                    {p.id.startsWith("custom-") && <span style={{ fontSize:9, fontFamily:"'JetBrains Mono',monospace", color:"rgba(167,139,250,.55)", border:"1px solid rgba(167,139,250,.2)", borderRadius:4, padding:"2px 5px" }}>custom</span>}
                  </div>
                ))}
              </div>
            </Glass>

            {/* Stack summary chips */}
            <Glass style={{ padding:"13px 14px", background:"rgba(8,145,178,.07)", border:"1px solid rgba(8,145,178,.15)" }}>
              <SectionLabel>Active Stack</SectionLabel>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {[
                  { label: fw?.label,            color: fw?.color },
                  { label: db?.label,            color: db?.color },
                  { label: inf?.label,           color: "#63b3ed" },
                  { label: `×${config.replicas} replicas`, color: "#67e8f9" },
                  { label: `:${config.port}`,    color: "#a78bfa" },
                  ...(config.features.docker     ? [{label:"Docker",   color:"#76e4f7"}] : []),
                  ...(config.features.prometheus ? [{label:"Prometheus",color:"#fcd34d"}] : []),
                  ...(config.features.tracing    ? [{label:"Tracing",  color:"#f9a8d4"}] : []),
                ].map((t,i) => (
                  <span key={i} style={{ padding:"4px 9px", borderRadius:6, fontSize:11, fontFamily:"'JetBrains Mono',monospace", background:`${t.color}15`, border:`1px solid ${t.color}35`, color:t.color }}>{t.label}</span>
                ))}
              </div>
              <div style={{ marginTop:10, fontFamily:"'JetBrains Mono',monospace", fontSize:11, color:"rgba(255,255,255,.25)" }}>
                {Object.values(config.features).filter(Boolean).length} / {Object.values(config.features).length} features active
              </div>
            </Glass>

            {/* JSON Preview */}
            <Glass style={{ padding:"14px 14px" }}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
                <SectionLabel>Output Schema</SectionLabel>
                <div style={{ display:"flex", gap:6 }}>
                  {["full","spec","meta"].map(t => (
                    <button key={t} onClick={() => setJsonTab(t)} style={{
                      padding:"3px 9px", borderRadius:5, fontSize:10, fontFamily:"'JetBrains Mono',monospace",
                      cursor:"pointer", fontWeight:600, letterSpacing:"0.04em",
                      background: jsonTab===t?"rgba(99,179,237,.2)":"transparent",
                      border: jsonTab===t?"1px solid rgba(99,179,237,.4)":"1px solid rgba(255,255,255,.07)",
                      color: jsonTab===t?"#67e8f9":"rgba(255,255,255,.3)",
                    }}>{t}</button>
                  ))}
                  <div style={{ width:7, height:7, borderRadius:"50%", background:"#68d391", boxShadow:"0 0 7px #68d391", alignSelf:"center", marginLeft:4, animation:"pulse 2s infinite" }} />
                </div>
              </div>
              <pre style={{
                fontSize:10.5, fontFamily:"'JetBrains Mono',monospace", color:"rgba(99,179,237,.8)",
                maxHeight:320, overflowY:"auto", lineHeight:1.7,
                background:"rgba(0,0,0,.35)", borderRadius:8, padding:12,
                border:"1px solid rgba(255,255,255,.05)",
              }}>{JSON.stringify(displayJSON, null, 2)}</pre>
            </Glass>

            {/* Code Snippet */}
            <Glass style={{ padding:"14px 14px" }}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
                <SectionLabel>Quick Snippet · {fw?.label}</SectionLabel>
                <button className="copy-btn" onClick={copySnippet} style={{
                  padding:"3px 10px", borderRadius:5, fontSize:10, fontFamily:"'JetBrains Mono',monospace",
                  cursor:"pointer", fontWeight:600, letterSpacing:"0.04em", transition:"all .2s",
                  background: snippetCopied?"rgba(104,211,145,.2)":"rgba(255,255,255,.05)",
                  border: snippetCopied?"1px solid rgba(104,211,145,.4)":"1px solid rgba(255,255,255,.1)",
                  color: snippetCopied?"#68d391":"rgba(255,255,255,.4)",
                }}>{snippetCopied ? "✓ Copied" : "Copy"}</button>
              </div>
              <pre style={{
                fontSize:10, fontFamily:"'JetBrains Mono',monospace", color:"rgba(167,139,250,.85)",
                maxHeight:200, overflowY:"auto", lineHeight:1.65,
                background:"rgba(0,0,0,.35)", borderRadius:8, padding:12,
                border:"1px solid rgba(255,255,255,.05)", whiteSpace:"pre-wrap",
              }}>{activeSnippet || "# No snippet available for this framework"}</pre>
            </Glass>

          </div>
        </div>
      </div>

      {/* ── Save Modal ── */}
      {showSave && (
        <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,.7)", backdropFilter:"blur(8px)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:200 }}>
          <Glass style={{ padding:28, width:380, background:"rgba(3,14,30,.9)", border:"1px solid rgba(99,179,237,.2)" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:17, fontWeight:700, color:"#fff", marginBottom:6 }}>Save as Template</div>
            <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:12, color:"rgba(255,255,255,.35)", marginBottom:20 }}>Snapshot current config · reusable across projects</div>
            <input
              autoFocus value={saveName} onChange={e => setSaveName(e.target.value)}
              onKeyDown={e => e.key==="Enter" && savePreset()}
              placeholder="Template name..."
              style={{ width:"100%", padding:"12px 14px", borderRadius:10, background:"rgba(255,255,255,.06)", border:"1px solid rgba(255,255,255,.14)", color:"#fff", fontSize:14, fontFamily:"'Syne',sans-serif", outline:"none", marginBottom:14 }}
            />
            <div style={{ display:"flex", gap:10 }}>
              <button onClick={() => setShowSave(false)} style={{ flex:1, padding:11, borderRadius:10, background:"rgba(255,255,255,.06)", border:"1px solid rgba(255,255,255,.1)", color:"rgba(255,255,255,.5)", cursor:"pointer", fontSize:13 }}>Cancel</button>
              <button onClick={savePreset} style={{ flex:2, padding:11, borderRadius:10, background:"linear-gradient(135deg,#1d4ed8,#0891b2)", border:"none", color:"#fff", cursor:"pointer", fontSize:13, fontWeight:600, fontFamily:"'Syne',sans-serif" }}>Save Template</button>
            </div>
          </Glass>
        </div>
      )}
    </div>
  );
}
