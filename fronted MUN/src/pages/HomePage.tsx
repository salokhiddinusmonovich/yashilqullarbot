import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import logoImg from "./photo_2025-10-08_22-18-51.jpg";
import { useLang } from "../contexts/LanguageContext";

const GLOBAL_CSS = `
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Montserrat:wght@700;900&family=Inter:wght@400;500&display=swap');
@keyframes yq-fadeUp{from{opacity:0;transform:translateY(36px)}to{opacity:1;transform:translateY(0)}}
@keyframes yq-fadeIn{from{opacity:0}to{opacity:1}}
@keyframes yq-introOut{0%{opacity:1;transform:scale(1)}100%{opacity:0;transform:scale(1.06)}}
@keyframes yq-logoIn{from{opacity:0;transform:scale(0.55)}to{opacity:1;transform:scale(1)}}
@keyframes yq-pulse{0%,100%{opacity:1}50%{opacity:0.3}}
@keyframes yq-float{0%,100%{transform:translateY(0px)}50%{transform:translateY(-12px)}}
@keyframes yq-glow{0%,100%{filter:drop-shadow(0 0 12px rgba(16,185,129,.5))}50%{filter:drop-shadow(0 0 28px rgba(16,185,129,.95))}}
@keyframes yq-spin-slow{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
@keyframes yq-spin-rev{from{transform:rotate(0deg)}to{transform:rotate(-360deg)}}
@keyframes yq-introBar{from{width:0}to{width:120px}}
@keyframes yq-ringPulse{0%,100%{opacity:.12}50%{opacity:.3}}

.yq-intro{position:fixed;inset:0;z-index:9999;background:#050505;display:flex;flex-direction:column;align-items:center;justify-content:center;animation:yq-fadeIn .25s ease}
.yq-intro.out{animation:yq-introOut .65s cubic-bezier(.4,0,.6,1) forwards}
.yq-intro-logo{animation:yq-logoIn .8s cubic-bezier(.22,1,.36,1) .15s both}
.yq-intro-label{animation:yq-fadeUp .65s ease .8s both}
.yq-intro-bar{width:0;height:2px;background:#10b981;border-radius:2px;margin-top:32px;animation:yq-introBar 1.6s cubic-bezier(.4,0,.2,1) .5s both}

.hw{display:block;font-family:'Anton',sans-serif;line-height:.9;text-transform:uppercase;letter-spacing:-.01em;color:#fff}
.hw-em{color:#10b981!important}
.hw:nth-child(1){animation:yq-fadeUp .85s cubic-bezier(.22,1,.36,1) .05s both}
.hw:nth-child(2){animation:yq-fadeUp .85s cubic-bezier(.22,1,.36,1) .15s both}
.hw:nth-child(3){animation:yq-fadeUp .85s cubic-bezier(.22,1,.36,1) .25s both}
.hw:nth-child(4){animation:yq-fadeUp .85s cubic-bezier(.22,1,.36,1) .35s both}
.hw:nth-child(5){animation:yq-fadeUp .85s cubic-bezier(.22,1,.36,1) .45s both}
.yq-sub{animation:yq-fadeUp .7s ease .55s both}
.yq-btns{animation:yq-fadeUp .7s ease .65s both}
.yq-stats{animation:yq-fadeUp .7s ease .75s both}
.yq-logo-anim{animation:yq-fadeIn 1s ease .3s both,yq-float 4s ease-in-out 1.3s infinite,yq-glow 3s ease-in-out 1.3s infinite}
.yq-dot{animation:yq-pulse 1.8s ease-in-out infinite}

.yq-ring-a{position:absolute;border-radius:50%;border:1.5px solid rgba(16,185,129,.22);animation:yq-spin-slow 10s linear infinite}
.yq-ring-b{position:absolute;border-radius:50%;border:1px dashed rgba(16,185,129,.14);animation:yq-spin-rev 16s linear infinite}
.yq-ring-c{position:absolute;border-radius:50%;border:1px solid rgba(16,185,129,.08);animation:yq-ringPulse 4s ease-in-out infinite}
.yq-orbit-dot{position:absolute;width:7px;height:7px;background:#10b981;border-radius:50%;box-shadow:0 0 10px #10b981,0 0 20px rgba(16,185,129,.5)}

.yq-btn-primary{background:#10b981;color:#fff;border:none;font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;padding:14px 28px;border-radius:10px;display:inline-flex;align-items:center;gap:8px;text-decoration:none;cursor:pointer;transition:background .2s,transform .15s,box-shadow .2s;white-space:nowrap}
.yq-btn-primary:hover{background:#059669;transform:translateY(-2px);box-shadow:0 8px 30px rgba(16,185,129,.35)}
.yq-btn-ghost{background:transparent;color:rgba(255,255,255,.65);border:1px solid rgba(255,255,255,.14);font-family:'Montserrat',sans-serif;font-size:11px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;padding:14px 28px;border-radius:10px;display:inline-flex;align-items:center;gap:8px;text-decoration:none;cursor:pointer;transition:border-color .2s,color .2s,transform .15s;white-space:nowrap}
.yq-btn-ghost:hover{border-color:rgba(16,185,129,.5);color:#fff;transform:translateY(-2px)}
.yq-stat-pill{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:10px 18px;display:inline-flex;flex-direction:column;align-items:center;transition:border-color .2s,background .2s}
.yq-stat-pill:hover{border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.05)}
.yq-committee-card{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.05);border-radius:16px;padding:24px;cursor:pointer;transition:border-color .25s,background .25s,transform .2s,box-shadow .25s}
.yq-committee-card:hover{border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.05);transform:translateY(-4px);box-shadow:0 16px 40px rgba(0,0,0,.4)}

.yq-hero-grid{display:grid;grid-template-columns:1fr 1fr;align-items:center;width:100%;padding:0 clamp(1.25rem,5vw,5rem)}
.yq-committees-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}

@media(max-width:1024px){.yq-committees-grid{grid-template-columns:1fr 1fr}}
@media(max-width:768px){
  .yq-hero-grid{grid-template-columns:1fr;padding:0 1.25rem;gap:1rem}
  .yq-logo-col{order:-1;display:flex;justify-content:center;overflow:hidden;padding:1.5rem 0}
  .yq-committees-grid{grid-template-columns:1fr}
  .yq-btns{flex-direction:column}
  .yq-btns a{justify-content:center;width:100%;box-sizing:border-box}
  .yq-cta-btns{flex-direction:column!important;align-items:stretch!important}
  .yq-cta-btns a{justify-content:center}
  .hw{font-size:clamp(2.2rem,11vw,4rem)!important;word-break:break-word}
}
@media(max-width:400px){.hw{font-size:clamp(1.8rem,10vw,2.8rem)!important}}
`;

