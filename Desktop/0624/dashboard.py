import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
import glob
import datetime

st.set_page_config(page_title="광고 성과 대시보드", layout="wide", page_icon="📊")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #F0F4FF !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stMain"] { background: #F0F4FF !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #E8EEFF 0%, #EDE8FF 100%) !important;
    border-right: 1px solid #D4D8F0 !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] label {
    color: #4A4E7A !important; font-weight: 600 !important; letter-spacing: 0.02em !important;
}
[data-testid="stSidebar"] [data-baseweb="select"],
[data-testid="stSidebar"] [data-baseweb="input"] {
    background: #FFFFFF99 !important; border: 1px solid #C4C8E8 !important; border-radius: 10px !important;
}

[data-testid="stMetric"] {
    background: #FFFFFF !important; border: 1px solid #E0E4F8 !important;
    border-radius: 16px !important; padding: 16px 20px !important;
    box-shadow: 0 2px 12px rgba(100,110,200,0.08) !important;
}
[data-testid="stMetric"]:hover { box-shadow: 0 4px 20px rgba(100,110,200,0.14) !important; }
[data-testid="stMetricLabel"] {
    font-size: 0.75rem !important; font-weight: 600 !important;
    letter-spacing: 0.08em !important; text-transform: uppercase !important; color: #8A8EBA !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.5rem !important; font-weight: 700 !important;
    color: #2D3172 !important; letter-spacing: -0.02em !important;
}

[data-testid="stTabs"] [role="tablist"] {
    background: #E8EEFF !important; border-radius: 12px !important; padding: 4px !important;
}
[data-testid="stTabs"] [role="tab"] {
    border-radius: 9px !important; font-weight: 500 !important;
    color: #6A6EA8 !important; padding: 6px 16px !important; font-size: 0.85rem !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #FFFFFF !important; color: #2D3172 !important;
    font-weight: 700 !important; box-shadow: 0 1px 6px rgba(100,110,200,0.12) !important;
}

