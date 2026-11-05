
import re
from itertools import combinations
from collections import Counter

import pandas as pd
import streamlit as st
import plotly.express as px


# ==========================================
# 1. 페이지 설정
# ==========================================

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.caption("송탄고등학교 중식 메뉴의 연관 규칙 분석")


# ==========================================
# 2. 데이터 불러오기
# ==========================================

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "it-teacher-go/data-share-/main/"
    "songtan_meals_184.csv"
)


@st.cache_data
def load_data():

    df = pd.read_csv(
        CSV_URL,
        encoding="utf-8"
    )

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(
                f"CSV에 '{col}' 열이 없습니다."
            )

    # 중식만 사용
    df = df[df["식사"] == "중식"].copy()

    # 결측값 제거
    df = df.dropna(
        subset=["날짜", "메뉴"]
    )

    return df


# ==========================================
# 3. 메뉴 이름 정리
# ==========================================

def clean_menu(menu):

    menu = str(menu)

    # 괄호와 괄호 안의 내용 제거
    while True:

        cleaned = re.sub(
            r"\([^()]*\)",
            "",
            menu
        )

        if cleaned == menu:
            break

        menu = cleaned

    return menu.strip()


# ==========================================
# 4. 하루 식단을 하나의 거래로 만들기
# ==========================================

def make_transactions(df):

    transactions = []

    for _, row in df.iterrows():

        menus = str(row["메뉴"]).split("|")

        cleaned_menus = []

        for menu in menus:

            menu = clean_menu(menu)

            if menu:
                cleaned_menus.append(menu)

        # 하루에 같은 메뉴가 중복되어도 한 번만 계산
        cleaned_menus = sorted(
            set(cleaned_menus)
        )

        transactions.append(
            cleaned_menus
        )

    return transactions


# ==========================================
# 5. 연관 규칙 분석
# ==========================================