const LogoCircle = ({ size }: { size: number }) => (
  <div style={{
    position: "relative",
    width: size,
    height: size,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  }}>
    <div className="yq-ring-c" style={{ width: size * 1.9, height: size * 1.9 }} />
    <div className="yq-ring-b" style={{ width: size * 1.55, height: size * 1.55 }} />
    <div className="yq-ring-a" style={{ width: size * 1.28, height: size * 1.28 }} />
    <div style={{ position:"absolute", width: size * 1.28, height: size * 1.28, animation:"yq-spin-slow 10s linear infinite", display:"flex", alignItems:"flex-start", justifyContent:"center" }}>
      <div className="yq-orbit-dot" style={{ marginTop: "-3.5px" }} />
    </div>
    <div style={{ position:"absolute", width: size * 1.55, height: size * 1.55, animation:"yq-spin-rev 16s linear infinite", display:"flex", alignItems:"flex-start", justifyContent:"center" }}>
      <div className="yq-orbit-dot" style={{ marginTop: "-3.5px", width: 5, height: 5 }} />
    </div>
    <div style={{
      position: "relative",
      zIndex: 2,
      width: size,
      height: size,
      borderRadius: "50%",
      border: "2px solid rgba(16,185,129,0.4)",
      backgroundColor: "#f0ede6",
      backgroundImage: `url(${logoImg})`,
      backgroundSize: "82%",
      backgroundPosition: "center center",
      backgroundRepeat: "no-repeat",
    }} />
  </div>
);

