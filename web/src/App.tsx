import { Fragment, useEffect, useState } from "react";

import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Bell,
  BookOpen,
  CandlestickChart,
  ChevronDown,
  CircleHelp,
  Clock3,
  Database,
  LayoutDashboard,
  Search,
  Flame,
  ShieldAlert,
  Settings2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

type NavItem = {
  label: string;
  icon: typeof LayoutDashboard;
  active?: boolean;
};

const mainNav: NavItem[] = [
  { label: "대시보드", icon: LayoutDashboard, active: true },
  { label: "시장 스캐너", icon: Search },
  { label: "종목 분석", icon: CandlestickChart },
  { label: "분석 기록", icon: BookOpen },
];

const marketNav: NavItem[] = [
  { label: "시장 현황", icon: BarChart3 },
];

type MarketBulletin = {
  date: string;
  advancers: number;
  decliners: number;
  unchanged: number;
  ticker_count: number;
  trading_value: number;
  index?: { name: string; close: number; change: number; change_pct: number; trend: number[] } | null;
  sectors?: { name: string; change_pct: number; stock_count: number; market: string }[];
  investor_flows?: { values?: Record<string, number> } | null;
};

type MarketCode = "ALL" | "KOSPI" | "KOSDAQ";
type Candle = {
  date: string;
  "시가": number | null; "고가": number | null; "저가": number | null; "종가": number | null;
  "거래량"?: number | null;
  MA10?: number | null; MA20?: number | null; MA60?: number | null;
  BB_UPPER?: number | null; BB_MIDDLE?: number | null; BB_LOWER?: number | null;
  MACD?: number | null; MACD_SIGNAL?: number | null; MACD_HIST?: number | null;
  RSI10?: number | null; RSI14?: number | null;
};
type StockAnalysis = { ticker: string; name: string; trading_date: string; signal?:{ready?:boolean;matched?:boolean;checks?:Record<string,boolean>;reason?:string}; latest?:{trade_plan?:{ready?:boolean;entry_low?:number;entry_high?:number;stop_loss?:number;target_1?:number;target_2?:number;reward_risk_1?:number;reward_risk_2?:number;warning?:string}}; ohlcv?: Candle[]; weekly_ohlcv?: Candle[] };
type ScanMatch = { ticker:string; name:string; trading_date:string; signal?:{checks?:Record<string,boolean>;rsi10?:number;rsi14?:number;macd?:number;macd_signal?:number;close?:number;ma10?:number;volume_ratio?:number}; weekly?:{ready?:boolean;trend?:string;grade?:"A"|"B"|"C";grade_score?:number;grade_reason?:string}; latest?:{close?:number;change_pct?:number;volume_ratio?:number;ma240?:number|null;ma10?:number|null;support20?:number|null;resistance20?:number|null;atr14?:number|null;trade_plan?:{ready?:boolean;entry_low?:number;entry_high?:number;stop_loss?:number;target_1?:number;target_2?:number;warning?:string}}; };
type ScanResult = { market:string; date:string; scanned:number; matches:ScanMatch[]; grade_counts?:Record<"A"|"B"|"C",number>; error_count:number; };
type ScanJob = { job_id:string; market:string; status:"running"|"completed"|"failed"; progress:number; total:number; current_ticker?:string|null; result?:ScanResult; error?:string; };


function formatCount(value: number | undefined) {
  return typeof value === "number" ? value.toLocaleString("ko-KR") : "—";
}

function formatTradingValue(value: number | undefined) {
  return typeof value === "number"
    ? `${(value / 100000000).toLocaleString("ko-KR", { maximumFractionDigits: 0 })}억`
    : "—";
}

function buildMarketNarrative(kospi?: MarketBulletin, kosdaq?: MarketBulletin) {
  if (!kospi || !kosdaq) return "코스피·코스닥 지수와 업종·수급 데이터를 모두 받은 뒤 장세를 요약합니다.";

  const markets = [kospi, kosdaq];
  const indexMoves = markets.map((item) => item.index?.change_pct).filter((v): v is number => typeof v === "number");
  const allUp = indexMoves.length === 2 && indexMoves.every((v) => v > 0);
  const allDown = indexMoves.length === 2 && indexMoves.every((v) => v < 0);
  const indexPhrase = allUp ? "코스피와 코스닥이 동반 상승했고"
    : allDown ? "코스피와 코스닥이 동반 하락했고"
      : indexMoves.length === 2 ? "코스피와 코스닥이 엇갈린 흐름을 보였고"
        : "지수 방향을 온전히 확인하기 어렵고";

  const sectors = markets.flatMap((item) => item.sectors ?? []);
  const sector = [...sectors].sort((a, b) => allDown
    ? a.change_pct - b.change_pct
    : b.change_pct - a.change_pct)[0];
  const sectorPhrase = sector && ((allDown && sector.change_pct < 0) || (!allDown && sector.change_pct > 0))
    ? `${sector.name} 업종이 ${sector.change_pct > 0 ? "+" : ""}${sector.change_pct.toFixed(2)}%로 ${allDown ? "낙폭이 컸고" : "강세를 주도했으며"}`
    : "";

  const flows: Record<string, number> = {};
  for (const item of markets) {
    for (const [name, value] of Object.entries(item.investor_flows?.values ?? {})) {
      flows[name] = (flows[name] ?? 0) + value;
    }
  }
  const investorNames = ["개인", "외국인", "기관합계"];
  const flowParts = investorNames.filter((name) => typeof flows[name] === "number" && flows[name] !== 0)
    .map((name) => `${name} ${flows[name] > 0 ? "순매수" : "순매도"}`);
  const flowPhrase = flowParts.length ? `${flowParts.join("·")} 흐름이 나타났고` : "";

  const adv = kospi.advancers + kosdaq.advancers;
  const dec = kospi.decliners + kosdaq.decliners;
  const breadthPhrase = adv > dec ? `상승 종목이 ${(adv - dec).toLocaleString("ko-KR")}개 더 많아 종목 확산도 양호했습니다.`
    : dec > adv ? `하락 종목이 ${(dec - adv).toLocaleString("ko-KR")}개 더 많아 시장 내부 체력은 약했습니다.`
      : "상승·하락 종목 수가 비슷해 종목 확산은 중립적이었습니다.";
  const closePhrase = allUp ? "상승 마감했습니다." : allDown ? "하락 마감했습니다." : "혼조세로 마감했습니다.";
  return [indexPhrase, sectorPhrase, flowPhrase, breadthPhrase, closePhrase].filter(Boolean).join(" ");
}