def association_analysis(transactions):

    total_days = len(transactions)

    # 메뉴별 등장 횟수
    menu_count = Counter()

    # 메뉴 쌍별 동시 등장 횟수
    pair_count = Counter()

    # 전체 메뉴 종류
    all_menus = set()

    for basket in transactions:

        all_menus.update(basket)

        # 메뉴별 등장 횟수
        for menu in basket:
            menu_count[menu] += 1

        # 같은 날 함께 나온 메뉴 쌍
        for pair in combinations(basket, 2):
            pair_count[pair] += 1

    rules = []

    # 메뉴 쌍별 양방향 규칙 생성
    for (menu_a, menu_b), count in pair_count.items():

        # 지지도
        support = count / total_days

        # 메뉴별 등장 비율
        support_a = menu_count[menu_a] / total_days
        support_b = menu_count[menu_b] / total_days

        # A → B
        confidence_ab = count / menu_count[menu_a]
        lift_ab = confidence_ab / support_b

        rules.append({
            "조건": menu_a,
            "결과": menu_b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
        confidence_ba = count / menu_count[menu_b]
        lift_ba = confidence_ba / support_a

        rules.append({
            "조건": menu_b,
            "결과": menu_a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(
        rules,
        columns=[
            "조건",
            "결과",
            "동시",
            "지지도",
            "신뢰도",
            "향상도"
        ]
    )

    return (
        rules_df,
        menu_count,
        pair_count,
        all_menus
    )


# ==========================================
# 6. 데이터 분석 실행
# ==========================================

try:

    df = load_data()

    transactions = make_transactions(df)

    (
        rules_df,
        menu_count,
        pair_count,
        all_menus
    ) = association_analysis(transactions)

except Exception as e:

    st.error(
        f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}"
    )

    st.stop()


if len(transactions) == 0:

    st.warning("분석할 급식 데이터가 없습니다.")
    st.stop()


# ==========================================
# 7. 요약 정보
# ==========================================

st.subheader("📊 분석 데이터 요약")

col1, col2, col3 = st.columns(3)

with col1:

    st.metric(
        label="급식 일수",
        value=f"{len(transactions):,}일"
    )

with col2:

    st.metric(
        label="메뉴 종류 수",
        value=f"{len(all_menus):,}종"
    )

with col3:

    st.metric(
        label="함께 나온 메뉴 쌍 수",
        value=f"{len(pair_count):,}쌍"
    )


st.divider()


# ==========================================
# 8. 최소 동시 일수 설정
# ==========================================

st.subheader("⚙️ 분석 조건")

min_days = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 메뉴 규칙은 제외합니다."
)


# ==========================================
# 9. 메뉴 선택 필터
# ==========================================

st.subheader("🔎 메뉴별 규칙 찾기")

menu_options = [
    "전체 메뉴"
] + sorted(all_menus)

selected_menu = st.selectbox(
    "규칙을 좁혀 볼 메뉴를 선택하세요.",
    options=menu_options,
    index=0,
    key="association_menu_select"
)


# ==========================================
# 10. 정렬 기준 선택
# ==========================================

sort_option = st.selectbox(
    "표 정렬 기준",
    options=[
        "향상도 순",
        "신뢰도 순",
        "동시 순"
    ],
    index=0
)


# ==========================================
# 11. 최소 동시 일수 적용
# ==========================================

filtered_df = rules_df.copy()

filtered_df = filtered_df[
    filtered_df["동시"] >= min_days
].copy()


# ==========================================
# 12. 메뉴 필터 적용
# ==========================================

if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ].copy()


# ==========================================
# 13. 정렬 적용
# ==========================================

if sort_option == "향상도 순":

    filtered_df = filtered_df.sort_values(
        by=["향상도", "신뢰도", "동시"],
        ascending=[False, False, False]
    )

elif sort_option == "신뢰도 순":

    filtered_df = filtered_df.sort_values(
        by=["신뢰도", "향상도", "동시"],
        ascending=[False, False, False]
    )

elif sort_option == "동시 순":

    filtered_df = filtered_df.sort_values(
        by=["동시", "향상도", "신뢰도"],
        ascending=[False, False, False]
    )


# ==========================================
# 14. 연관 규칙 표
# ==========================================

st.subheader("📋 메뉴 연관 규칙")

st.caption(
    "조건 메뉴가 나왔을 때 결과 메뉴도 함께 나오는 관계입니다. "
    "각 메뉴 쌍은 방향을 바꾼 규칙도 포함합니다."
)

# 남은 규칙 수 표시
st.write(
    f"**현재 조건에서 남은 규칙: {len(filtered_df):,}개**"
)

if filtered_df.empty:

    st.info(
        "선택한 조건에 해당하는 규칙이 없습니다. "
        "최소 동시 일수를 낮추거나 다른 메뉴를 선택해 보세요."
    )

else:

    display_df = filtered_df[
        [
            "조건",
            "결과",
            "동시",
            "지지도",
            "신뢰도",
            "향상도"
        ]
    ].copy()

    # 백분율로 변환
    display_df["지지도"] *= 100
    display_df["신뢰도"] *= 100

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config={

            "조건": st.column_config.TextColumn(
                "조건"
            ),

            "결과": st.column_config.TextColumn(
                "결과"
            ),

            "동시": st.column_config.NumberColumn(
                "동시",
                format="%d회"
            ),

            "지지도": st.column_config.NumberColumn(
                "지지도",
                format="%.2f%%",
                help="전체 급식일 중 두 메뉴가 함께 나온 비율"
            ),

            "신뢰도": st.column_config.NumberColumn(
                "신뢰도",
                format="%.2f%%",
                help="조건 메뉴가 나온 날 중 결과 메뉴도 나온 비율"
            ),

            "향상도": st.column_config.NumberColumn(
                "향상도",
                format="%.3f",
                help="두 메뉴가 독립적으로 등장할 때와 비교한 연관 정도"
            )
        }
    )


st.caption(
    "※ 향상도가 1보다 크면 독립적으로 등장할 때보다 "
    "함께 등장하는 경향이 강합니다."
)


# ==========================================
# 15. 향상도 TOP 10 가로 막대그래프
# ==========================================

st.divider()

st.subheader("📈 향상도 TOP 10 메뉴 규칙")

st.caption(
    "최소 동시 일수와 메뉴 선택 조건을 적용한 상위 10개 규칙입니다."
)

chart_df = filtered_df.sort_values(
    by=["향상도", "신뢰도", "동시"],
    ascending=[False, False, False]
).head(10).copy()


if chart_df.empty:

    st.info("그래프로 표시할 규칙이 없습니다.")