export const HomePage = () => {
  const { t } = useLang();
  const [introVisible, setIntroVisible] = useState(true);
  const [introOut, setIntroOut] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = document.createElement("style");
    el.textContent = GLOBAL_CSS;
    document.head.appendChild(el);
    const timer1 = setTimeout(() => setIntroOut(true), 2100);
    const timer2 = setTimeout(() => setIntroVisible(false), 2750);
    return () => { clearTimeout(timer1); clearTimeout(timer2); document.head.removeChild(el); };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let animId: number;
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight; };
    resize();
    window.addEventListener("resize", resize);
    type Dot = { x: number; y: number; vx: number; vy: number; r: number };
    const dots: Dot[] = Array.from({ length: 60 }, () => ({
      x: Math.random() * canvas.width, y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.45, vy: (Math.random() - 0.5) * 0.45,
      r: Math.random() * 1.8 + 0.8,
    }));
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const d of dots) {
        d.x += d.vx; d.y += d.vy;
        if (d.x < 0 || d.x > canvas.width) d.vx *= -1;
        if (d.y < 0 || d.y > canvas.height) d.vy *= -1;
      }
      for (let i = 0; i < dots.length; i++) {
        for (let j = i + 1; j < dots.length; j++) {
          const dx = dots[i].x - dots[j].x, dy = dots[i].y - dots[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            ctx.beginPath();
            ctx.strokeStyle = `rgba(16,185,129,${0.18 * (1 - dist / 150)})`;
            ctx.lineWidth = 0.7;
            ctx.moveTo(dots[i].x, dots[i].y);
            ctx.lineTo(dots[j].x, dots[j].y);
            ctx.stroke();
          }
        }
      }
      for (const d of dots) {
        ctx.beginPath(); ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(16,185,129,0.5)"; ctx.fill();
      }
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => { cancelAnimationFrame(animId); window.removeEventListener("resize", resize); };
  }, []);

  const stats = [
    { value: t.stat0val, label: t.stat0lbl },
    { value: t.stat1val, label: t.stat1lbl },
    { value: t.stat2val, label: t.stat2lbl },
    { value: t.stat3val, label: t.stat3lbl },
  ];
  const colors = ["from-emerald-600 to-teal-400", "from-amber-600 to-amber-400", "from-red-700 to-red-500", "from-orange-700 to-emerald-500"];

  return (
    <>
      {introVisible && (
        <div className={`yq-intro${introOut ? " out" : ""}`} aria-hidden="true">
          <div className="yq-intro-logo" style={{ position:"relative", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <div style={{ position:"absolute", width:150, height:150, borderRadius:"50%", border:"1.5px solid rgba(16,185,129,.4)", animation:"yq-spin-slow 8s linear infinite" }} />
            <div style={{ position:"absolute", width:175, height:175, borderRadius:"50%", border:"1px dashed rgba(16,185,129,.2)", animation:"yq-spin-rev 12s linear infinite" }} />
            <div style={{
              width: 110, height: 110, borderRadius: "50%",
              border: "2px solid rgba(16,185,129,0.5)",
              boxShadow: "0 0 30px rgba(16,185,129,.7), 0 0 60px rgba(16,185,129,.3)",
              backgroundColor: "#f0ede6",
              backgroundImage: `url(${logoImg})`,
              backgroundSize: "82%",
              backgroundPosition: "center center",
              backgroundRepeat: "no-repeat",
            }} />
          </div>
          <div className="yq-intro-label" style={{ textAlign:"center", marginTop:"28px" }}>
            <div style={{ fontFamily:"'Anton',sans-serif", fontSize:"clamp(1.8rem,6vw,3.2rem)", color:"#fff", letterSpacing:".06em", textTransform:"uppercase", lineHeight:1 }}>Yashil Qo'llar</div>
            <div style={{ fontFamily:"'Anton',sans-serif", fontSize:"clamp(1.8rem,6vw,3.2rem)", color:"#10b981", letterSpacing:".06em", textTransform:"uppercase", lineHeight:1, marginTop:"4px" }}>MUN 2026</div>
          </div>
          <div className="yq-intro-bar" />
        </div>
      )}

      <main className="bg-stone-950 min-h-screen">

        {/* HERO */}
        <section style={{ position:"relative", overflow:"hidden", paddingTop:"clamp(5rem,12vw,9rem)", paddingBottom:"3rem", minHeight:"92vh", display:"flex", alignItems:"center" }}>
          <canvas ref={canvasRef} style={{ position:"absolute", inset:0, width:"100%", height:"100%", pointerEvents:"none", zIndex:1 }} />
          <div style={{ position:"absolute", inset:0, zIndex:2, pointerEvents:"none", background:"radial-gradient(ellipse 70% 60% at 65% 50%,rgba(16,185,129,.07) 0%,transparent 70%)" }} />
          <div style={{ position:"absolute", inset:0, zIndex:2, pointerEvents:"none", backgroundImage:`linear-gradient(rgba(16,185,129,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(16,185,129,.03) 1px,transparent 1px)`, backgroundSize:"64px 64px" }} />

          <div className="yq-hero-grid" style={{ position:"relative", zIndex:3 }}>
            {/* TEXT */}
            <div>
              <div className="yq-sub" style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"1.5rem" }}>
                <span className="yq-dot" style={{ display:"inline-block", width:8, height:8, borderRadius:"50%", background:"#10b981" }} />
                <span style={{ fontFamily:"'Montserrat',sans-serif", fontSize:"10px", fontWeight:700, letterSpacing:"2.5px", textTransform:"uppercase", color:"rgba(255,255,255,.4)" }}>{t.dateTag}</span>
              </div>
              <h1 style={{ margin:0, padding:0 }}>
                <span className="hw" style={{ fontSize:"clamp(2.8rem,8vw,8rem)" }}>{t.heroLine1}</span>
                <span className="hw" style={{ fontSize:"clamp(2.8rem,8vw,8rem)" }}>{t.heroLine2}</span>
                <span className="hw" style={{ fontSize:"clamp(2.8rem,8vw,8rem)" }}>{t.heroLine3}</span>
                <span className="hw" style={{ fontSize:"clamp(2.8rem,8vw,8rem)" }}>{t.heroLine4}</span>
                <span className="hw hw-em" style={{ fontSize:"clamp(2.8rem,8vw,8rem)" }}>{t.heroLine5}</span>
              </h1>
              <div className="yq-sub" style={{ marginTop:"1.5rem" }}>
                <p style={{ fontFamily:"'Inter',sans-serif", color:"rgba(255,255,255,.45)", fontSize:"clamp(.875rem,1.5vw,1rem)", lineHeight:1.75, maxWidth:"480px", margin:0 }}>{t.heroSub}</p>
                <div style={{ display:"flex", alignItems:"center", gap:"8px", marginTop:"14px" }}>
                  <span className="yq-dot" style={{ display:"inline-block", width:7, height:7, borderRadius:"50%", background:"#10b981" }} />
                  <span style={{ fontFamily:"'Montserrat',sans-serif", fontSize:"10px", fontWeight:700, letterSpacing:"2px", textTransform:"uppercase", color:"#10b981" }}>{t.heroBadge}</span>
                </div>
              </div>
              <div className="yq-btns" style={{ display:"flex", flexWrap:"wrap", gap:"12px", marginTop:"1.75rem" }}>
                <Link to="/registration" className="yq-btn-primary">
                  {t.btnRegister}
                  <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
                </Link>
                <Link to="/committees" className="yq-btn-ghost">
                  <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
                  {t.btnCommittees}
                </Link>
              </div>
              <div className="yq-stats" style={{ display:"flex", flexWrap:"wrap", gap:"8px", marginTop:"1.5rem" }}>
                {stats.map((s, i) => (
                  <div key={i} className="yq-stat-pill">
                    <span style={{ fontFamily:"'Anton',sans-serif", fontSize:"22px", color:"#fff", lineHeight:1 }}>{s.value}</span>
                    <span style={{ fontFamily:"'Montserrat',sans-serif", fontSize:"9px", fontWeight:700, letterSpacing:"2px", textTransform:"uppercase", color:"rgba(16,185,129,.65)", marginTop:"4px" }}>{s.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* LOGO */}
            <div className="yq-logo-anim yq-logo-col" style={{ display:"flex", alignItems:"center", justifyContent:"center" }}>
              <LogoCircle size={260} />
            </div>
          </div>
        </section>

        {/* COMMITTEES */}
        <section style={{ padding:"4rem clamp(1.25rem,5vw,5rem)" }}>
          <div style={{ maxWidth:"90rem", margin:"0 auto" }}>
            <div style={{ marginBottom:"2.5rem" }}>
              <span style={{ color:"#10b981", fontSize:"10px", fontWeight:700, letterSpacing:"2.5px", textTransform:"uppercase", fontFamily:"'Montserrat',sans-serif", display:"block", marginBottom:"10px" }}>{t.councilsLabel}</span>
              <h2 style={{ fontFamily:"'Anton',sans-serif", fontSize:"clamp(1.6rem,4vw,2.8rem)", color:"#fff", textTransform:"uppercase", margin:0 }}>{t.councilsTitle}</h2>
            </div>
            <div className="yq-committees-grid">
              {t.committees.map((c, i) => (
                <div key={c.code} className="yq-committee-card">
                  <div className={`inline-flex items-center justify-center bg-gradient-to-br ${colors[i]} text-white`}
                    style={{ fontSize:"10px", fontWeight:900, letterSpacing:"1px", textTransform:"uppercase", fontFamily:"'Montserrat',sans-serif", padding:"5px 12px", borderRadius:"8px", marginBottom:"16px" }}>
                    {c.code}
                  </div>
                  <h3 style={{ fontFamily:"'Montserrat',sans-serif", fontWeight:700, color:"#fff", fontSize:"15px", marginBottom:"8px", marginTop:0 }}>{c.name}</h3>
                  <p style={{ color:"rgba(255,255,255,.38)", fontSize:"13px", lineHeight:1.65, margin:0 }}>{c.topic}</p>
                </div>
              ))}
            </div>
            <div style={{ textAlign:"center", marginTop:"2rem" }}>
              <Link to="/committees" className="yq-btn-ghost">
                {t.viewAll}
                <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3"/></svg>
              </Link>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section style={{ padding:"6rem clamp(1.25rem,5vw,5rem)", position:"relative", overflow:"hidden" }}>
          <div style={{ position:"absolute", inset:0, background:"radial-gradient(ellipse at center,rgba(16,185,129,.08) 0%,transparent 60%)", pointerEvents:"none" }} />
          <div style={{ position:"relative", zIndex:10, maxWidth:"52rem", margin:"0 auto", textAlign:"center" }}>
            <div style={{ marginBottom:"24px", display:"flex", justifyContent:"center" }}>
              <div className="yq-logo-anim"><LogoCircle size={72} /></div>
            </div>
            <h2 style={{ fontFamily:"'Anton',sans-serif", fontSize:"clamp(2rem,7vw,5rem)", color:"#fff", textTransform:"uppercase", lineHeight:.92, margin:"0 0 24px" }}>
              {t.ctaTitle1}{" "}<span style={{ color:"#10b981" }}>{t.ctaTitle2}</span>
            </h2>
            <p style={{ fontFamily:"'Inter',sans-serif", color:"rgba(255,255,255,.48)", fontSize:"clamp(.875rem,1.5vw,1rem)", lineHeight:1.75, marginBottom:"2.5rem" }}>{t.ctaSub}</p>
            <div className="yq-cta-btns" style={{ display:"flex", flexWrap:"wrap", gap:"12px", justifyContent:"center" }}>
              <Link to="/registration" className="yq-btn-primary" style={{ padding:"16px 40px", fontSize:"12px" }}>{t.btnRegister}</Link>
              <Link to="/contact" className="yq-btn-ghost" style={{ padding:"16px 40px", fontSize:"12px" }}>{t.btnContact}</Link>
            </div>
          </div>
        </section>

      </main>
    </>
  );
};
