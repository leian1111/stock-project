import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# 페이지 기본 설정
st.set_page_config(page_title="실시간 주가 대시보드", layout="wide")
st.title("📈 실시간 주가 대시보드")

# 버튼으로 고를 종목 목록: (표시 이름, 입력값)
PRESETS = [
    ("삼성전자", "005930"),
    ("SK하이닉스", "000660"),
    ("애플", "AAPL"),
    ("테슬라", "TSLA"),
    ("엔비디아", "NVDA"),
    ("마이크로소프트", "MSFT"),
]


def normalize_ticker(raw: str) -> str:
    """입력값을 yfinance가 인식하는 티커로 변환한다.
    - 숫자로만 이루어진 경우(예: 005930) → 한국 주식으로 보고 '.KS'를 붙인다.
    - 그 외(예: AAPL, TSLA) → 미국 주식으로 보고 대문자로 그대로 사용한다.
    """
    raw = raw.strip().upper()
    if raw.isdigit():
        return f"{raw}.KS"
    return raw


def format_price(ticker: str, price: float) -> str:
    """한국 주식은 원 단위 정수로, 그 외는 달러 소수점 둘째 자리로 표시한다."""
    if ticker.endswith((".KS", ".KQ")):
        return f"{price:,.0f} 원"
    return f"${price:,.2f}"


@st.fragment(run_every=5)
def draw_price(ticker: str):
    """현재가와 전일 대비 등락률을 5초마다 가볍게 갱신한다.
    fast_info를 사용해 서버 부하를 최소화하고, 실패해도 화면이 터지지 않게 한다.
    """
    try:
        info = yf.Ticker(ticker).fast_info
        last = info["last_price"]
        prev = info["previous_close"]
    except Exception:
        st.metric(label=f"{ticker} 현재가", value="—", delta="데이터 없음")
        return

    # 값이 없거나 0이면 계산하지 않는다 (0 나눗셈 방지)
    if last is None or prev is None or prev == 0:
        st.metric(label=f"{ticker} 현재가", value="—", delta="데이터 없음")
        return

    change_pct = (last - prev) / prev * 100
    st.metric(
        label=f"{ticker} 현재가",
        value=format_price(ticker, last),
        delta=f"{change_pct:+.2f}%",
    )


@st.fragment(run_every=60)
def draw_chart(ticker: str):
    """1분 단위 종가 차트를 60초마다 부분 새로고침한다."""
    # 최근 1일치 데이터를 1분 단위로 수집
    data = yf.download(ticker, period="1d", interval="1m", progress=False, auto_adjust=True)

    # 최신 yfinance는 단일 종목도 멀티인덱스 컬럼으로 반환할 수 있어 평탄화한다.
    if data.columns.nlevels > 1:
        data.columns = data.columns.get_level_values(0)

    # 데이터 예외 처리: 잘못된 티커이거나 주말 등으로 데이터가 없는 경우
    if data.empty or "Close" not in data.columns:
        st.error("데이터를 불러올 수 없습니다. 티커를 확인하세요.")
        return

    close = data["Close"].dropna()
    if close.empty:
        st.error("데이터를 불러올 수 없습니다. 티커를 확인하세요.")
        return

    # 종가(Close)를 Plotly 선 그래프로 시각화
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=close.index,
        y=close,
        mode="lines",
        name="종가",
    ))
    fig.update_layout(
        title=f"{ticker} 1분 단위 종가 (최근 1일)",
        xaxis_title="시간",
        yaxis_title="가격",
    )
    st.plotly_chart(fig, use_container_width=True)


# 처음 실행 시 기본 종목 설정
if "ticker" not in st.session_state:
    st.session_state["ticker"] = normalize_ticker("AAPL")

# 종목 선택 버튼: 누르면 해당 종목으로 전환된다
st.write("종목을 선택하세요")
cols = st.columns(len(PRESETS))
for col, (name, code) in zip(cols, PRESETS):
    if col.button(name, use_container_width=True):
        st.session_state["ticker"] = normalize_ticker(code)

ticker = st.session_state["ticker"]

# 현재가 위젯(5초 갱신) → 차트(60초 갱신) 순서로 표시
draw_price(ticker)
draw_chart(ticker)

# 하단 중앙 정렬 푸터
st.markdown(
    "<p style='text-align:center; color:gray;'>PRODUCED BY 2712 · AI ASSISTED WEB PROJECT</p>",
    unsafe_allow_html=True,
)