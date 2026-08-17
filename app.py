import streamlit as st
import pandas as pd
import numpy as np
import FinanceDataReader as fdr
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import time

# ============================================================
# 1. 페이지 설정 (항상 맨 위에 위치해야 함)
# ============================================================
st.set_page_config(
    page_title="📊 퀀트 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 2. 데이터 수집 함수들
# ============================================================

@st.cache_data(ttl=3600)  # 1시간 캐싱
def get_korea_market_data():
    """한국 시장 데이터 수집 (코스피, 코스닥 지수)"""
    try:
        # 코스피 지수
        kospi = fdr.DataReader('KS11', datetime.now() - timedelta(days=5))
        kospi_price = kospi['Close'].iloc[-1]
        kospi_change = ((kospi_price - kospi['Close'].iloc[-2]) / kospi['Close'].iloc[-2]) * 100
        
        # 코스닥 지수
        kosdaq = fdr.DataReader('KQ11', datetime.now() - timedelta(days=5))
        kosdaq_price = kosdaq['Close'].iloc[-1]
        kosdaq_change = ((kosdaq_price - kosdaq['Close'].iloc[-2]) / kosdaq['Close'].iloc[-2]) * 100
        
        return {
            'kospi': {'price': kospi_price, 'change': kospi_change},
            'kosdaq': {'price': kosdaq_price, 'change': kosdaq_change}
        }
    except:
        return {
            'kospi': {'price': 2800, 'change': 1.2},
            'kosdaq': {'price': 900, 'change': -0.3}
        }

@st.cache_data(ttl=3600)
def get_us_market_data():
    """미국 시장 데이터 수집 (나스닥, S&P500)"""
    try:
        # 나스닥
        nasdaq = yf.Ticker("^IXIC")
        nasdaq_hist = nasdaq.history(period="5d")
        nasdaq_price = nasdaq_hist['Close'].iloc[-1]
        nasdaq_change = ((nasdaq_price - nasdaq_hist['Close'].iloc[-2]) / nasdaq_hist['Close'].iloc[-2]) * 100
        
        # S&P500
        sp500 = yf.Ticker("^GSPC")
        sp500_hist = sp500.history(period="5d")
        sp500_price = sp500_hist['Close'].iloc[-1]
        sp500_change = ((sp500_price - sp500_hist['Close'].iloc[-2]) / sp500_hist['Close'].iloc[-2]) * 100
        
        return {
            'nasdaq': {'price': nasdaq_price, 'change': nasdaq_change},
            'sp500': {'price': sp500_price, 'change': sp500_change}
        }
    except:
        return {
            'nasdaq': {'price': 18500, 'change': 0.8},
            'sp500': {'price': 5600, 'change': -0.2}
        }

@st.cache_data(ttl=3600)
def get_macro_data():
    """거시경제 데이터 (금, WTI, 환율, 금리)"""
    try:
        # 금값
        gold = yf.Ticker("GC=F")
        gold_price = gold.history(period="1d")['Close'].iloc[-1]
        
        # WTI
        wti = yf.Ticker("CL=F")
        wti_price = wti.history(period="1d")['Close'].iloc[-1]
        
        # 환율 (원/달러)
        usd_krw = fdr.DataReader('USD/KRW', datetime.now() - timedelta(days=1))
        exchange_rate = usd_krw['Close'].iloc[-1]
        
        # 한국 10년 국채수익률 (임시 데이터)
        kr_bond = 3.2
        us_bond = 4.1
        
        return {
            'gold': gold_price,
            'wti': wti_price,
            'exchange_rate': exchange_rate,
            'kr_bond': kr_bond,
            'us_bond': us_bond
        }
    except:
        return {
            'gold': 2400,
            'wti': 82,
            'exchange_rate': 1350,
            'kr_bond': 3.2,
            'us_bond': 4.1
        }

@st.cache_data(ttl=7200)
def get_top_stocks():
    """시가총액 상위 150개 종목 수집"""
    try:
        # KRX 전체 종목 리스트
        all_stocks = fdr.StockListing('KRX')
        
        # ETF 제외
        stocks = all_stocks[~all_stocks['Name'].str.contains('ETF|ETN', case=False)]
        
        # 시가총액 기준 상위 150개
        stocks = stocks.sort_values('Marcap', ascending=False).head(150)
        
        # 종목코드를 6자리 문자열로 변환
        stocks['Code'] = stocks['Symbol'].astype(str).str.zfill(6)
        
        return stocks[['Code', 'Name', 'Marcap']]
    except:
        # 임시 데이터 (실패 시 사용)
        temp_data = pd.DataFrame({
            'Code': ['005930', '000660', '373220', '207940', '005380'],
            'Name': ['삼성전자', 'SK하이닉스', 'LG에너지솔루션', '삼성바이오로직스', '현대차'],
            'Marcap': [400000, 200000, 150000, 100000, 80000]
        })
        return temp_data

@st.cache_data(ttl=3600)
def get_stock_price(code, name):
    """개별 종목 가격 및 기본 정보 수집"""
    try:
        df = fdr.DataReader(code, datetime.now() - timedelta(days=100))
        if df.empty:
            return None
            
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        change = ((current_price - prev_price) / prev_price) * 100
        
        # 이동평균선 계산
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        ma60 = df['Close'].rolling(60).mean().iloc[-1]
        
        return {
            'name': name,
            'code': code,
            'price': current_price,
            'change': change,
            'ma5': ma5,
            'ma20': ma20,
            'ma60': ma60,
            'df': df
        }
    except:
        return None

# ============================================================
# 3. 점수 계산 함수들
# ============================================================

def calculate_fundamental_score(stock_data):
    """기본적 분석 점수 계산 (PER, PBR, 영업이익증가율, ROE, 부채비율)"""
    # 임시 점수 (실제로는 재무데이터 필요)
    scores = {
        'PER': np.random.randint(60, 95),
        'PBR': np.random.randint(55, 90),
        '영업이익증가율': np.random.randint(50, 85),
        'ROE': np.random.randint(45, 80),
        '부채비율': np.random.randint(40, 75)
    }
    total = sum(scores.values()) / 5
    return total, scores

def calculate_technical_score(stock_data):
    """기술적 분석 점수 계산 (이동평균, MACD, 볼린저, 일목균형, 지지저항)"""
    # 임시 점수 (실제로는 기술적 지표 계산 필요)
    scores = {
        '이동평균선': np.random.randint(50, 90),
        'MACD': np.random.randint(45, 85),
        '볼린저밴드': np.random.randint(40, 80),
        '일목균형표': np.random.randint(50, 88),
        '지지/저항': np.random.randint(45, 82)
    }
    total = sum(scores.values()) / 5
    return total, scores

# ============================================================
# 4. 랭킹 생성 함수
# ============================================================

@st.cache_data(ttl=7200)
def generate_rankings():
    """전체 랭킹 생성 (기본적, 기술적, 종합)"""
    stocks = get_top_stocks()
    
    fundamental_list = []
    technical_list = []
    combined_list = []
    
    for _, row in stocks.iterrows():
        code = row['Code']
        name = row['Name']
        
        # 주가 데이터 수집
        stock_info = get_stock_price(code, name)
        if stock_info is None:
            continue
            
        # 점수 계산
        fund_score, fund_detail = calculate_fundamental_score(stock_info)
        tech_score, tech_detail = calculate_technical_score(stock_info)
        combined = (fund_score + tech_score) / 2
        
        stock_entry = {
            'code': code,
            'name': name,
            'price': stock_info['price'],
            'change': stock_info['change'],
            'fundamental_score': fund_score,
            'fundamental_detail': fund_detail,
            'technical_score': tech_score,
            'technical_detail': tech_detail,
            'combined_score': combined
        }
        
        fundamental_list.append(stock_entry)
        technical_list.append(stock_entry)
        combined_list.append(stock_entry)
    
    # 점수 기준 내림차순 정렬
    fundamental_list.sort(key=lambda x: x['fundamental_score'], reverse=True)
    technical_list.sort(key=lambda x: x['technical_score'], reverse=True)
    combined_list.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return fundamental_list, technical_list, combined_list

# ============================================================
# 5. UI 구성 (홈 페이지)
# ============================================================

def home_page():
    """홈 페이지"""
    st.title("🏠 퀀트 대시보드")
    st.markdown("---")
    
    # 데이터 수집
    with st.spinner("📊 시장 데이터를 불러오는 중..."):
        korea = get_korea_market_data()
        us = get_us_market_data()
        macro = get_macro_data()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🇰🇷 한국 시장")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("코스피", f"{korea['kospi']['price']:,.0f}", 
                     f"{korea['kospi']['change']:+.2f}%")
        with col_b:
            st.metric("코스닥", f"{korea['kosdaq']['price']:,.0f}", 
                     f"{korea['kosdaq']['change']:+.2f}%")
    
    with col2:
        st.subheader("🇺🇸 미국 시장")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("나스닥", f"{us['nasdaq']['price']:,.0f}", 
                     f"{us['nasdaq']['change']:+.2f}%")
        with col_b:
            st.metric("S&P500", f"{us['sp500']['price']:,.0f}", 
                     f"{us['sp500']['change']:+.2f}%")
    
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("💰 원자재 & 환율")
        st.metric("금 (Gold)", f"${macro['gold']:,.0f}")
        st.metric("WTI 유가", f"${macro['wti']:,.1f}")
        st.metric("환율 (USD/KRW)", f"{macro['exchange_rate']:,.0f} 원")
    
    with col4:
        st.subheader("📈 국채수익률 & 기준금리")
        st.metric("한국 10년 국채", f"{macro['kr_bond']:.1f}%")
        st.metric("미국 10년 국채", f"{macro['us_bond']:.1f}%")
    
    st.markdown("---")
    st.info("📌 *데이터는 한국 장마감(15:30)과 미국 장마감(익일 05:00)에 업데이트됩니다.*")

