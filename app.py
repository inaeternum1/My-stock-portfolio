import streamlit as st
import pandas as pd
import yfinance as yf
import altair as alt  # 🚨 차트 디자인을 완벽하게 제어하기 위해 추가!

# 페이지 설정
st.set_page_config(page_title="내 주식 현황", page_icon="💰", layout="wide")

# --- 🎨 화면 디자인 수정: 메트릭(숫자) 글자 크기 줄이기 ---
st.markdown("""
<style>
/* 숫자 크기 조절 */
[data-testid="stMetricValue"] {
    font-size: 24px !important;
}
/* 제목 글자 크기 조절 */
[data-testid="stMetricLabel"] {
    font-size: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# --- 🔄 타이틀과 새로고침 버튼을 같은 줄에 배치 ---
col_title, col_btn = st.columns([4, 1])
with col_title:
    st.title("📊 내 주식 포트폴리오")
with col_btn:
    st.write("") 
    st.write("")
    if st.button("🔄 시세 새로고침", use_container_width=True):
        st.cache_data.clear() 
        st.rerun() 

st.markdown("친구야, 내 피땀눈물이 담긴 계좌다. (실시간 시세 & 환율 자동 반영 중 💸)")

# 1. 고정 데이터 (삼성전자, 앱셀레라)
portfolio = [
    {"종목명": "삼성전자", "티커": "005930.KS", "평단가": 160500, "주식수": 177, "통화": "KRW"},
    {"종목명": "앱셀레라", "티커": "ABCL", "평단가": 3.40, "주식수": 3000, "통화": "USD"}
]
df = pd.DataFrame(portfolio)

# 실시간 환율 가져오기
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        return yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
    except:
        return 1380.0

rate = get_exchange_rate()

# 2. 실시간 데이터 & 과거 3개월 데이터(그래프용) 가져오기
@st.cache_data(ttl=60)
def fetch_market_data(tickers):
    data_dict = {}
    history_dict = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo")
            if not hist.empty:
                data_dict[ticker] = hist['Close'].iloc[-1] 
                history_dict[ticker] = hist['Close'] 
            else:
                data_dict[ticker] = 0
                history_dict[ticker] = pd.Series(dtype=float)
        except:
            data_dict[ticker] = 0
            history_dict[ticker] = pd.Series(dtype=float)
    return data_dict, history_dict

with st.spinner('최신 시세와 차트 그리는 중... 🚀'):
    current_prices, historical_prices = fetch_market_data(df['티커'].tolist())

df['현재가'] = df['티커'].map(current_prices)

# 3. 현재 계좌 가치 계산 (환율 적용)
def calc_current(row):
    ex_rate = rate if row['통화'] == 'USD' else 1
    
    buy_total = row['평단가'] * row['주식수'] * ex_rate
    cur_total = row['현재가'] * row['주식수'] * ex_rate
    profit = cur_total - buy_total
    profit_rate = (profit / buy_total * 100) if buy_total > 0 else 0
    
    return pd.Series([buy_total, cur_total, profit, profit_rate])

df[['매수금액(원)', '평가금액(원)', '수익금(원)', '수익률(%)']] = df.apply(calc_current, axis=1)

total_buy = df['매수금액(원)'].sum()
total_eval = df['평가금액(원)'].sum()
total_profit = total_eval - total_buy
total_rate = (total_profit / total_buy * 100) if total_buy > 0 else 0

# 4. 상단 요약 대시보드 (빨강/파랑 색상 적용)
st.subheader("💰 전체 계좌 요약")

t_color = "#ff4b4b" if total_profit > 0 else "#1e88e5" if total_profit < 0 else "black"
t_sign = "+" if total_profit > 0 else ""

col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"<div style='font-size:14px; color:gray;'>총 매수금액</div><div style='font-size:22px; font-weight:bold;'>{total_buy:,.0f}원</div>", unsafe_allow_html=True)
col2.markdown(f"<div style='font-size:14px; color:gray;'>총 평가금액</div><div style='font-size:22px; font-weight:bold;'>{total_eval:,.0f}원</div>", unsafe_allow_html=True)
col3.markdown(f"<div style='font-size:14px; color:gray;'>총 수익금</div><div style='font-size:22px; font-weight:bold; color:{t_color};'>{t_sign}{total_profit:,.0f}원</div>", unsafe_allow_html=True)
col4.markdown(f"<div style='font-size:14px; color:gray;'>총 수익률</div><div style='font-size:22px; font-weight:bold; color:{t_color};'>{t_sign}{total_rate:.2f}%</div>", unsafe_allow_html=True)

st.divider()

# 5. 수익률 꺾은선 그래프 (3개월) - Altair로 업그레이드!
st.subheader("📈 최근 3개월 내 계좌 총 수익률 흐름")

chart_df = pd.DataFrame()

for idx, row in df.iterrows():
    ticker = row['티커']
    qty = row['주식수']
    ex_rate = rate if row['통화'] == 'USD' else 1
    
    if ticker in historical_prices and not historical_prices[ticker].empty:
        daily_value = historical_prices[ticker] * qty * ex_rate
        daily_value.index = daily_value.index.tz_localize(None)
        chart_df[ticker] = daily_value

if not chart_df.empty:
    chart_df.ffill(inplace=True)
    chart_df.bfill(inplace=True)
    
    chart_df['총평가금액'] = chart_df.sum(axis=1)
    chart_df['총수익률(%)'] = ((chart_df['총평가금액'] - total_buy) / total_buy) * 100
    
    # Altair 차트를 그리기 위해 인덱스(날짜)를 일반 컬럼으로 꺼냄
    plot_df = chart_df.reset_index()
    plot_df.rename(columns={'index': 'Date'}, inplace=True)
    
    chart_color = "#ff4b4b" if chart_df['총수익률(%)'].iloc[-1] >= 0 else "#1e88e5"
    
    # 🚨 Altair를 이용한 섬세한 차트 설정 (가로 글자 강제 고정, 월/일 포맷)
    line_chart = alt.Chart(plot_df).mark_line(color=chart_color, strokeWidth=2).encode(
        x=alt.X('Date:T', 
                axis=alt.Axis(
                    title='', 
                    format='%m월 %d일', # 년도를 빼고 월/일만 표시
                    labelAngle=0,      # 글자를 세로로 꺾지 말고 무조건 가로(0도)로 유지
                    tickCount=6        # 가로로 유지되도록 눈금 개수 조절
                )),
        y=alt.Y('총수익률(%):Q', axis=alt.Axis(title='수익률 (%)')),
        tooltip=[
            alt.Tooltip('Date:T', format='%Y년 %m월 %d일', title='날짜'),
            alt.Tooltip('총수익률(%):Q', format='+.2f', title='총 수익률(%)')
        ]
    ).interactive() # 마우스 드래그 확대/축소 기능 추가

    st.altair_chart(line_chart, use_container_width=True)
else:
    st.info("차트를 그릴 데이터가 부족합니다.")

st.divider()

# 6. 상세 종목 내역
st.subheader("📝 보유 종목 상세 내역")
def color_val(val):
    return f"color: {'#ff4b4b' if val > 0 else '#1e88e5' if val < 0 else 'black'}"

display_df = df[['종목명', '티커', '평단가', '현재가', '주식수', '매수금액(원)', '평가금액(원)', '수익금(원)', '수익률(%)']].copy()

st.dataframe(display_df.style.format({
    '평단가': '{:,.2f}', 
    '현재가': '{:,.2f}', 
    '주식수': '{:,.0f}',
    '매수금액(원)': '{:,.0f}원',
    '평가금액(원)': '{:,.0f}원',
    '수익금(원)': '{:,.0f}원',
    '수익률(%)': '{:+.2f}%'
}).map(color_val, subset=['수익률(%)', '수익금(원)']), use_container_width=True)

st.caption(f"적용된 실시간 환율: 1 USD = {rate:,.2f} KRW | 데이터 제공: Yahoo Finance")