else:

    chart_df["규칙"] = (
        chart_df["조건"] +
        " → " +
        chart_df["결과"]
    )

    # 가로 막대그래프에서 높은 값이 위로 오도록 정렬
    chart_df = chart_df.sort_values(
        "향상도",
        ascending=True
    )

    fig = px.bar(
        chart_df,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.2%",
            "신뢰도": ":.2%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "메뉴 규칙"
        },
        title="향상도가 높은 메뉴 연관 규칙 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=max(400, len(chart_df) * 48),
        xaxis_title="향상도",
        yaxis_title="조건 → 결과",
        showlegend=False,
        margin=dict(
            l=20,
            r=70,
            t=60,
            b=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# 16. 함께 나온 적 없는 짝
# ==========================================

st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.caption(
    "선택한 메뉴와 한 번도 같은 날 나오지 않았지만, "
    "각각 10일 이상 등장한 메뉴를 찾아줍니다."
)

# 위의 연관 규칙 메뉴 선택과 별도로 작동하는 메뉴 선택
no_pair_menu = st.selectbox(
    "함께 나온 적 없는 짝을 찾을 메뉴를 선택하세요.",
    options=sorted(all_menus),
    key="no_pair_menu_select"
)


# 선택한 메뉴의 등장 일수
selected_menu_days = menu_count[no_pair_menu]


# 선택한 메뉴와 함께 나온 적 없는 메뉴 찾기
no_pair_results = []

for candidate in all_menus:

    # 자기 자신은 제외
    if candidate == no_pair_menu:
        continue

    # 후보 메뉴의 등장 일수
    candidate_days = menu_count[candidate]

    # 10일 미만 등장한 메뉴 제외
    if candidate_days < 10:
        continue

    # 두 메뉴가 함께 나온 적이 있는지 확인
    pair = tuple(sorted([
        no_pair_menu,
        candidate
    ]))

    together_days = pair_count.get(pair, 0)

    # 한 번도 함께 나오지 않은 메뉴만 추가
    if together_days == 0:

        no_pair_results.append({
            "메뉴": candidate,
            "메뉴 등장 일수": candidate_days,
            "선택 메뉴 등장 일수": selected_menu_days
        })


# 등장 일수가 많은 순으로 정렬
no_pair_df = pd.DataFrame(
    no_pair_results,
    columns=[
        "메뉴",
        "메뉴 등장 일수",
        "선택 메뉴 등장 일수"
    ]
)

if not no_pair_df.empty:

    no_pair_df = no_pair_df.sort_values(
        by="메뉴 등장 일수",
        ascending=False
    ).reset_index(drop=True)


# 선택 메뉴 등장 일수 표시
st.write(
    f"**선택한 메뉴: {no_pair_menu} | 등장 일수: {selected_menu_days}일**"
)


# 결과 표시
if no_pair_df.empty:

    st.info(
        "조건에 맞는 메뉴가 없습니다. "
        "이 메뉴와 한 번도 함께 나오지 않은 10일 이상 등장 메뉴가 없습니다."
    )

else:

    st.write(
        f"**함께 나온 적 없는 메뉴: {len(no_pair_df):,}종**"
    )

    st.dataframe(
        no_pair_df,
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={

            "메뉴": st.column_config.TextColumn(
                "메뉴"
            ),

            "메뉴 등장 일수": st.column_config.NumberColumn(
                "메뉴 등장 일수",
                format="%d일"
            ),

            "선택 메뉴 등장 일수": st.column_config.NumberColumn(
                "선택 메뉴 등장 일수",
                format="%d일"
            )
        }
    )


# ==========================================
# 17. 분석 방법 안내
# ==========================================

st.divider()

with st.expander("📖 연관 규칙 분석 지표 알아보기"):

    st.markdown("""
    ### ① 지지도 (Support)

    전체 급식일 중 두 메뉴가 함께 나온 날의 비율입니다.

    지지도 = 두 메뉴가 함께 나온 일수 ÷ 전체 급식일 수

    ### ② 신뢰도 (Confidence)

    조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 비율입니다.

    신뢰도 = 두 메뉴가 함께 나온 일수 ÷ 조건 메뉴가 나온 일수

    ### ③ 향상도 (Lift)

    두 메뉴의 동시 등장 비율이 독립적으로 등장할 때와 비교해
    얼마나 높은지를 나타냅니다.

    향상도 = 신뢰도 ÷ 결과 메뉴의 등장 비율

    - 향상도 > 1 : 함께 나오는 경향이 독립적일 때보다 강함
    - 향상도 = 1 : 독립적으로 등장하는 것과 비슷함
    - 향상도 < 1 : 함께 나오는 경향이 독립적일 때보다 약함

    ### ④ 동시

    두 메뉴가 같은 날 급식에 등장한 횟수입니다.

    ### ⑤ 규칙의 방향

    A → B와 B → A는 서로 다른 규칙입니다.

    두 규칙은 지지도와 동시 등장 횟수는 같지만,
    신뢰도와 향상도는 다를 수 있습니다.

    ### ⑥ 함께 나온 적 없는 짝

    선택한 메뉴와 한 번도 같은 날 나오지 않은 메뉴 중
    각각 10일 이상 등장한 메뉴를 보여 줍니다.
    """)