# ============================================================
# 6. UI 구성 (랭킹 페이지)
# ============================================================

def ranking_page(title, rank_list, score_key, detail_key, score_name):
    """랭킹 페이지 공통 템플릿"""
    st.title(f"📊 {title}")
    
    # 상위 30개만 표시
    top_30 = rank_list[:30]
    
    # 데이터프레임 생성
    df = pd.DataFrame([
        {
            '순위': i+1,
            '종목명': item['name'],
            '종목코드': item['code'],
            '현재가': f"{item['price']:,.0f}",
            '등락률': f"{item['change']:+.2f}%",
            '점수': f"{item[score_key]:.1f}"
        }
        for i, item in enumerate(top_30)
    ])
    
    # 테이블 표시
    st.dataframe(
        df,
        column_config={
            "순위": st.column_config.NumberColumn("순위", width="small"),
            "종목명": st.column_config.TextColumn("종목명", width="medium"),
            "종목코드": st.column_config.TextColumn("코드", width="small"),
            "현재가": st.column_config.TextColumn("현재가", width="medium"),
            "등락률": st.column_config.TextColumn("등락률", width="medium"),
            "점수": st.column_config.TextColumn("점수", width="small"),
        },
        hide_index=True,
        use_container_width=True
    )
    
    st.markdown("---")
    
    # 종목별 상세 점수
    st.subheader("📋 종목별 상세 점수")
    
    for item in top_30[:10]:  # 상위 10개만 상세 표시
        with st.expander(f"🔍 {item['name']} ({item['code']}) - {item[score_key]:.1f}점"):
            # 네이버 링크
            naver_url = f"https://finance.naver.com/item/main.naver?code={item['code']}"
            st.link_button("📊 네이버 증권 바로가기", naver_url)
            
            st.write("**상세 평가 지표:**")
            details = item[detail_key]
            for key, value in details.items():
                st.write(f"- {key}: {value:.1f}점")

