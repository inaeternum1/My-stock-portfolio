import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="실시간 주식 관리자", page_icon="💰", layout="wide")

st.title("📊 주식 포트폴리오 대시보드")
st.markdown("친구가 공유받을 내 주식 현황입니다.")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

@st.cache_data(ttl=60)
def get_stock_info(ticker):
    ticker = str(ticker).strip().upper()
    
    # 6자리 숫자로만 입력했다면 자동으로 .KS(코스피) 붙여주기
    if ticker.isdigit() and len(ticker) == 6:
        ticker += ".KS"
        
    try:
        # 에러 메시지 해결! 억지로 세션을 만들지 않고 yfinance 자체 기능에 온전히 맡김
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        
        if hist.empty:
            return {"price": 0.0, "change": 0.0, "error": "데이터 없음(종목코드 오류 또는 상장폐지)"}
            
        current_price = hist['Close'].iloc[-1]
        
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            daily_change = ((current_price - prev_close) / prev_close) * 100
        else:
            daily_change = 0.0
            
        return {"price": current_price, "change": daily_change, "error": None}
        
    except Exception as e:
        return {"price": 0.0, "change": 0.0, "error": f"통신 에러: {str(e)}"}

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        return yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
    except:
        return 1380.0

rate = get_exchange_rate()

# --- 1. 입력 섹션 ---
with st.expander("➕ 새 종목 추가하기", expanded=True):
    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
        with c1: name = st.text_input("종목명", placeholder="예: 삼성전자")
        with c2: ticker_input = st.text_input("티커/종목번호", placeholder="005930 또는 ABCL")
        with c3: avg_price = st.number_input("내 평단가", min_value=0.0, step=1.0)
        with c4: count = st.number_input("주식 수", min_value=0.0, step=1.0)
        with c5: currency = st.selectbox("통화", ["KRW", "USD"])
        
        if st.form_submit_button("추가하기") and ticker_input:
            st.session_state.portfolio.append({
                "종목명": name if name else ticker_input,
                "티커": ticker_input,
                "평단가": avg_price,
                "주식수": count,
                "통화": currency
            })
            st.rerun()

# --- 2. 데이터 처리 ---
if st.session_state.portfolio:
    df = pd.DataFrame(st.session_state.portfolio)
    
    with st.spinner('실시간 시장 데이터 긁어오는 중...'):
        current_data = [get_stock_info(t) for t in df['티커']]
        
    for i, data in enumerate(current_data):
        if data['error']:
            st.error(f"⚠️ '{df['종목명'].iloc[i]}' 데이터 수신 실패! 사유: {data['error']}")
            
    df['현재가'] = [d['price'] for d in current_data]
    df['오늘등락률'] = [d['change'] for d in current_data]

    def calculate_values(row):
        is_usd = row['통화'] == 'USD'
        ex_rate = rate if is_usd else 1
        
        buy_total = row['평단가'] * row['주식수'] * ex_rate
        cur_total = row['현재가'] * row['주식수'] * ex_rate
        profit = cur_total - buy_total
        profit_rate = (profit / buy_total * 100) if buy_total > 0 else 0
        
        return pd.Series([buy_total, cur_total, profit, profit_rate])

    df[['매수금액', '평가금액', '수익금', '수익률']] = df.apply(calculate_values, axis=1)

    # --- 3. 대시보드 ---
    total_buy = df['매수금액'].sum()
    total_eval = df['평가금액'].sum()
    total_profit = total_eval - total_buy
    total_rate = (total_profit / total_buy * 100) if total_buy > 0 else 0

    st.subheader("💰 전체 계좌 요약")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("총 매수금액", f"{total_buy:,.0f}원")
    m2.metric("총 평가금액", f"{total_eval:,.0f}원")
    m3.metric("총 수익금", f"{total_profit:,.0f}원")
    m4.metric("총 수익률", f"{total_rate:.2f}%")

    st.divider()

    def color_val(val):
        return f"color: {'red' if val > 0 else 'blue' if val < 0 else 'black'}"

    st.subheader("📝 보유 종목 상세 내역")
    
    display_df = df[['종목명', '티커', '평단가', '현재가', '주식수', '오늘등락률', '수익률', '수익금']].copy()
    
    st.dataframe(display_df.style.format({
        '평단가': '{:,.2f}', '현재가': '{:,.2f}', '주식수': '{:,.0f}',
        '오늘등락률': '{:+.2f}%', '수익률': '{:+.2f}%', '수익금': '{:,.0f}원'
    }).map(color_val, subset=['오늘등락률', '수익률']), use_container_width=True)

    if st.button("🗑️ 리스트 완벽 초기화"):
        st.session_state.portfolio = []
        st.cache_data.clear()
        st.rerun()
else:
    st.info("좌측 상단의 '새 종목 추가하기'를 눌러 종목을 입력해 주세요.")