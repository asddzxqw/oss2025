import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from folium import Icon
import numpy as np

# 페이지 설정
st.set_page_config(page_title="서울시 대기질 모니터링", page_icon="🌫️", layout="wide")

# CSS 스타일
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .good { color: #0066cc; }
    .moderate { color: #00cc00; }
    .bad { color: #ff9900; }
    .very-bad { color: #ff0000; }
</style>
""", unsafe_allow_html=True)

# 데이터 로드 함수
@st.cache_data
def load_data():
    """CSV 파일들을 로드하고 합치기"""
    dfs = []
    files = {
        '2008-2011': 'seoul_air_20082011.csv',
        '2012-2015': 'seoul_air_20122015.csv',
        '2016-2019': 'seoul_air_20162019.csv',
        '2020-2021': 'seoul_air_20202021.csv',
        '2022': 'seoul_air_2022.csv'
    }
    
    for period, file in files.items():
        try:
            df = pd.read_csv(file, encoding='utf-8')
            dfs.append(df)
        except:
            st.error(f"파일 읽기 실패: {file}")
    
    if dfs:
        data = pd.concat(dfs, ignore_index=True)
        # 날짜 형식 변환
        data['일시'] = pd.to_datetime(data['일시'], errors='coerce')
        data = data.dropna(subset=['일시'])
        data['연도'] = data['일시'].dt.year
        data['월'] = data['일시'].dt.month
        data['일'] = data['일시'].dt.day
        data['시간'] = data['일시'].dt.hour
        return data
    else:
        return pd.DataFrame()

# 대기질 등급 판정 함수
def get_air_quality_grade(value, pollutant='PM10'):
    """대기질 등급 반환"""
    if pd.isna(value):
        return '데이터없음'
    
    if pollutant == 'PM10':
        if value <= 30: return '좋음'
        elif value <= 80: return '보통'
        elif value <= 150: return '나쁨'
        else: return '매우나쁨'
    else:  # PM2.5
        if value <= 15: return '좋음'
        elif value <= 35: return '보통'
        elif value <= 75: return '나쁨'
        else: return '매우나쁨'

# 대기질 등급별 색상
def get_grade_color(grade):
    colors = {
        '좋음': '#0066cc',
        '보통': '#00cc00',
        '나쁨': '#ff9900',
        '매우나쁨': '#ff0000',
        '데이터없음': '#808080'
    }
    return colors.get(grade, '#808080')

# 앱 제목
st.title("🌫️ 서울시 대기질 실시간 모니터링 시스템")
st.caption(f"2008년부터 2022년까지의 서울시 미세먼지 데이터 분석")

# 데이터 로드
data = load_data()

if data.empty:
    st.error("데이터를 불러올 수 없습니다. CSV 파일을 확인해주세요.")
    st.stop()

# 사이드바 - 필터 및 설정
with st.sidebar:
    st.header("⚙️ 필터 설정")
    
    # 연도 선택
    years = sorted(data['연도'].unique())
    selected_year = st.selectbox("연도 선택", years, index=len(years)-1)
    
    # 구역 선택
    districts = sorted(data['구분'].unique())
    selected_districts = st.multiselect("구역 선택", districts, default=districts[:5])
    
    # 오염물질 선택
    pollutant = st.radio("오염물질", ['PM10', 'PM25'])
    
    # 즐겨찾기 구역
    st.markdown("---")
    st.header("⭐ 즐겨찾기 구역")
    if "favorite_districts" not in st.session_state:
        st.session_state.favorite_districts = []
    
    fav_district = st.selectbox("즐겨찾기 추가", districts)
    if st.button("추가"):
        if fav_district not in st.session_state.favorite_districts:
            st.session_state.favorite_districts.append(fav_district)
            st.success(f"{fav_district} 추가됨")
    
    if st.session_state.favorite_districts:
        st.write("즐겨찾기 목록:")
        for dist in st.session_state.favorite_districts:
            col1, col2 = st.columns([3, 1])
            col1.write(f"• {dist}")
            if col2.button("삭제", key=f"del_{dist}"):
                st.session_state.favorite_districts.remove(dist)
                st.rerun()

# 데이터 필터링
filtered_data = data[
    (data['연도'] == selected_year) & 
    (data['구분'].isin(selected_districts))
].copy()

# 메인 컨텐츠
tab1, tab2, tab3, tab4 = st.tabs(["📊 실시간 현황", "📈 트렌드 분석", "🗺️ 지도 시각화", "📋 상세 데이터"])

with tab1:
    # 현재 상태 요약
    st.header("현재 대기질 상태")
    
    # 최근 데이터만 추출
    latest_data = filtered_data[filtered_data['일시'] == filtered_data['일시'].max()]
    
    if not latest_data.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        avg_value = latest_data[pollutant].mean()
        max_value = latest_data[pollutant].max()
        min_value = latest_data[pollutant].min()
        
        col1.metric("평균", f"{avg_value:.1f} ㎍/㎥", 
                   delta=get_air_quality_grade(avg_value, pollutant))
        col2.metric("최고", f"{max_value:.1f} ㎍/㎥",
                   delta=latest_data[latest_data[pollutant] == max_value]['구분'].iloc[0])
        col3.metric("최저", f"{min_value:.1f} ㎍/㎥",
                   delta=latest_data[latest_data[pollutant] == min_value]['구분'].iloc[0])
        col4.metric("측정 시간", latest_data['일시'].iloc[0].strftime('%Y-%m-%d %H시'))
    
    # 구역별 현황
    st.subheader(f"구역별 {pollutant} 농도")
    
    district_avg = filtered_data.groupby('구분')[pollutant].mean().sort_values(ascending=False)
    
    fig_bar = px.bar(
        x=district_avg.index,
        y=district_avg.values,
        title=f"{selected_year}년 구역별 평균 {pollutant} 농도",
        labels={'x': '구역', 'y': f'{pollutant} (㎍/㎥)'},
        color=district_avg.values,
        color_continuous_scale=['blue', 'green', 'yellow', 'red']
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.header("시계열 트렌드 분석")
    
    # 월별 트렌드
    monthly_trend = filtered_data.groupby(['월', '구분'])[pollutant].mean().reset_index()
    
    fig_line = px.line(
        monthly_trend,
        x='월',
        y=pollutant,
        color='구분',
        title=f"{selected_year}년 월별 {pollutant} 농도 변화",
        labels={'월': '월', pollutant: f'{pollutant} (㎍/㎥)'}
    )
    st.plotly_chart(fig_line, use_container_width=True)
    
    # 시간대별 패턴
    hourly_pattern = filtered_data.groupby(['시간'])[pollutant].mean().reset_index()
    
    fig_hour = px.bar(
        hourly_pattern,
        x='시간',
        y=pollutant,
        title=f"시간대별 평균 {pollutant} 농도",
        labels={'시간': '시간', pollutant: f'{pollutant} (㎍/㎥)'}
    )
    st.plotly_chart(fig_hour, use_container_width=True)

with tab3:
    st.header("지도 시각화")
    
    # 서울시 구청 좌표
    district_coords = {
        '종로구': [37.5735, 126.9790],
        '중구': [37.5641, 126.9979],
        '용산구': [37.5326, 126.9905],
        '성동구': [37.5633, 127.0371],
        '광진구': [37.5385, 127.0823],
        '동대문구': [37.5744, 127.0400],
        '중랑구': [37.6063, 127.0936],
        '성북구': [37.5894, 127.0167],
        '강북구': [37.6398, 127.0257],
        '도봉구': [37.6687, 127.0471],
        '노원구': [37.6543, 127.0568],
        '은평구': [37.6175, 126.9227],
        '서대문구': [37.5794, 126.9365],
        '마포구': [37.5664, 126.9014],
        '양천구': [37.5169, 126.8667],
        '강서구': [37.5509, 126.8495],
        '구로구': [37.4954, 126.8876],
        '금천구': [37.4567, 126.8958],
        '영등포구': [37.5264, 126.8962],
        '동작구': [37.5124, 126.9393],
        '관악구': [37.4782, 126.9516],
        '서초구': [37.4837, 127.0324],
        '강남구': [37.5172, 127.0473],
        '송파구': [37.5145, 127.1058],
        '강동구': [37.5301, 127.1238]
    }
    
    # 지도 생성
    m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
    
    # 구역별 데이터 표시
    for district in selected_districts:
        if district in district_coords:
            district_data = filtered_data[filtered_data['구분'] == district]
            if not district_data.empty:
                avg_pollution = district_data[pollutant].mean()
                grade = get_air_quality_grade(avg_pollution, pollutant)
                color = 'blue' if grade == '좋음' else 'green' if grade == '보통' else 'orange' if grade == '나쁨' else 'red'
                
                popup_html = f"""
                <div style="width: 200px;">
                    <strong>{district}</strong><br>
                    평균 {pollutant}: {avg_pollution:.1f} ㎍/㎥<br>
                    등급: {grade}
                </div>
                """
                
                folium.CircleMarker(
                    location=district_coords[district],
                    radius=10,
                    popup=folium.Popup(popup_html, max_width=250),
                    color=color,
                    fill=True,
                    fillColor=color
                ).add_to(m)
    
    st_folium(m, width=700, height=500)

with tab4:
    st.header("상세 데이터")
    
    # 날짜 범위 선택
    date_range = st.date_input(
        "날짜 범위 선택",
        value=(filtered_data['일시'].min().date(), filtered_data['일시'].max().date()),
        min_value=filtered_data['일시'].min().date(),
        max_value=filtered_data['일시'].max().date()
    )
    
    # 선택한 날짜 범위의 데이터
    date_filtered = filtered_data[
        (filtered_data['일시'].dt.date >= date_range[0]) &
        (filtered_data['일시'].dt.date <= date_range[1])
    ]
    
    # 통계 요약
    st.subheader("통계 요약")
    summary_stats = date_filtered.groupby('구분')[pollutant].agg(['mean', 'max', 'min', 'std']).round(1)
    st.dataframe(summary_stats, use_container_width=True)
    
    # 원본 데이터
    with st.expander("원본 데이터 보기"):
        st.dataframe(date_filtered[['일시', '구분', pollutant]], use_container_width=True)
    
    # 다운로드 버튼
    csv = date_filtered.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 데이터 다운로드 (CSV)",
        data=csv,
        file_name=f'air_quality_{selected_year}_{pollutant}.csv',
        mime='text/csv'
    )

# 사용자 메모 기능
st.markdown("---")
st.header("📝 분석 메모")
memo_text = st.text_area("대기질 분석에 대한 메모를 작성하세요", height=100)
if st.button("메모 저장"):
    if "memos" not in st.session_state:
        st.session_state.memos = []
    st.session_state.memos.append({
        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'memo': memo_text
    })
    st.success("메모가 저장되었습니다")

# 저장된 메모 표시
if "memos" in st.session_state and st.session_state.memos:
    with st.expander("저장된 메모 보기"):
        for memo in st.session_state.memos:
            st.write(f"**{memo['date']}**")
            st.write(memo['memo'])
            st.markdown("---")
