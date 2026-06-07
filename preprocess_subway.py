"""
서울시 지하철 호선별·역별·시간대별 승하차 인원 전처리 스크립트
- 원본: 81,732행 × 52열 (Wide 형태, 시간대별 컬럼 분리)
- 결과: Long 형태로 변환 + 파생 변수 추가 + 정제
"""

import pandas as pd

# ─────────────────────────────────────────────
# 1. 데이터 로드
# ─────────────────────────────────────────────
FILE_PATH = r"C:\Users\win\Desktop\고급\서울시 지하철 호선별 역별 시간대별 승하차 인원 정보.csv"

df = pd.read_csv(FILE_PATH, encoding="cp949")
print(f"[원본] {df.shape[0]:,}행 × {df.shape[1]}열")


# ─────────────────────────────────────────────
# 2. 불필요 컬럼 제거
# ─────────────────────────────────────────────
# '작업일자'는 데이터 갱신 날짜로 분석에 불필요
df = df.drop(columns=["작업일자"])


# ─────────────────────────────────────────────
# 3. 날짜 파싱 (사용월 → year / month / date)
# ─────────────────────────────────────────────
df["사용월"] = df["사용월"].astype(str)
df["연도"] = df["사용월"].str[:4].astype(int)
df["월"]   = df["사용월"].str[4:6].astype(int)
df["날짜"]  = pd.to_datetime(df["사용월"], format="%Y%m")


# ─────────────────────────────────────────────
# 4. Wide → Long 변환 (시간대 컬럼 → 행으로)
# ─────────────────────────────────────────────
id_vars = ["사용월", "연도", "월", "날짜", "호선명", "지하철역"]

# 승차 / 하차 컬럼을 각각 melt 후 합치기
승차_cols = [c for c in df.columns if "승차인원" in c]
하차_cols = [c for c in df.columns if "하차인원" in c]

df_승차 = df.melt(
    id_vars=id_vars,
    value_vars=승차_cols,
    var_name="시간대_승차",
    value_name="승차인원"
)
df_승차["시간대"] = df_승차["시간대_승차"].str.replace(" 승차인원", "", regex=False)

df_하차 = df.melt(
    id_vars=id_vars,
    value_vars=하차_cols,
    var_name="시간대_하차",
    value_name="하차인원"
)
df_하차["시간대"] = df_하차["시간대_하차"].str.replace(" 하차인원", "", regex=False)

# 시간대 기준으로 합치기
df_long = df_승차[id_vars + ["시간대", "승차인원"]].merge(
    df_하차[id_vars + ["시간대", "하차인원"]],
    on=id_vars + ["시간대"],
    how="inner"
)

print(f"[Long 변환 후] {df_long.shape[0]:,}행 × {df_long.shape[1]}열")


# ─────────────────────────────────────────────
# 5. 시간대 정수 파싱 (시작 시각 기준)
# ─────────────────────────────────────────────
# 예: "04시-05시" → 4
df_long["시작시"] = (
    df_long["시간대"]
    .str.extract(r"^(\d{2})시")[0]
    .astype(int)
)


# ─────────────────────────────────────────────
# 6. 파생 변수 생성
# ─────────────────────────────────────────────
# 총 이용인원 (승차 + 하차)
df_long["총이용인원"] = df_long["승차인원"] + df_long["하차인원"]

# 시간대 구분 (새벽 / 오전 / 오후 / 저녁 / 심야)
def classify_time(h):
    if h in range(4, 7):
        return "새벽"
    elif h in range(7, 12):
        return "오전"
    elif h in range(12, 18):
        return "오후"
    elif h in range(18, 22):
        return "저녁"
    else:
        return "심야"

df_long["시간구분"] = df_long["시작시"].apply(classify_time)

# 피크 여부 (출퇴근 러시아워: 7~9시, 18~20시)
df_long["피크여부"] = df_long["시작시"].isin([7, 8, 18, 19])

# 분기
df_long["분기"] = df_long["월"].apply(lambda m: f"Q{(m - 1) // 3 + 1}")


# ─────────────────────────────────────────────
# 7. 호선명 정규화 (중복 표기 통일)
# ─────────────────────────────────────────────
# '9호선2단계', '9호선2~3단계' → '9호선'으로 통일
df_long["호선명_정규화"] = df_long["호선명"].replace(
    {"9호선2단계": "9호선", "9호선2~3단계": "9호선"}
)


# ─────────────────────────────────────────────
# 8. 컬럼 정리 및 정렬
# ─────────────────────────────────────────────
final_cols = [
    "날짜", "연도", "월", "분기",
    "호선명", "호선명_정규화", "지하철역",
    "시간대", "시작시", "시간구분", "피크여부",
    "승차인원", "하차인원", "총이용인원"
]

df_final = df_long[final_cols].sort_values(
    ["날짜", "호선명", "지하철역", "시작시"]
).reset_index(drop=True)


# ─────────────────────────────────────────────
# 9. 저장
# ─────────────────────────────────────────────
OUTPUT_PATH = r"C:\Users\win\Desktop\고급\서울시_지하철_전처리.csv"
df_final.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

print(f"\n[최종 결과] {df_final.shape[0]:,}행 × {df_final.shape[1]}열")
print(f"저장 완료: {OUTPUT_PATH}")
print("\n── 샘플 (5행) ──")
print(df_final.head())
print("\n── 컬럼별 타입 ──")
print(df_final.dtypes)
print("\n── 기초 통계 ──")
print(df_final[["승차인원", "하차인원", "총이용인원"]].describe())
