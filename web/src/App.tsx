import {
  Activity,
  ArrowDownRight,
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
  Settings2,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Wallet,
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
  { label: "내 계좌", icon: Wallet },
];

function App() {
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
            <a className={active ? "nav-link active" : "nav-link"} href="#" key={label}>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {label === "시장 스캐너" && <span className="nav-count">3</span>}
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
            <span><b>시스템 준비 중</b><small>실제 데이터 연결 전</small></span>
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
            <span className="market-status"><i /> 데이터 연결 대기</span>
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
            <article className="market-card">
              <div className="card-top"><span>KOSPI</span><span className="market-tag">종합지수</span></div>
              <div className="market-value placeholder">데이터 연결 대기</div>
              <div className="market-foot"><span>지수 및 등락률</span><span className="neutral-label">미수신</span></div>
            </article>
            <article className="market-card">
              <div className="card-top"><span>KOSDAQ</span><span className="market-tag">기술주 시장</span></div>
              <div className="market-value placeholder">데이터 연결 대기</div>
              <div className="market-foot"><span>지수 및 등락률</span><span className="neutral-label">미수신</span></div>
            </article>
            <article className="market-card accent-card">
              <div className="card-top"><span>MARKET BREADTH</span><Activity size={16} /></div>
              <div className="market-value placeholder">— <small>/ —</small></div>
              <div className="market-foot"><span>상승 종목 / 하락 종목</span><span className="neutral-label">미수신</span></div>
            </article>
            <article className="market-card">
              <div className="card-top"><span>TRADING VALUE</span><BarChart3 size={16} /></div>
              <div className="market-value placeholder">— <small>억원</small></div>
              <div className="market-foot"><span>시장 전체 거래대금</span><span className="neutral-label">미수신</span></div>
            </article>
          </section>

          <section className="office-layout">
            <article className="office-scene panel">
              <div className="section-heading">
                <div><span className="section-kicker">THE ANALYST ROOM</span><h2>너구리의 분석실</h2></div>
                <span className="live-label"><i /> STANDBY</span>
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
                <div className="desk-character">
                  <div className="character-status"><i /> ANALYST AVAILABLE</div>
                  <div className="character-placeholder" aria-label="너구리 캐릭터 에셋 연결 예정">🦝</div>
                  <div className="character-name">너구리 <span>CHIEF ANALYST</span></div>
                  <div className="character-caption">시장 데이터를 기다리는 중입니다.</div>
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
            </div>
          </section>

          <section className="bottom-grid">
            <article className="panel chart-panel">
              <div className="section-heading compact">
                <div><span className="section-kicker">MARKET MOMENTUM</span><h2>시장 추세 모니터</h2></div>
                <span className="period-select">일봉 <ChevronDown size={13} /></span>
              </div>
              <div className="chart-empty">
                <div className="chart-grid-lines"><i /><i /><i /><i /></div>
                <div className="chart-empty-content"><TrendingUp size={23} /><b>시장 데이터 연결 후 표시됩니다</b><span>실제 시세가 연결되기 전까지 임의의 차트를 표시하지 않습니다.</span></div>
              </div>
            </article>
            <article className="panel checklist-panel">
              <div className="section-heading compact">
                <div><span className="section-kicker">SYSTEM STATUS</span><h2>연결 및 준비 상태</h2></div>
                <Database size={18} />
              </div>
              <div className="system-row"><span>국내 시장 데이터</span><span className="status-wait">연결 전</span></div>
              <div className="system-row"><span>OpenRouter AI</span><span className="status-wait">연결 전</span></div>
              <div className="system-row"><span>토스증권 API</span><span className="status-wait">연결 전</span></div>
              <div className="system-row"><span>분석 데이터베이스</span><span className="status-wait">점검 예정</span></div>
              <div className="system-hint"><ArrowDownRight size={14} /> 실제 연결 및 응답 검증 후 상태가 변경됩니다.</div>
            </article>
          </section>

          <footer className="page-footer"><span>© 2026 DONMULWON 2</span><span>DATA FIRST · RISK AWARE · NO AUTO TRADING</span></footer>
        </div>
      </section>
    </main>
  );
}

export default App;