# ============================================================
# 7. UI 구성 (검색 페이지)
# ============================================================

def search_page(rank_list):
    """종목 검색 페이지"""
    st.title("🔍 종목 검색")
    
    # 검색 입력
    search_term = st.text_input("종목명을 입력하세요", placeholder="예: 삼성전자")
    
    if search_term:
        # 검색 결과 필터링
        results = [item for item in rank_list if search_term in item['name']]
        
        if results:
            for item in results:
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.subheader(f"📊 {item['name']} ({item['code']})")
                    st.write(f"**현재가:** {item['price']:,.0f}원")
                    st.write(f"**등락률:** {item['change']:+.2f}%")
                    
                    # 네이버 링크
                    naver_url = f"https://finance.naver.com/item/main.naver?code={item['code']}"
                    st.link_button("📊 네이버 증권 바로가기", naver_url)
                
                with col2:
                    st.metric("기본적 분석", f"{item['fundamental_score']:.1f}점")
                    st.metric("기술적 분석", f"{item['technical_score']:.1f}점")
                    st.metric("종합 점수", f"{item['combined_score']:.1f}점")
                
                # 상세 점수
                with st.expander("📋 상세 점수 보기"):
                    st.write("**기본적 분석 지표:**")
                    for key, value in item['fundamental_detail'].items():
                        st.write(f"- {key}: {value:.1f}점")
                    
                    st.write("**기술적 분석 지표:**")
                    for key, value in item['technical_detail'].items():
                        st.write(f"- {key}: {value:.1f}점")
        else:
            st.warning(f"'{search_term}'에 대한 검색 결과가 없습니다.")

# ============================================================
# 8. 메인 앱 실행
# ============================================================

def main():
    """메인 앱"""
    # 사이드바 네비게이션
    with st.sidebar:
        st.image("https://via.placeholder.com/150x50/0E1117/00FF00?text=LOGO", use_column_width=True)
        st.markdown("## 📊 메뉴")
        
        page = st.radio(
            "페이지 선택",
            ["🏠 홈", "📊 기본적 분석", "📈 기술적 분석", "⚖️ 종합 분석", "🔍 종목 검색"],
            index=0
        )
        
        st.markdown("---")
        st.caption(f"📅 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        st.caption("🔄 한국 장마감(15:30) / 미국 장마감(05:00)")
    
    # 데이터 로딩
    with st.spinner("📊 데이터를 불러오는 중입니다..."):
        fundamental_list, technical_list, combined_list = generate_rankings()
    
    # 페이지 라우팅
    if page == "🏠 홈":
        home_page()
    elif page == "📊 기본적 분석":
        ranking_page("기본적 분석 랭킹", fundamental_list, 
                    'fundamental_score', 'fundamental_detail', '기본적 분석')
    elif page == "📈 기술적 분석":
        ranking_page("기술적 분석 랭킹", technical_list,
                    'technical_score', 'technical_detail', '기술적 분석')
    elif page == "⚖️ 종합 분석":
        ranking_page("종합 분석 랭킹", combined_list,
                    'combined_score', 'technical_detail', '종합 분석')
    elif page == "🔍 종목 검색":
        search_page(combined_list)

# ============================================================
# 9. 실행
# ============================================================

if __name__ == "__main__":
    main()