function PriceChart({ bars }: { bars: Candle[] }) {
  const rows = bars.filter((b) => [b["시가"], b["고가"], b["저가"], b["종가"]].every((v) => typeof v === "number" && Number.isFinite(v)));
  if (!rows.length) return <div className="chart-empty-content"><b>선택한 주기의 차트 데이터가 없습니다.</b></div>;

  const width = 900, left = 58, right = 16, plotWidth = width - left - right;
  const step = plotWidth / rows.length;
  const candleWidth = Math.max(2, Math.min(10, step * 0.62));
  const numeric = (v: number | null | undefined) => typeof v === "number" && Number.isFinite(v) ? v : null;
  const priceValues = rows.flatMap((b) => [numeric(b["고가"]), numeric(b["저가"]), numeric(b.BB_UPPER), numeric(b.BB_LOWER), numeric(b.MA10), numeric(b.MA20), numeric(b.MA60)]).filter((v): v is number => v !== null);
  const minPrice = Math.min(...priceValues), maxPrice = Math.max(...priceValues);
  const pricePad = (maxPrice - minPrice || 1) * 0.08;
  const pMin = minPrice - pricePad, pMax = maxPrice + pricePad;
  const priceY = (v: number) => 12 + ((pMax - v) / (pMax - pMin || 1)) * 216;
  const xAt = (i: number) => left + step * i + step / 2;
  const linePath = (key: keyof Candle, yFn: (v: number) => number) => {
    let path = "", drawing = false;
    rows.forEach((bar, i) => {
      const value = numeric(bar[key] as number | null | undefined);
      if (value === null) { drawing = false; return; }
      path += `${drawing ? " L" : " M"} ${xAt(i).toFixed(2)} ${yFn(value).toFixed(2)}`;
      drawing = true;
    });
    return path;
  };
  const volumeMax = Math.max(1, ...rows.map((b) => numeric(b["거래량"]) ?? 0));
  const macdValues = rows.flatMap((b) => [numeric(b.MACD), numeric(b.MACD_SIGNAL), numeric(b.MACD_HIST)]).filter((v): v is number => v !== null);
  const macdAbs = Math.max(1, ...macdValues.map(Math.abs)) * 1.15;
  const macdY = (v: number) => 42 + ((macdAbs - v) / (2 * macdAbs)) * 66;
  const rsiY = (v: number) => 20 + ((100 - v) / 100) * 76;
  const dateLabel = (value: string) => value?.slice(2) ?? "";

  return <div className="technical-chart">
    <div className="chart-legend">
      <span><i className="legend-candle-up" /> 상승</span><span><i className="legend-candle-down" /> 하락</span>
      <span className="legend-ma10">MA10</span><span className="legend-ma20">MA20</span><span className="legend-ma60">MA60</span><span className="legend-bb">볼린저밴드(20,2)</span>
    </div>
    <div className="chart-panel-title"><b>가격 · OHLC</b><span>{rows.length}개 봉</span></div>
    <svg className="technical-svg price-svg" viewBox={`0 0 ${width} 240`} role="img" aria-label="이동평균선과 볼린저밴드가 표시된 캔들 차트">
      {[0,1,2,3,4].map(n => <g key={n}><line x1={left} x2={width-right} y1={12+n*54} y2={12+n*54} className="technical-grid"/><text x={left-8} y={16+n*54} textAnchor="end" className="axis-label">{Math.round(pMax-(pMax-pMin)*n/4).toLocaleString("ko-KR")}</text></g>)}
      <path d={linePath("BB_UPPER",priceY)} className="indicator-line bb-line"/>
      <path d={linePath("BB_MIDDLE",priceY)} className="indicator-line bb-mid-line"/>
      <path d={linePath("BB_LOWER",priceY)} className="indicator-line bb-line"/>
      <path d={linePath("MA60",priceY)} className="indicator-line ma60-line"/>
      <path d={linePath("MA20",priceY)} className="indicator-line ma20-line"/>
      <path d={linePath("MA10",priceY)} className="indicator-line ma10-line"/>
      {rows.map((bar,i) => {
        const open=numeric(bar["시가"])!, high=numeric(bar["고가"])!, low=numeric(bar["저가"])!, close=numeric(bar["종가"])!;
        const up=close>=open, x=xAt(i), top=Math.min(priceY(open),priceY(close)), body=Math.max(1.5,Math.abs(priceY(open)-priceY(close)));
        return <g key={bar.date}><line x1={x} x2={x} y1={priceY(high)} y2={priceY(low)} className={up?"candle-wick up":"candle-wick down"}/><rect x={x-candleWidth/2} y={top} width={candleWidth} height={body} className={up?"candle-body up":"candle-body down"}/></g>;
      })}
    </svg>
    <div className="chart-date-axis"><span>{rows[0].date}</span><span>{rows[Math.floor(rows.length/2)].date}</span><span>{rows[rows.length-1].date}</span></div>

    <div className="chart-panel-title subchart-title"><b>거래량</b><span>거래량 막대</span></div>
    <svg className="technical-svg volume-svg" viewBox={`0 0 ${width} 76`} role="img" aria-label="거래량 차트">
      {[0,1,2].map(n=><line key={n} x1={left} x2={width-right} y1={8+n*28} y2={8+n*28} className="technical-grid"/>)}
      {rows.map((bar,i)=>{const volume=numeric(bar["거래량"])??0, up=(numeric(bar["종가"])??0)>=(numeric(bar["시가"])??0), h=volume/volumeMax*60;return <rect key={bar.date} x={xAt(i)-candleWidth/2} y={70-h} width={candleWidth} height={h} className={up?"volume-bar up":"volume-bar down"}/>;})}
    </svg>

    <div className="chart-panel-title subchart-title"><b>MACD (5, 10, 9)</b><span>MACD · Signal · Histogram</span></div>
    <svg className="technical-svg indicator-svg" viewBox={`0 0 ${width} 120`} role="img" aria-label="MACD 보조지표">
      <line x1={left} x2={width-right} y1={75} y2={75} className="zero-line"/>
      {rows.map((bar,i)=>{const v=numeric(bar.MACD_HIST)??0, y=macdY(v), zero=macdY(0);return <rect key={bar.date} x={xAt(i)-candleWidth/2} y={Math.min(y,zero)} width={candleWidth} height={Math.max(1,Math.abs(zero-y))} className={v>=0?"macd-positive":"macd-negative"}/>;})}
      <path d={linePath("MACD",macdY)} className="indicator-line macd-line"/>
      <path d={linePath("MACD_SIGNAL",macdY)} className="indicator-line signal-line"/>
    </svg>

    <div className="chart-panel-title subchart-title"><b>RSI (10 / 14)</b><span>과매수 70 · 과매도 30</span></div>
    <svg className="technical-svg indicator-svg" viewBox={`0 0 ${width} 112`} role="img" aria-label="RSI 보조지표">
      {[30,50,70].map(v=><g key={v}><line x1={left} x2={width-right} y1={rsiY(v)} y2={rsiY(v)} className={v===50?"zero-line":"threshold-line"}/><text x={left-8} y={rsiY(v)+3} textAnchor="end" className="axis-label">{v}</text></g>)}
      <path d={linePath("RSI14",rsiY)} className="indicator-line rsi14-line"/>
      <path d={linePath("RSI10",rsiY)} className="indicator-line rsi10-line"/>
    </svg>
    <div className="chart-date-axis"><span>{dateLabel(rows[0].date)}</span><span>{dateLabel(rows[rows.length-1].date)}</span></div>
    <div className="indicator-legend"><span className="legend-rsi10">RSI10</span><span className="legend-rsi14">RSI14</span><span className="legend-macd">MACD</span><span className="legend-signal">Signal</span></div>
  </div>;
}
function App() {
  const [chartPeriod, setChartPeriod] = useState<"daily" | "weekly">("daily");
  const [tickerInput, setTickerInput] = useState("");
  const [selectedTicker, setSelectedTicker] = useState("");
  const [stockAnalysis, setStockAnalysis] = useState<StockAnalysis | null>(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState("");
  const apiBase = "http://" + window.location.hostname + ":8000";
  const [apiStatus, setApiStatus] = useState("API 연결 확인 중");
  const [marketData, setMarketData] = useState<Partial<Record<MarketCode, MarketBulletin>>>({});
  const [scanMarket, setScanMarket] = useState<MarketCode>("ALL");
  const [scanLoading, setScanLoading] = useState(false);
  const [scanError, setScanError] = useState("");
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [scanProgress, setScanProgress] = useState<ScanJob | null>(null);
  const analystWorking = scanLoading || stockLoading;
  const analystStatus = scanLoading ? "FULL MARKET SCAN" : stockLoading ? "STOCK ANALYSIS" : "STANDBY";
  const analystCaption = scanLoading
    ? (scanProgress && scanProgress.total > 0
      ? `전 종목 분석 중 · ${scanProgress.progress.toLocaleString("ko-KR")} / ${scanProgress.total.toLocaleString("ko-KR")}`
      : "국내 전체 종목 목록을 불러오는 중입니다.")
    : stockLoading ? "선택한 종목의 차트와 지표를 분석 중입니다."
      : scanResult ? `분석 완료 · ${scanResult.scanned.toLocaleString("ko-KR")}종목 확인`
      : "대기 중 · 스캔을 시작하면 분석을 진행합니다.";

  async function runMarketScan() {
    setScanLoading(true); setScanError(""); setScanResult(null); setScanProgress(null);
    try {
      const start = await fetch(apiBase + "/api/scan/" + scanMarket, { method: "POST" });
      const started = await start.json();
      if (!start.ok) throw new Error(started.detail || "시장 스캔을 시작하지 못했습니다.");
      const jobId = String(started.job_id || "");
      if (!jobId) throw new Error("서버가 스캔 작업 ID를 반환하지 않았습니다.");
      while (true) {
        const response = await fetch(apiBase + "/api/scan/jobs/" + jobId);
        const job = await response.json() as ScanJob;
        if (!response.ok) throw new Error((job as unknown as {detail?:string}).detail || "스캔 상태를 확인하지 못했습니다.");
        setScanProgress(job);
        if (job.status === "completed" && job.result) { setScanResult(job.result); break; }
        if (job.status === "failed") throw new Error(job.error || "시장 스캔이 실패했습니다.");
        await new Promise(resolve => window.setTimeout(resolve, 1200));
      }
    } catch (error) {
      setScanError(error instanceof Error ? error.message : "시장 스캔에 실패했습니다.");
    } finally { setScanLoading(false); }
  }

  function openCandidate(item: ScanMatch) {
    setTickerInput(item.ticker);
    setSelectedTicker(item.ticker);
    document.getElementById("chart-desk")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  useEffect(() => {
    const controller = new AbortController();

    async function loadMarketData() {
      try {
        const healthResponse = await fetch(apiBase + "/api/health", {
          signal: controller.signal,
        });
        if (!healthResponse.ok) throw new Error("API health check failed");
        setApiStatus("Python API 연결됨");

        const codes: MarketCode[] = ["KOSPI", "KOSDAQ"];
        const results = await Promise.allSettled(
          codes.map(async (code) => {
            const response = await fetch(apiBase + "/api/market/" + code + "/bulletin", {
              signal: controller.signal,
            });
            if (!response.ok) throw new Error(`${code} market data unavailable`);
            return [code, await response.json()] as const;
          }),
        );

        const next: Partial<Record<MarketCode, MarketBulletin>> = {};
        results.forEach((result) => {
          if (result.status === "fulfilled") next[result.value[0]] = result.value[1] as MarketBulletin;
        });
        setMarketData(next);
        if (Object.keys(next).length === 0) setApiStatus("KRX 데이터 미수신");
        else if (Object.keys(next).length < 2) setApiStatus("일부 시장 데이터 미수신");
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        setApiStatus("Python API 연결 실패");
      }
    }

    void loadMarketData();
    return () => controller.abort();
  }, []);


  useEffect(() => {
    if (!selectedTicker) return;
    const controller = new AbortController();
    async function loadStock() {
      setStockLoading(true); setStockError("");
      try {
        const response = await fetch(apiBase + "/api/stocks/" + selectedTicker, { signal: controller.signal });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "종목 데이터를 불러오지 못했습니다.");
        setStockAnalysis(payload as StockAnalysis);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        setStockAnalysis(null); setStockError(error instanceof Error ? error.message : "종목 조회에 실패했습니다.");
      } finally { if (!controller.signal.aborted) setStockLoading(false); }
    }
    void loadStock();
    return () => controller.abort();
  }, [selectedTicker]);

  const activeBars = chartPeriod === "daily" ? stockAnalysis?.ohlcv ?? [] : stockAnalysis?.weekly_ohlcv ?? [];
  const kospi = marketData.KOSPI;
  const kosdaq = marketData.KOSDAQ;
  const bothMarketsReady = Boolean(kospi && kosdaq);
  const totalAdvancers = kospi && kosdaq ? kospi.advancers + kosdaq.advancers : undefined;
  const totalDecliners = kospi && kosdaq ? kospi.decliners + kosdaq.decliners : undefined;
  const totalTradingValue = kospi && kosdaq ? kospi.trading_value + kosdaq.trading_value : undefined;
  const sectors = [ ...(kospi?.sectors ?? []), ...(kosdaq?.sectors ?? []) ];
  const strongestSectors = [...sectors].sort((a, b) => b.change_pct - a.change_pct).filter((item) => item.change_pct > 0).slice(0, 5);
  const weakestSectors = [...sectors].sort((a, b) => a.change_pct - b.change_pct).filter((item) => item.change_pct < 0).slice(0, 5);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="돈물원 홈">
          <span className="brand-mark">돈</span>
          <span className="brand-copy">
            <strong>돈물원</strong>
            <small>DONMULWON <i>02</i></small>
          </span>
        </a>

        <div className="workspace-switch">
          <span className="workspace-icon">DW</span>
          <span><b>Investment Lab</b><small>개인 분석실</small></span>
          <ChevronDown size={15} />
        </div>

        <nav className="nav-groups" aria-label="주요 메뉴">
          <p className="nav-caption">WORKSPACE</p>
          {mainNav.map(({ label, icon: Icon, active }) => (
            <a className={active ? "nav-link active" : "nav-link"} href={label === "시장 스캐너" ? "#market-scanner" : "#"} key={label}>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {label === "시장 스캐너" && <span className="nav-count">SCAN</span>}
            </a>
          ))}

          <p className="nav-caption market-caption">MARKET</p>
          {marketNav.map(({ label, icon: Icon }) => (
            <a className="nav-link" href="#" key={label}>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
            </a>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="connection-card">
            <span className="connection-dot" />
            <span><b>{apiStatus === "Python API 연결됨" ? "분석 엔진 연결됨" : "시스템 연결 확인 중"}</b><small>{apiStatus}</small></span>
          </div>
          <a className="nav-link muted" href="#"><Settings2 size={17} />설정</a>
          <a className="nav-link muted" href="#"><CircleHelp size={17} />도움말</a>
          <div className="sidebar-version">DONMULWON 2.0 <span>WEB PREVIEW</span></div>
        </div>
      </aside>

      <section className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>WORKSPACE</span><b>/</b> 대시보드</div>
          <div className="top-actions">
            <span className="market-status"><i /> {apiStatus}</span>
            <button className="icon-button" aria-label="알림"><Bell size={17} /><i /></button>
            <div className="user-chip"><span className="user-avatar">나</span><span>투자자</span><ChevronDown size={14} /></div>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> YOUR PRIVATE MARKET OFFICE</div>
              <h1>좋은 매매는 <em>기다림</em>에서 시작됩니다.</h1>
              <p>시장 흐름을 확인하고, 조건을 만족하는 종목을 찾아보세요.</p>
            </div>
            <div className="date-pill"><Clock3 size={14} /> MARKET DESK <span>·</span> KST</div>
          </section>

          <section className="market-grid" aria-label="시장 요약">
            {([["KOSPI", "코스피", kospi], ["KOSDAQ", "코스닥", kosdaq]] as const).map(([code, label, data]) => {
              const index = data?.index;
              const rising = (index?.change_pct ?? 0) > 0;
              const falling = (index?.change_pct ?? 0) < 0;
              const values = index?.trend ?? [];
              const min = Math.min(...values, 0), max = Math.max(...values, 1);
              const points = values.map((value, i) => `${8 + i * (84 / Math.max(values.length - 1, 1))},${28 - ((value - min) / (max - min || 1)) * 22}`).join(" ");
              return <article className="market-card" key={code}>
                <div className="card-top"><span>{label}</span><span className="market-tag">종합지수</span></div>
                <div className="index-main">
                  <div>
                    <div className="index-close">{index ? index.close.toLocaleString("ko-KR", { maximumFractionDigits: 2 }) : "데이터 대기"}</div>
                    <div className={rising ? "index-change positive" : falling ? "index-change negative" : "index-change neutral"}>
                      {rising ? <ArrowUpRight size={15} /> : falling ? <ArrowDownRight size={15} /> : <span>—</span>}
                      {index ? `${index.change > 0 ? "+" : ""}${index.change.toLocaleString("ko-KR", { maximumFractionDigits: 2 })} (${index.change_pct > 0 ? "+" : ""}${index.change_pct.toFixed(2)}%)` : "등락률 미수신"}
                    </div>
                  </div>
                  <svg className={rising ? "index-sparkline positive" : falling ? "index-sparkline negative" : "index-sparkline"} viewBox="0 0 100 32" role="img" aria-label={`${label} 최근 지수 흐름`}>
                    {values.length > 1 && <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}
                  </svg>
                </div>
                <div className="market-foot"><span>{data ? `상승 ${formatCount(data.advancers)} / 하락 ${formatCount(data.decliners)} · ${data.date}` : "시장 데이터"}</span><span className="neutral-label">{index ? "수신" : "미수신"}</span></div>
              </article>;
            })}
            <article className="market-card accent-card">
              <div className="card-top"><span>시장 상승·하락 종목 수</span><Activity size={16} /></div>
              <div className="market-value">{formatCount(totalAdvancers)} <small>/ {formatCount(totalDecliners)}</small></div>
              <div className="market-foot"><span>코스피 + 코스닥 · 상승 / 하락</span><span className="neutral-label">{bothMarketsReady ? "수신" : "미수신"}</span></div>
            </article>
            <article className="market-card">
              <div className="card-top"><span>TRADING VALUE</span><BarChart3 size={16} /></div>
              <div className="market-value">{formatTradingValue(totalTradingValue)}</div>
              <div className="market-foot"><span>KOSPI + KOSDAQ 거래대금</span><span className="neutral-label">{bothMarketsReady ? "수신" : "미수신"}</span></div>
            </article>
          </section>

          <section className="office-layout">
            <article className="office-scene panel">
              <div className="section-heading">
                <div><span className="section-kicker">THE ANALYST ROOM</span><h2>너구리의 분석실</h2></div>
                <span className={analystWorking ? "live-label working" : "live-label"}><i /> {analystStatus}</span>
              </div>

              <div className="office-window">
                <div className="window-top"><span>DONMULWON MARKET OFFICE</span><span>EST. 2026</span></div>
                <div className="window-view">
                  <div className="sky-glow" />
                  <div className="skyline skyline-back"><i /><i /><i /><i /><i /></div>
                  <div className="skyline skyline-front"><i /><i /><i /><i /><i /><i /></div>
                  <div className="window-horizon" />
                  <span className="window-label">MARKET VIEW · SEOUL</span>
                </div>
                <div className="window-divider vertical" />
                <div className="window-divider horizontal" />
              </div>

              <div className="desk-area">
                <div className="desk-lamp"><span /></div>
                <div className={analystWorking ? "desk-character working" : "desk-character"}>
                  <div className="character-status"><i /> {analystWorking ? "ANALYST WORKING" : scanResult ? "ANALYSIS COMPLETE" : "ANALYST READY"}</div>
                  <div className="character-placeholder" aria-label="분석 상태에 따라 움직이는 너구리 분석가">🦝<span className="character-work-effect">⌨</span></div>
                  <div className="character-name">너구리 <span>CHIEF ANALYST</span></div>
                  <div className="character-caption">{analystCaption}</div>
                </div>
                <div className="desk-surface">
                  <div className="desk-monitor"><div /><div /><div /></div>
                  <div className="desk-keyboard" />
                  <div className="desk-cup" />
                </div>
                <div className="desk-front" />
              </div>
              <div className="scene-footer"><span>ONE ANALYST. ONE STANDARD.</span><span>분석 근거 없는 매수 의견은 제시하지 않습니다.</span></div>
            </article>

            <div className="right-column">
              <article className="panel chart-panel" id="chart-desk">
                <div className="section-heading compact">
                  <div><span className="section-kicker">TECHNICAL ANALYSIS DESK</span><h2>차트 분석 모니터</h2></div>
                  <form className="chart-controls" onSubmit={(event) => { event.preventDefault(); if (!/^\d{6}$/.test(tickerInput)) { setStockError("종목코드 6자리를 입력해 주세요."); return; } setSelectedTicker(tickerInput); }}><label className="ticker-search"><Search size={15}/><input aria-label="종목코드" value={tickerInput} onChange={(event) => setTickerInput(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="종목코드 6자리" maxLength={6} /></label><button className="ticker-submit" type="submit" disabled={stockLoading}>{stockLoading ? "조회 중" : "종목 조회"}</button><div className="period-toggle"><button type="button" className={chartPeriod === "daily" ? "selected" : ""} onClick={() => setChartPeriod("daily")}>일봉</button><button type="button" className={chartPeriod === "weekly" ? "selected" : ""} onClick={() => setChartPeriod("weekly")}>주봉</button></div></form>
                </div>
                <div className="chart-empty chart-workspace">
                  <div className="chart-grid-lines"><i /><i /><i /><i /></div>
                  {stockLoading ? <div className="chart-empty-content"><b>종목 데이터 조회 중…</b></div> : stockError ? <div className="chart-empty-content"><b>{stockError}</b></div> : stockAnalysis ? <PriceChart bars={activeBars} /> : <div className="chart-empty-content"><CandlestickChart size={25} /><b>종목 조회 대기</b><span>예: 삼성전자 005930 · 종목코드 입력 후 조회</span></div>}
                </div>
                {stockAnalysis && <div className="stock-plan">
                  <div className="stock-plan-heading"><b>{stockAnalysis.name} · 매매 기준 점검</b><span>{stockAnalysis.trading_date}</span></div>
                  <div className="stock-checks">
                    {[
                      ["RSI(10/14) 골든크로스", "rsi_cross_and_rising"],
                      ["MACD(5/10/9) 골든크로스", "macd_cross_and_rising"],
                      ["종가 MA10 상향 돌파", "ma10_breakout"],
                    ].map(([label, key]) => <span key={key} className={stockAnalysis.signal?.checks?.[key] ? "check-pass" : "check-fail"}>{stockAnalysis.signal?.checks?.[key] ? "충족" : "미충족"} · {label}</span>)}
                  </div>
                  {stockAnalysis.latest?.trade_plan?.ready ? <div className="stock-plan-grid">
                    <div><small>진입 참고 구간</small><b>{Math.round(stockAnalysis.latest.trade_plan.entry_low ?? 0).toLocaleString("ko-KR")} ~ {Math.round(stockAnalysis.latest.trade_plan.entry_high ?? 0).toLocaleString("ko-KR")}</b></div>
                    <div><small>손절 기준</small><b>{Math.round(stockAnalysis.latest.trade_plan.stop_loss ?? 0).toLocaleString("ko-KR")}</b></div>
                    <div><small>목표 1 · 2R</small><b>{Math.round(stockAnalysis.latest.trade_plan.target_1 ?? 0).toLocaleString("ko-KR")}</b></div>
                    <div><small>목표 2 · 3R</small><b>{Math.round(stockAnalysis.latest.trade_plan.target_2 ?? 0).toLocaleString("ko-KR")}</b></div>
                  </div> : <div className="scanner-state">변동성 데이터 부족으로 진입·손절·목표 가격을 계산할 수 없습니다.</div>}
                  <small className="stock-plan-warning">{stockAnalysis.latest?.trade_plan?.warning ?? "ATR 기반 참고값이며 매수 추천이 아닙니다."}</small>
                </div>}
                <div className="sector-watch-grid">
                  <section className="sector-watch-card">
                    <div className="sector-watch-title"><span><Flame size={15} /> 오늘의 강세 업종</span><small>상승률 상위</small></div>
                    {strongestSectors.length ? <ul className="sector-list">{strongestSectors.map((sector) => <li key={sector.market + sector.name}><span>{sector.name}<small>{sector.market === "KOSPI" ? "코스피" : "코스닥"} · {sector.stock_count}종목 평균</small></span><b className="positive">+{sector.change_pct.toFixed(2)}%</b></li>)}</ul> : <div className="sector-empty">업종 데이터 수신 대기 또는 상승 업종 없음</div>}
                  </section>
                  <section className="sector-watch-card">
                    <div className="sector-watch-title"><span><ShieldAlert size={15} /> 오늘의 약세 업종</span><small>하락률 상위</small></div>
                    {weakestSectors.length ? <ul className="sector-list">{weakestSectors.map((sector) => <li key={sector.market + sector.name}><span>{sector.name}<small>{sector.market === "KOSPI" ? "코스피" : "코스닥"} · {sector.stock_count}종목 평균</small></span><b className="negative">{sector.change_pct.toFixed(2)}%</b></li>)}</ul> : <div className="sector-empty">업종 데이터 수신 대기 또는 하락 업종 없음</div>}
                  </section>
                </div>
                <div className="market-one-line">
                  <span className="one-line-label">MARKET IN ONE LINE</span>
                  <p>{buildMarketNarrative(kospi, kosdaq)}</p>
                </div>
              </article>
            </div>
          </section>

          <section className="bottom-grid">
            <article className="panel analyst-panel">
              <div className="section-heading compact">
                <div><span className="section-kicker">AI ANALYST</span><h2>너구리</h2></div>
                <span className="single-agent">ONLY ONE</span>
              </div>
              <div className="analyst-profile">
                <div className="analyst-avatar">🦝</div>
                <div><b>수석 기술·시장 애널리스트</b><small>DONMULWON RESEARCH</small></div>
              </div>
              <p className="analyst-message">“시장은 매일 기회를 주지 않습니다. 조건이 맞을 때까지 기다리겠습니다.”</p>
              <div className="analyst-footer"><span><i /> 대기 중</span><span>OPENROUTER 연결 예정</span></div>
            </article>
            <article className="panel signal-panel">
              <div className="section-heading compact">
                <div><span className="section-kicker">CORE STRATEGY</span><h2>종목 발굴 조건</h2></div>
                <ShieldCheck size={18} />
              </div>
              <div className="signal-row"><span className="signal-index">01</span><span><b>RSI 골든크로스</b><small>RSI(10) ↑ RSI(14) · 동반 상승</small></span><span className="signal-pending">대기</span></div>
              <div className="signal-row"><span className="signal-index">02</span><span><b>MACD 골든크로스</b><small>MACD(5/10/9) · 상승 확인</small></span><span className="signal-pending">대기</span></div>
              <div className="signal-row"><span className="signal-index">03</span><span><b>MA10 상향 돌파</b><small>종가 기준 돌파 확인</small></span><span className="signal-pending">대기</span></div>
              <div className="strategy-note"><Sparkles size={14} /> 세 가지 조건을 모두 충족해야 발굴 후보가 됩니다.</div>
            </article>
            <article className="panel checklist-panel">
              <div className="section-heading compact">
                <div><span className="section-kicker">SYSTEM STATUS</span><h2>연결 및 준비 상태</h2></div>
                <Database size={18} />
              </div>
              <div className="system-row"><span>국내 시장 데이터</span><span className="status-wait">{bothMarketsReady ? "수신" : apiStatus}</span></div>
              <div className="system-row"><span>OpenRouter AI</span><span className="status-wait">연결 전</span></div>
              <div className="system-row"><span>토스증권 API</span><span className="status-wait">연결 전</span></div>
              <div className="system-row"><span>분석 데이터베이스</span><span className="status-wait">점검 예정</span></div>
              <div className="system-hint"><ArrowDownRight size={14} /> 실제 연결 및 응답 검증 후 상태가 변경됩니다.</div>
            </article>
          </section>


          <section className="panel scanner-panel" id="market-scanner">
            <div className="section-heading compact">
              <div><span className="section-kicker">RULE-BASED DISCOVERY</span><h2>시장 스캐너</h2></div>
              <span className="single-agent">DAILY SIGNAL · CLOSE CONFIRMED</span>
            </div>
            <p className="scanner-intro">일봉 필수 조건과 240일선 필터를 통과한 종목을 주봉 추세로 A·B·C 등급화합니다. A부터 C 순서로 정렬하며 주봉이 약한 종목도 C등급으로 확인할 수 있습니다.</p>
            <div className="scanner-toolbar">
              <div className="period-toggle">
                <button type="button" className={scanMarket === "ALL" ? "selected" : ""} onClick={() => setScanMarket("ALL")}>전체 시장</button>
                <button type="button" className={scanMarket === "KOSPI" ? "selected" : ""} onClick={() => setScanMarket("KOSPI")}>코스피</button>
                <button type="button" className={scanMarket === "KOSDAQ" ? "selected" : ""} onClick={() => setScanMarket("KOSDAQ")}>코스닥</button>
              </div>
              <button className="ticker-submit scan-submit" type="button" onClick={runMarketScan} disabled={scanLoading}>{scanLoading ? "전 종목 분석 중…" : "전체 종목 검색 시작"}</button>
              {scanResult && <span className="scan-meta">{scanResult.date} · {scanResult.scanned.toLocaleString("ko-KR")}종목 검사 · 후보 {scanResult.matches.length}개 · A {scanResult.grade_counts?.A ?? 0} / B {scanResult.grade_counts?.B ?? 0} / C {scanResult.grade_counts?.C ?? 0} · 오류 {scanResult.error_count}건</span>}
            </div>
            {scanLoading && <div className="scanner-state"><span className="loading-pulse" /> {scanProgress && scanProgress.total > 0 ? `진행 ${scanProgress.progress.toLocaleString("ko-KR")} / ${scanProgress.total.toLocaleString("ko-KR")} · 현재 종목 ${scanProgress.current_ticker ?? "준비 중"}` : "시장 종목 목록을 준비하고 있습니다."}</div>}
            {scanError && <div className="scanner-state error">{scanError}</div>}
            {scanResult && <div className="scanner-table-wrap">
              {scanResult.matches.length === 0 ? <div className="scanner-state">현재 기준을 모두 충족한 종목이 없습니다. 조건을 임의로 완화하지 않았습니다.</div> :
              <table className="scanner-table">
                <thead><tr><th>등급</th><th>종목</th><th>종가</th><th>RSI 10 / 14</th><th>거래량 / 10일 평균</th><th>주봉 추세</th><th>진입 참고 구간</th><th>손절 / 목표 1</th><th>240일선 필터</th><th></th></tr></thead>
                <tbody>{(["A", "B", "C"] as const).map((grade) => {
                  const group = scanResult.matches.filter((item) => (item.weekly?.grade ?? "C") === grade);
                  if (group.length === 0) return null;
                  const groupTitle = grade === "A" ? "매수 매우 추천" : grade === "B" ? "매수 추천" : "매수 보류";
                  return <Fragment key={grade}>
                    <tr className={`grade-divider grade-divider-${grade.toLowerCase()}`}><td colSpan={10}><b>{grade}등급 · {groupTitle}</b><span>{group.length}종목</span></td></tr>
                    {group.map((item) => {
                      const below240 = typeof item.latest?.ma240 === "number" && typeof item.latest?.close === "number" && item.latest.close < item.latest.ma240;
                      return <tr key={item.ticker}>
                        <td><span className={`grade-badge grade-${(item.weekly?.grade ?? "C").toLowerCase()}`}>{item.weekly?.grade ?? "C"}</span><small>{item.weekly?.grade_score ?? 0}점</small></td>
                        <td><b>{item.name}</b><small>{item.ticker}</small></td>
                        <td>{item.latest?.close?.toLocaleString("ko-KR") ?? "—"}</td>
                        <td>{item.signal?.rsi10?.toFixed(1) ?? "—"} / {item.signal?.rsi14?.toFixed(1) ?? "—"}</td>
                        <td>{typeof item.latest?.volume_ratio === "number" ? item.latest.volume_ratio.toFixed(2) + "x" : "—"}</td>
                        <td title={item.weekly?.grade_reason}>{item.weekly?.ready ? item.weekly.trend : "데이터 부족"}</td>
                        <td>{item.latest?.trade_plan?.ready ? `${Math.round(item.latest.trade_plan.entry_low ?? 0).toLocaleString("ko-KR")} ~ ${Math.round(item.latest.trade_plan.entry_high ?? 0).toLocaleString("ko-KR")}` : "산출 불가"}</td>
                        <td>{item.latest?.trade_plan?.ready ? `${Math.round(item.latest.trade_plan.stop_loss ?? 0).toLocaleString("ko-KR")} / ${Math.round(item.latest.trade_plan.target_1 ?? 0).toLocaleString("ko-KR")}` : "—"}</td>
                        <td><span className={below240 ? "risk-flag" : "risk-ok"}>{below240 ? "제외 대상" : "통과"}</span></td>
                        <td><button type="button" className="row-action" onClick={() => openCandidate(item)}>차트 분석</button></td>
                      </tr>;
                    })}
                  </Fragment>;
                })}</tbody>
              </table>}
            </div>}
            <div className="scanner-footnote">데이터 출처: KRX 종목 목록 및 설정된 시세 공급자. 스캔은 조회 전용이며 주문을 실행하지 않습니다. 장중 데이터는 종가 확정 신호와 구분해 해석해야 합니다.</div>
          </section>

          <footer className="page-footer"><span>© 2026 DONMULWON 2</span><span>DATA FIRST · RISK AWARE · NO AUTO TRADING</span></footer>
        </div>
      </section>
    </main>
  );
}

export default App;