h1 { color: #2D3172 !important; font-weight: 700 !important; letter-spacing: -0.03em !important; }
h2, h3 { color: #3D4182 !important; font-weight: 600 !important; }

[data-testid="stDataFrame"] {
    border-radius: 12px !important; overflow: hidden !important; border: 1px solid #E0E4F8 !important;
}
hr { border-color: #D8DCFA !important; }
[data-testid="stCaptionContainer"] { color: #8A8EBA !important; font-size: 0.8rem !important; }
[data-testid="stDownloadButton"] button {
    background: linear-gradient(135deg, #A8B8F8, #C4A8F0) !important;
    border: none !important; border-radius: 10px !important;
    color: #2D3172 !important; font-weight: 600 !important;
}
.alert-card {
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
    font-size: 14px; line-height: 1.6;
}
.alert-danger { background: #FFE8EC; border-left: 4px solid #FF6B8A; }
.alert-warn   { background: #FFF8E0; border-left: 4px solid #FFD166; }
.alert-ok     { background: #E8F8EE; border-left: 4px solid #A8E0B8; }
.top-material-card {
    background: #fff; border-radius: 14px; border: 1px solid #E0E4F8;
    padding: 16px; box-shadow: 0 2px 8px rgba(100,110,200,0.07);
}
</style>
""", unsafe_allow_html=True)

# ── KPI 목표값 ──────────────────────────────────────────────────────
KPI_TARGETS = {
    "구글":  {"roas": 8,  "cpa": 6000},
    "메타":  {"roas": 6,  "cpa": 8000},
    "네이버":{"roas": 20, "cpa": 3000},
}
CTR_WARN        = 0.5   # % 미만 시 경고
COST_SPIKE_PCT  = 30    # 전일 대비 ±% 급변 임계
AF_DIFF_PCT     = 20    # 채널-AF 클릭 괴리 % 임계
FATIGUE_DAYS    = 14    # 소재 피로도 체크 일수

PASTEL = {"구글": "#A8C8F0", "메타": "#F4A8B8", "네이버": "#A8E0B8"}
DATA_DIR = Path(__file__).parent

# ── 데이터 로드 & 조인 ──────────────────────────────────────────────
@st.cache_data
def load_data(data_dir: str):
    ch_files = sorted(glob.glob(f"{data_dir}/data/channel/*_channel.parquet"))
    af_files = sorted(glob.glob(f"{data_dir}/data/appsflyer/*_appsflyer.parquet"))
    if not ch_files or not af_files:
        return pd.DataFrame()

    ch = pd.concat([pd.read_parquet(f) for f in ch_files], ignore_index=True)
    af = pd.concat([pd.read_parquet(f) for f in af_files], ignore_index=True)

    ch["일"] = pd.to_datetime(ch["일"])
    af["일"] = pd.to_datetime(af["일"])

    df = ch.merge(
        af[["일","캠페인","그룹","소재","클릭","회원가입","구매","구매매출"]],
        on=["일","캠페인","그룹","소재"], how="left", suffixes=("_ch","_af"),
    )
    df["소재유형"] = df["소재"].str.extract(r"^([A-Z]+)_")
    df["ROAS"] = (df["구매매출_ch"] / df["비용"].replace(0, pd.NA)).round(2)
    df["CPA"]  = (df["비용"] / df["구매_ch"].replace(0, pd.NA)).round(0)
    df["CTR"]  = (df["클릭_ch"] / df["노출"].replace(0, pd.NA) * 100).round(2)
    df["CVR"]  = (df["구매_ch"] / df["클릭_ch"].replace(0, pd.NA) * 100).round(2)
    return df

df = load_data(str(DATA_DIR))

if df.empty:
    st.error("데이터 파일을 찾을 수 없어요. data/channel/ · data/appsflyer/ 폴더를 확인해주세요.")
    st.stop()

# ── 헬퍼 함수 ───────────────────────────────────────────────────────
def fmt_krw(v):
    if v >= 1_0000_0000: return f"₩{v/1_0000_0000:.1f}억"
    if v >= 1_0000:      return f"₩{v/1_0000:.0f}만"
    return f"₩{v:,.0f}"

def fmt_num(v):
    if v >= 1_0000_0000: return f"{v/1_0000_0000:.1f}억"
    if v >= 1_0000:      return f"{v/1_0000:.0f}만"
    return f"{v:,}"

def delta_str(cur, prev, invert=False):
    if not prev or prev == 0: return None
    pct = round((cur - prev) / prev * 100, 1)
    up = pct >= 0
    arrow = "▲" if (up != invert) else "▼"
    return f"{arrow} {abs(pct)}%"

# ── 사이드바 ────────────────────────────────────────────────────────
st.sidebar.title("필터")

if st.sidebar.button("🔄 데이터 새로고침", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.divider()

date_min = df["일"].min().date()
date_max = df["일"].max().date()
date_range = st.sidebar.date_input("📅 조회 기간", [date_min, date_max],
                                    min_value=date_min, max_value=date_max)
if len(date_range) < 2:
    date_range = (date_range[0], date_range[0])

channels  = st.sidebar.multiselect("채널",  df["채널"].unique().tolist(),  default=df["채널"].unique().tolist())
campaigns = st.sidebar.multiselect("캠페인", df["캠페인"].unique().tolist(), default=df["캠페인"].unique().tolist())

st.sidebar.divider()
use_compare = st.sidebar.toggle("📊 비교 기간 사용", value=False)
cmp_start = cmp_end = None

if use_compare:
    period_days     = (date_range[1] - date_range[0]).days + 1
    cmp_default_end   = date_range[0] - datetime.timedelta(days=1)
    cmp_default_start = cmp_default_end - datetime.timedelta(days=period_days - 1)

    preset = st.sidebar.radio("비교 기간 프리셋",
                               ["직전 동기간","전주","전월","직접 입력"])
    if preset == "직전 동기간":
        cmp_start, cmp_end = cmp_default_start, cmp_default_end
    elif preset == "전주":
        cmp_end   = date_range[0] - datetime.timedelta(days=1)
        cmp_start = cmp_end - datetime.timedelta(days=6)
    elif preset == "전월":
        first = date_range[0].replace(day=1)
        cmp_end   = first - datetime.timedelta(days=1)
        cmp_start = cmp_end.replace(day=1)
    else:
        cr = st.sidebar.date_input("직접 선택", [cmp_default_start, cmp_default_end])
        cmp_start, cmp_end = (cr[0], cr[1]) if len(cr) == 2 else (cr[0], cr[0])
    st.sidebar.caption(f"비교: {cmp_start} ~ {cmp_end}")

# ── 필터 적용 ───────────────────────────────────────────────────────
def apply_filter(frame, d0, d1):
    return frame[
        (frame["일"].dt.date >= d0) & (frame["일"].dt.date <= d1) &
        (frame["채널"].isin(channels)) & (frame["캠페인"].isin(campaigns))
    ]

fdf = apply_filter(df, date_range[0], date_range[1])
cdf = apply_filter(df, cmp_start, cmp_end) if use_compare and cmp_start else pd.DataFrame()

# ── 제목 & KPI ──────────────────────────────────────────────────────
st.title("📊 광고 성과 대시보드")
cmp_caption = f"  vs  {cmp_start} ~ {cmp_end}" if use_compare and cmp_start else ""
st.caption(f"기간: {date_range[0]} ~ {date_range[1]}{cmp_caption}  |  {len(fdf):,}행")

cur_cost  = fdf["비용"].sum()
cur_imp   = fdf["노출"].sum()
cur_click = fdf["클릭_ch"].sum()
cur_buy   = fdf["구매_ch"].sum()
cur_rev   = fdf["구매매출_ch"].sum()
cur_roas  = (cur_rev / cur_cost) if cur_cost else 0
cur_cpa   = (cur_cost / cur_buy) if cur_buy else 0

p_cost = p_imp = p_click = p_buy = p_roas = p_cpa = None
if not cdf.empty:
    p_cost  = cdf["비용"].sum()
    p_imp   = cdf["노출"].sum()
    p_click = cdf["클릭_ch"].sum()
    p_buy   = cdf["구매_ch"].sum()
    p_rev   = cdf["구매매출_ch"].sum()
    p_roas  = (p_rev / p_cost) if p_cost else 0
    p_cpa   = (p_cost / p_buy) if p_buy else 0

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("총 비용",        fmt_krw(cur_cost),              delta_str(cur_cost,  p_cost,  invert=True))
k2.metric("총 노출",        fmt_num(cur_imp),               delta_str(cur_imp,   p_imp))
k3.metric("총 클릭 (채널)", fmt_num(cur_click),             delta_str(cur_click, p_click))
k4.metric("총 구매",        fmt_num(cur_buy),               delta_str(cur_buy,   p_buy))
k5.metric("ROAS",           f"{cur_roas:.2f}x" if cur_roas else "-", delta_str(cur_roas, p_roas))
k6.metric("CPA",            fmt_krw(cur_cpa) if cur_cpa else "-",    delta_str(cur_cpa,  p_cpa, invert=True))

st.divider()

# ── 탭 ─────────────────────────────────────────────────────────────
t_overview, t_trend, t_material, t_anomaly, t_raw = st.tabs([
    "🏠 Overview", "📅 트렌드", "🎨 소재 분석", "⚡ 이상 감지", "🔍 원본 데이터"
])

# ════════════════════════════════════════════════════════════════════
# 🏠 OVERVIEW
# ════════════════════════════════════════════════════════════════════
with t_overview:
    ch_agg = fdf.groupby("채널").agg(
        비용=("비용","sum"), 노출=("노출","sum"),
        클릭=("클릭_ch","sum"), 구매=("구매_ch","sum"), 매출=("구매매출_ch","sum")
    ).reset_index()
    ch_agg["ROAS"] = (ch_agg["매출"] / ch_agg["비용"].replace(0, pd.NA)).round(2)
    ch_agg["CPA"]  = (ch_agg["비용"] / ch_agg["구매"].replace(0, pd.NA)).round(0)

    # ── 채널별 복합 차트 (비교 ON/OFF 분기) ──
    if use_compare and cmp_start:
        cur_label = f"현재 ({date_range[0]}~{date_range[1]})"
        cmp_label_str = f"비교 ({cmp_start}~{cmp_end})"
        ch_agg["기간"] = cur_label

        if not cdf.empty:
            cmp_ch = cdf.groupby("채널").agg(
                비용=("비용","sum"), 매출=("구매매출_ch","sum"), 구매=("구매_ch","sum")
            ).reset_index()
            cmp_ch["ROAS"] = (cmp_ch["매출"] / cmp_ch["비용"].replace(0, pd.NA)).round(2)
            cmp_ch["기간"] = cmp_label_str
        else:
            st.info(f"비교 기간({cmp_start}~{cmp_end})에 데이터가 없어요.")
            chs = ch_agg["채널"].tolist()
            cmp_ch = pd.DataFrame({"채널": chs, "비용": [0]*len(chs),
                                   "ROAS": [None]*len(chs), "매출": [0]*len(chs),
                                   "구매": [0]*len(chs), "기간": cmp_label_str})

        both = pd.concat([ch_agg[["채널","비용","ROAS","기간"]], cmp_ch[["채널","비용","ROAS","기간"]]])
        cc1, cc2 = st.columns(2)
        with cc1:
            b = alt.Chart(both).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("채널:N", axis=alt.Axis(labelAngle=0, title=None)),
                xOffset="기간:N",
                y=alt.Y("비용:Q", title="비용 (원)", axis=alt.Axis(format=",.0f")),
                color=alt.Color("기간:N",
                    scale=alt.Scale(domain=[cur_label, cmp_label_str], range=["#A8C8F0","#D0C8F0"]),
                    legend=alt.Legend(title=None, orient="top")),
                tooltip=["채널","기간", alt.Tooltip("비용:Q",format=","), alt.Tooltip("ROAS:Q",format=".2f")]
            ).properties(height=320, title="채널별 비용")
            st.altair_chart(b, use_container_width=True)
        with cc2:
            r = alt.Chart(both).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("채널:N", axis=alt.Axis(labelAngle=0, title=None)),
                xOffset="기간:N",
                y=alt.Y("ROAS:Q", title="ROAS"),
                color=alt.Color("기간:N",
                    scale=alt.Scale(domain=[cur_label, cmp_label_str], range=["#A8E0B8","#C8EED8"]),
                    legend=alt.Legend(title=None, orient="top")),
                tooltip=["채널","기간", alt.Tooltip("ROAS:Q",format=".2f")]
            ).properties(height=320, title="채널별 ROAS")
            st.altair_chart(r, use_container_width=True)
    else:
        bar = alt.Chart(ch_agg).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("채널:N", sort="-y", axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("비용:Q", title="비용 (원)", axis=alt.Axis(format=",.0f")),
            color=alt.Color("채널:N",
                scale=alt.Scale(domain=list(PASTEL.keys()), range=list(PASTEL.values())), legend=None),
            tooltip=["채널", alt.Tooltip("비용:Q",format=","),
                     alt.Tooltip("ROAS:Q",format=".2f"), alt.Tooltip("CPA:Q",format=",")]
        )
        line = alt.Chart(ch_agg).mark_line(color="#888", strokeDash=[4,2], strokeWidth=1.5).encode(
            x=alt.X("채널:N", sort="-y"),
            y=alt.Y("ROAS:Q", title="ROAS", axis=alt.Axis(format=".1f")),
        )
        pts = alt.Chart(ch_agg).mark_point(filled=True, size=80, color="#555").encode(
            x=alt.X("채널:N", sort="-y"), y="ROAS:Q",
            tooltip=["채널:N", alt.Tooltip("ROAS:Q",format=".2f")]
        )
        txt = alt.Chart(ch_agg).mark_text(dy=-14, fontSize=12, fontWeight="bold", color="#444").encode(
            x=alt.X("채널:N", sort="-y"), y="ROAS:Q", text=alt.Text("ROAS:Q", format=".1f")
        )
        st.altair_chart(
            alt.layer(bar, line+pts+txt).resolve_scale(y="independent").properties(height=360),
            use_container_width=True
        )

    st.divider()

    # ── ROAS 목표 달성률 ──
    st.subheader("📌 채널별 ROAS 목표 달성률")
    goal_cols = st.columns(len(ch_agg))
    for i, row in ch_agg.iterrows():
        ch_name = row["채널"]
        target  = KPI_TARGETS.get(ch_name, {}).get("roas", 10)
        actual  = row["ROAS"] if pd.notna(row["ROAS"]) else 0
        pct     = min(actual / target, 1.0) if target else 0
        color   = PASTEL.get(ch_name, "#D0C8F0")
        with goal_cols[list(ch_agg["채널"]).index(ch_name)]:
            st.markdown(f"""
            <div style="background:#fff;border-radius:14px;padding:16px;border:1px solid #E0E4F8;text-align:center;">
              <div style="font-size:13px;font-weight:700;color:#2D3172;margin-bottom:8px;">{ch_name}</div>
              <div style="font-size:22px;font-weight:800;color:#2D3172;">{actual:.1f}x</div>
              <div style="font-size:11px;color:#8A8EBA;margin-bottom:8px;">목표 {target}x</div>
              <div style="background:#E8EEFF;border-radius:20px;height:8px;overflow:hidden;">
                <div style="background:{color};width:{pct*100:.0f}%;height:8px;border-radius:20px;"></div>
              </div>
              <div style="font-size:12px;color:#4A4E7A;margin-top:6px;font-weight:600;">{pct*100:.0f}% 달성</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Top 3 소재 ──
    st.subheader("🏆 Top 3 소재 (ROAS 기준)")
    mat_sum = fdf.groupby(["소재","채널","소재유형"]).agg(
        비용=("비용","sum"), 구매=("구매_ch","sum"),
        매출=("구매매출_ch","sum"), 클릭=("클릭_ch","sum"), 노출=("노출","sum")
    ).reset_index()
    mat_sum["ROAS"] = (mat_sum["매출"] / mat_sum["비용"].replace(0, pd.NA)).round(2)
    mat_sum["CTR"]  = (mat_sum["클릭"] / mat_sum["노출"].replace(0, pd.NA) * 100).round(2)
    mat_sum["CPA"]  = (mat_sum["비용"] / mat_sum["구매"].replace(0, pd.NA)).round(0)
    top3 = mat_sum.dropna(subset=["ROAS"]).nlargest(3, "ROAS")

    t3cols = st.columns(3)
    medals = ["🥇","🥈","🥉"]
    for i, (_, row) in enumerate(top3.iterrows()):
        clr = PASTEL.get(row["채널"], "#D0C8F0")
        with t3cols[i]:
            st.markdown(f"""
            <div class="top-material-card">
              <div style="font-size:20px;margin-bottom:4px;">{medals[i]}</div>
              <div style="font-size:12px;font-weight:700;color:#2D3172;margin-bottom:2px;">{row['소재']}</div>
              <div style="display:inline-block;background:{clr};border-radius:20px;
                          padding:2px 10px;font-size:11px;color:#2D3172;font-weight:600;margin-bottom:10px;">
                {row['채널']} · {row['소재유형']}
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:12px;color:#555;">
                <div><span style="color:#8A8EBA;font-size:10px;">ROAS</span><br>
                     <b style="color:#2D3172;font-size:16px;">{row['ROAS']:.1f}x</b></div>
                <div><span style="color:#8A8EBA;font-size:10px;">CPA</span><br>
                     <b style="color:#2D3172;">₩{row['CPA']:,.0f}</b></div>
                <div><span style="color:#8A8EBA;font-size:10px;">CTR</span><br>
                     <b style="color:#2D3172;">{row['CTR']:.2f}%</b></div>
                <div><span style="color:#8A8EBA;font-size:10px;">구매</span><br>
                     <b style="color:#2D3172;">{row['구매']:,.0f}</b></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── 채널별 요약 테이블 ──
    st.subheader("📋 채널별 요약")
    disp = ch_agg.copy()
    disp["ROAS목표"] = disp["채널"].map(lambda x: KPI_TARGETS.get(x,{}).get("roas","—"))
    disp["달성률"] = disp.apply(
        lambda r: f"{r['ROAS']/r['ROAS목표']*100:.0f}%" if isinstance(r["ROAS목표"], (int,float)) and pd.notna(r["ROAS"]) else "—", axis=1
    )
    st.dataframe(
        disp.style.format({"비용":"{:,.0f}","노출":"{:,}","클릭":"{:,}",
                           "구매":"{:,}","매출":"{:,.0f}","ROAS":"{:.2f}","CPA":"{:,.0f}"}),
        use_container_width=True
    )

# ════════════════════════════════════════════════════════════════════
# 📅 트렌드
# ════════════════════════════════════════════════════════════════════
with t_trend:
    daily = fdf.groupby(["일","채널"]).agg(
        비용=("비용","sum"), 노출=("노출","sum"), 클릭=("클릭_ch","sum"),
        구매=("구매_ch","sum"), 회원가입=("회원가입_ch","sum"), 매출=("구매매출_ch","sum")
    ).reset_index()
    daily["ROAS"] = (daily["매출"] / daily["비용"].replace(0, pd.NA)).round(2)
    daily["일_str"] = daily["일"].dt.strftime("%m/%d")

    if daily["일"].nunique() < 2:
        st.info("📅 트렌드 차트는 2일 이상 데이터가 있을 때 의미 있게 보여요. 지금은 1일 데이터로 표시합니다.")

    # ── 일별 비용 추이 ──
    st.subheader("일별 비용 추이 (채널별)")
    cost_chart = alt.Chart(daily).mark_area(opacity=0.7).encode(
        x=alt.X("일:T", title=None, axis=alt.Axis(format="%m/%d")),
        y=alt.Y("비용:Q", stack="zero", title="비용 (원)", axis=alt.Axis(format=",.0f")),
        color=alt.Color("채널:N",
            scale=alt.Scale(domain=list(PASTEL.keys()), range=list(PASTEL.values())),
            legend=alt.Legend(orient="top")),
        tooltip=["채널:N", alt.Tooltip("일:T", format="%Y-%m-%d"),
                 alt.Tooltip("비용:Q", format=",")]
    ).properties(height=260)
    st.altair_chart(cost_chart, use_container_width=True)

    # ── ROAS 꺾은선 ──
    st.subheader("채널별 ROAS 추이")
    roas_line = alt.Chart(daily).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("일:T", title=None, axis=alt.Axis(format="%m/%d")),
        y=alt.Y("ROAS:Q", title="ROAS"),
        color=alt.Color("채널:N",
            scale=alt.Scale(domain=list(PASTEL.keys()), range=list(PASTEL.values())),
            legend=alt.Legend(orient="top")),
        tooltip=["채널:N", alt.Tooltip("일:T", format="%Y-%m-%d"), alt.Tooltip("ROAS:Q", format=".2f")]
    ).properties(height=220)
    st.altair_chart(roas_line, use_container_width=True)

    # ── 구매 · 회원가입 추이 ──
    st.subheader("구매 · 회원가입 추이")
    daily_total = fdf.groupby("일").agg(
        구매=("구매_ch","sum"), 회원가입=("회원가입_ch","sum")
    ).reset_index()
    conv_melt = daily_total.melt("일", var_name="지표", value_name="값")
    conv_chart = alt.Chart(conv_melt).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("일:T", title=None, axis=alt.Axis(format="%m/%d")),
        y=alt.Y("값:Q", title="건수"),
        color=alt.Color("지표:N",
            scale=alt.Scale(domain=["구매","회원가입"], range=["#A8C8F0","#C4A8F0"]),
            legend=alt.Legend(orient="top")),
        tooltip=["지표:N", alt.Tooltip("일:T", format="%Y-%m-%d"), "값:Q"]
    ).properties(height=220)
    st.altair_chart(conv_chart, use_container_width=True)

    # ── 요일별 히트맵 ──
    st.subheader("요일별 ROAS 패턴")
    daily_heat = fdf.copy()
    daily_heat["요일"] = daily_heat["일"].dt.day_name()
    DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    DOW_KR    = {"Monday":"월","Tuesday":"화","Wednesday":"수","Thursday":"목",
                 "Friday":"금","Saturday":"토","Sunday":"일"}
    daily_heat["요일"] = daily_heat["요일"].map(DOW_KR)
    heat_agg = daily_heat.groupby(["채널","요일"]).agg(
        비용=("비용","sum"), 매출=("구매매출_ch","sum")
    ).reset_index()
    heat_agg["ROAS"] = (heat_agg["매출"] / heat_agg["비용"].replace(0,pd.NA)).round(2)
    heat_chart = alt.Chart(heat_agg).mark_rect(cornerRadius=4).encode(
        x=alt.X("요일:O", sort=["월","화","수","목","금","토","일"], title=None),
        y=alt.Y("채널:N", title=None),
        color=alt.Color("ROAS:Q", scale=alt.Scale(scheme="blues"), legend=alt.Legend(title="ROAS")),
        tooltip=["채널:N","요일:O", alt.Tooltip("ROAS:Q", format=".2f")]
    ).properties(height=160)
    st.altair_chart(heat_chart, use_container_width=True)

# ════════════════════════════════════════════════════════════════════
# 🎨 소재 분석
# ════════════════════════════════════════════════════════════════════
with t_material:

    mat_agg = fdf.groupby(["소재유형","소재","채널"]).agg(
        비용=("비용","sum"), 노출=("노출","sum"),
        클릭=("클릭_ch","sum"), 구매=("구매_ch","sum"), 매출=("구매매출_ch","sum")
    ).reset_index()
    mat_agg["ROAS"] = (mat_agg["매출"] / mat_agg["비용"].replace(0,pd.NA)).round(2)
    mat_agg["CTR"]  = (mat_agg["클릭"] / mat_agg["노출"].replace(0,pd.NA) * 100).round(2)
    mat_agg["CPA"]  = (mat_agg["비용"] / mat_agg["구매"].replace(0,pd.NA)).round(0)

    # ── 소재 유형별 ROAS / CTR ──
    st.subheader("소재 유형별 성과")
    type_agg = fdf.groupby("소재유형").agg(
        비용=("비용","sum"), 매출=("구매매출_ch","sum"),
        노출=("노출","sum"), 클릭=("클릭_ch","sum")
    ).reset_index()
    type_agg["ROAS"] = (type_agg["매출"] / type_agg["비용"].replace(0,pd.NA)).round(2)
    type_agg["CTR"]  = (type_agg["클릭"] / type_agg["노출"].replace(0,pd.NA) * 100).round(2)

    mc1, mc2 = st.columns(2)
    TYPE_COLORS = {"VID":"#A8C8F0","IMG":"#F4A8B8","CRS":"#A8E0B8","TXT":"#C4A8F0"}
    with mc1:
        st.markdown("**ROAS**")
        c = alt.Chart(type_agg).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("소재유형:N", sort="-y", axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("ROAS:Q"),
            color=alt.Color("소재유형:N",
                scale=alt.Scale(domain=list(TYPE_COLORS.keys()), range=list(TYPE_COLORS.values())), legend=None),
            tooltip=["소재유형", alt.Tooltip("ROAS:Q",format=".2f"), alt.Tooltip("비용:Q",format=",")]
        ).properties(height=260)
        st.altair_chart(c, use_container_width=True)
    with mc2:
        st.markdown("**CTR (%)**")
        c2 = alt.Chart(type_agg).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("소재유형:N", sort="-y", axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("CTR:Q", title="CTR (%)"),
            color=alt.Color("소재유형:N",
                scale=alt.Scale(domain=list(TYPE_COLORS.keys()), range=list(TYPE_COLORS.values())), legend=None),
            tooltip=["소재유형", alt.Tooltip("CTR:Q",format=".2f")]
        ).properties(height=260)
        st.altair_chart(c2, use_container_width=True)

    st.divider()

    # ── AB 테스트 비교 ──
    st.subheader("🔬 AB 테스트 비교")
    ab_df = fdf.copy()
    ab_df["AB버전"] = ab_df["소재"].str.extract(r"_(A|B)_v\d+$")
    ab_only = ab_df.dropna(subset=["AB버전"])
    if ab_only.empty:
        st.caption("AB 버전 소재가 없거나 필터 범위에 없어요.")
    else:
        ab_agg = ab_only.groupby(["캠페인","소재유형","AB버전"]).agg(
            비용=("비용","sum"), 구매=("구매_ch","sum"),
            매출=("구매매출_ch","sum"), 클릭=("클릭_ch","sum"), 노출=("노출","sum")
        ).reset_index()
        ab_agg["ROAS"] = (ab_agg["매출"] / ab_agg["비용"].replace(0,pd.NA)).round(2)
        ab_agg["CTR"]  = (ab_agg["클릭"] / ab_agg["노출"].replace(0,pd.NA) * 100).round(2)
        ab_agg["CPA"]  = (ab_agg["비용"] / ab_agg["구매"].replace(0,pd.NA)).round(0)

        ab_chart = alt.Chart(ab_agg).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X("캠페인:N", axis=alt.Axis(labelAngle=-20, title=None)),
            xOffset="AB버전:N",
            y=alt.Y("ROAS:Q", title="ROAS"),
            color=alt.Color("AB버전:N",
                scale=alt.Scale(domain=["A","B"], range=["#A8C8F0","#F4A8B8"]),
                legend=alt.Legend(title="버전", orient="top")),
            tooltip=["캠페인","소재유형","AB버전",
                     alt.Tooltip("ROAS:Q",format=".2f"),
                     alt.Tooltip("CTR:Q",format=".2f"),
                     alt.Tooltip("CPA:Q",format=","),
                     alt.Tooltip("비용:Q",format=",")]
        ).properties(height=300)
        st.altair_chart(ab_chart, use_container_width=True)
        st.dataframe(ab_agg.sort_values(["캠페인","AB버전"]).style.format(
            {"비용":"{:,.0f}","매출":"{:,.0f}","ROAS":"{:.2f}","CTR":"{:.2f}%","CPA":"{:,.0f}"}
        ), use_container_width=True)

    st.divider()

    # ── 소재 피로도 ──
    st.subheader(f"⏳ 소재 피로도 ({FATIGUE_DAYS}일+ 운영 소재)")
    op_days = fdf.groupby("소재")["일"].nunique().reset_index(name="운영일수")
    fatigue = op_days[op_days["운영일수"] >= FATIGUE_DAYS].merge(
        mat_agg[["소재","ROAS","CTR","비용"]], on="소재", how="left"
    )
    if fatigue.empty:
        st.success(f"✅ {FATIGUE_DAYS}일 이상 운영된 소재가 없어요.")
    else:
        st.dataframe(fatigue.style.format(
            {"ROAS":"{:.2f}","CTR":"{:.2f}%","비용":"{:,.0f}"}
        ), use_container_width=True)

    st.divider()

    # ── 캠페인 목적별 소재 성과 ──
    st.subheader("🎯 캠페인 목적별 소재 성과")
    purposes = fdf["캠페인목적"].dropna().unique().tolist()
    purpose_tabs = st.tabs(purposes)
    for ptab, purpose in zip(purpose_tabs, purposes):
        with ptab:
            purpose_소재 = fdf[fdf["캠페인목적"]==purpose]["소재"].unique()
            sub = mat_agg[mat_agg["소재"].isin(purpose_소재)]
            if sub.empty:
                st.caption("해당 목적의 소재가 없어요.")
                continue
            st.dataframe(
                sub.sort_values("ROAS", ascending=False).style.format(
                    {"비용":"{:,.0f}","매출":"{:,.0f}","ROAS":"{:.2f}","CTR":"{:.2f}%","CPA":"{:,.0f}"}
                ), use_container_width=True
            )

    st.divider()

    # ── 전체 소재 테이블 ──
    st.subheader("📋 전체 소재 성과")
    st.dataframe(
        mat_agg.sort_values("ROAS", ascending=False).style.format(
            {"비용":"{:,.0f}","노출":"{:,}","클릭":"{:,}",
             "구매":"{:,}","매출":"{:,.0f}","ROAS":"{:.2f}","CTR":"{:.2f}%","CPA":"{:,.0f}"}
        ), use_container_width=True
    )

# ════════════════════════════════════════════════════════════════════
# ⚡ 이상 감지
# ════════════════════════════════════════════════════════════════════
with t_anomaly:
    st.subheader("⚡ 이상 감지")
    st.caption(f"기준: ROAS 목표 미달 | 비용 급변 ±{COST_SPIKE_PCT}% | CTR {CTR_WARN}% 미만 | 채널-AF 클릭 괴리 {AF_DIFF_PCT}%+")

    alerts = []

    # 1. ROAS 목표 미달
    camp_roas = fdf.groupby(["채널","캠페인"]).agg(
        비용=("비용","sum"), 매출=("구매매출_ch","sum"), 구매=("구매_ch","sum")
    ).reset_index()
    camp_roas["ROAS"] = (camp_roas["매출"] / camp_roas["비용"].replace(0,pd.NA)).round(2)
    for _, row in camp_roas.iterrows():
        target = KPI_TARGETS.get(row["채널"],{}).get("roas", None)
        if target and pd.notna(row["ROAS"]) and row["ROAS"] < target:
            gap = target - row["ROAS"]
            alerts.append({
                "등급": "🔴 위험",
                "유형": "ROAS 목표 미달",
                "대상": f"{row['채널']} · {row['캠페인']}",
                "내용": f"ROAS {row['ROAS']:.2f}x (목표 {target}x, -{gap:.1f}x 부족)",
                "css": "alert-danger"
            })

    # 2. 비용 급변 (전일 대비 — 데이터 2일 이상일 때)
    daily_cost = fdf.groupby(["일","채널"])["비용"].sum().reset_index()
    for ch in daily_cost["채널"].unique():
        sub = daily_cost[daily_cost["채널"]==ch].sort_values("일")
        if len(sub) >= 2:
            for i in range(1, len(sub)):
                prev_c = sub.iloc[i-1]["비용"]
                cur_c  = sub.iloc[i]["비용"]
                if prev_c > 0:
                    chg = (cur_c - prev_c) / prev_c * 100
                    if abs(chg) >= COST_SPIKE_PCT:
                        dt = sub.iloc[i]["일"].strftime("%m/%d")
                        alerts.append({
                            "등급": "🟡 주의",
                            "유형": "비용 급변",
                            "대상": f"{ch} ({dt})",
                            "내용": f"전일 대비 {chg:+.1f}% 변동 (₩{prev_c:,.0f} → ₩{cur_c:,.0f})",
                            "css": "alert-warn"
                        })

    # 3. CTR 경고
    mat_ctr = fdf.groupby(["채널","캠페인","소재"]).agg(
        노출=("노출","sum"), 클릭=("클릭_ch","sum"), 비용=("비용","sum")
    ).reset_index()
    mat_ctr["CTR"] = (mat_ctr["클릭"] / mat_ctr["노출"].replace(0,pd.NA) * 100).round(2)
    low_ctr = mat_ctr[(mat_ctr["CTR"] < CTR_WARN) & (mat_ctr["비용"] > 0)]
    for _, row in low_ctr.iterrows():
        alerts.append({
            "등급": "🟡 주의",
            "유형": "CTR 경고",
            "대상": f"{row['채널']} · {row['소재']}",
            "내용": f"CTR {row['CTR']:.3f}% (경고선 {CTR_WARN}% 미만) | 비용 ₩{row['비용']:,.0f}",
            "css": "alert-warn"
        })

    # 4. 채널-AF 클릭 괴리
    ch_af = fdf.groupby("채널").agg(
        클릭_ch=("클릭_ch","sum"), 클릭_af=("클릭_af","sum")
    ).reset_index()
    for _, row in ch_af.iterrows():
        if row["클릭_ch"] > 0:
            diff_pct = abs(row["클릭_ch"] - row["클릭_af"]) / row["클릭_ch"] * 100
            if diff_pct >= AF_DIFF_PCT:
                alerts.append({
                    "등급": "🟡 주의",
                    "유형": "채널-AF 괴리",
                    "대상": f"{row['채널']}",
                    "내용": f"채널 클릭 {row['클릭_ch']:,} vs AF {row['클릭_af']:,} (괴리 {diff_pct:.1f}%)",
                    "css": "alert-warn"
                })

    if not alerts:
        st.markdown("""
        <div class="alert-card alert-ok">
          🟢 <b>오늘은 이상 없어요!</b> 모든 캠페인이 목표 범위 안에서 운영 중이에요.
        </div>
        """, unsafe_allow_html=True)
    else:
        # 등급 순 정렬 (위험 먼저)
        order = {"🔴 위험": 0, "🟡 주의": 1, "🟢 정상": 2}
        alerts.sort(key=lambda x: order.get(x["등급"], 9))
        danger_cnt = sum(1 for a in alerts if a["등급"] == "🔴 위험")
        warn_cnt   = sum(1 for a in alerts if a["등급"] == "🟡 주의")
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("🔴 위험", danger_cnt)
        sc2.metric("🟡 주의", warn_cnt)
        sc3.metric("🟢 정상", "확인 필요")
        st.markdown("---")
        for a in alerts:
            st.markdown(f"""
            <div class="alert-card {a['css']}">
              <b>{a['등급']} [{a['유형']}]</b> — {a['대상']}<br>
              <span style="color:#555;">{a['내용']}</span>
            </div>
            """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════
# 🔍 원본 데이터
# ════════════════════════════════════════════════════════════════════
with t_raw:
    raw_tab1, raw_tab2, raw_tab3 = st.tabs(["조인 데이터", "채널 원본", "AF 원본"])

    with raw_tab1:
        st.dataframe(fdf, use_container_width=True)
        csv = fdf.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV 다운로드 (조인)", csv, "merged_data.csv", "text/csv")

    with raw_tab2:
        ch_raw_files = sorted(glob.glob(str(DATA_DIR / "data/channel/*_channel.parquet")))
        if ch_raw_files:
            ch_raw = pd.concat([pd.read_parquet(f) for f in ch_raw_files], ignore_index=True)
            ch_raw["일"] = pd.to_datetime(ch_raw["일"])
            ch_raw_f = ch_raw[
                (ch_raw["일"].dt.date >= date_range[0]) &
                (ch_raw["일"].dt.date <= date_range[1]) &
                (ch_raw["채널"].isin(channels))
            ]
            st.dataframe(ch_raw_f, use_container_width=True)
            st.download_button("⬇️ CSV 다운로드 (채널)",
                ch_raw_f.to_csv(index=False).encode("utf-8-sig"), "channel_raw.csv", "text/csv")

    with raw_tab3:
        af_raw_files = sorted(glob.glob(str(DATA_DIR / "data/appsflyer/*_appsflyer.parquet")))
        if af_raw_files:
            af_raw = pd.concat([pd.read_parquet(f) for f in af_raw_files], ignore_index=True)
            af_raw["일"] = pd.to_datetime(af_raw["일"])
            af_raw_f = af_raw[
                (af_raw["일"].dt.date >= date_range[0]) &
                (af_raw["일"].dt.date <= date_range[1])
            ]
            st.dataframe(af_raw_f, use_container_width=True)
            st.download_button("⬇️ CSV 다운로드 (AF)",
                af_raw_f.to_csv(index=False).encode("utf-8-sig"), "appsflyer_raw.csv", "text/csv")
