import pandas as pd
import streamlit as st
import plotly.express as px
from io import StringIO

# --------------------------------------------------
# Настройки
# --------------------------------------------------

PORTAL_TYPES = [
    "Статья",
    "Труды конференций",
    "Монографии",
    "Учебные пособия",
    "Учебники",
    "Сборники статей"
]

SCOPUS_TYPES = [
    "Article",
    "Conference Paper",
    "Book"
]

# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.set_page_config(page_title="Графики публикаций НИУ ВШЭ", layout="wide")
st.title("📊 Публикации НИУ ВШЭ: Portal и Scopus")

uploaded_file = st.file_uploader("Загрузите CSV-файл (разделитель ;)", type=["csv"])
if uploaded_file is None:
    st.stop()

# --------------------------------------------------
# Загрузка CSV
# --------------------------------------------------

def load_csv(uploaded_file):
    encodings = ["utf-8-sig", "utf-8", "cp1251", "windows-1251"]
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=";", encoding=enc)
            return df
        except:
            continue
    uploaded_file.seek(0)
    raw = uploaded_file.read().decode("utf-8", errors="ignore")
    df = pd.read_csv(StringIO(raw), sep=";")
    return df

df = load_csv(uploaded_file)

# --------------------------------------------------
# Обработка данных
# --------------------------------------------------

# Приведение фракционного балла к числу
df["Фракционный балл"] = pd.to_numeric(df["Фракционный балл"], errors="coerce").fillna(0)

# Разделение подразделений
df["Подразделение_list"] = df["Подразделение (широко)"].fillna("").apply(lambda x: [i.strip() for i in x.split(";") if i.strip()])
df = df.explode("Подразделение_list")

# Расчет фракционного балла с делением на количество подразделений
div_cnt = df.groupby("НАЗВАНИЕ")["Подразделение_list"].transform("count").replace(0,1)
df["fractional_score_adj"] = df["Фракционный балл"] / div_cnt

# --------------------------------------------------
# Фильтры справа
# --------------------------------------------------

st.sidebar.header("Фильтры")
selected_years = st.sidebar.multiselect("Годы", options=sorted(df["ГОД"].dropna().unique()), default=sorted(df["ГОД"].dropna().unique()))
selected_divs = st.sidebar.multiselect("Подразделения", options=sorted(df["Подразделение_list"].dropna().unique()), default=sorted(df["Подразделение_list"].dropna().unique()))

df = df[df["ГОД"].isin(selected_years) & df["Подразделение_list"].isin(selected_divs)]

# --------------------------------------------------
# Агрегация
# --------------------------------------------------

def aggregate_data(df, types_list):
    df_filtered = df[df["Тип (по Portal)"].isin(types_list)] if types_list == PORTAL_TYPES else df[df["Тип (по Scopus)"].isin(types_list)]
    agg = df_filtered.groupby(["ГОД", "Подразделение_list"], as_index=False).agg(
        publications_cnt=("НАЗВАНИЕ", "nunique"),
        fractional_score_sum=("fractional_score_adj", "sum")
    )
    return agg

portal_df = aggregate_data(df, PORTAL_TYPES)
scopus_df = aggregate_data(df, SCOPUS_TYPES)

# --------------------------------------------------
# Построение графиков
# --------------------------------------------------

def draw_chart(df, title):
    if df.empty:
        st.warning(f"Нет данных для {title}")
        return

    order = df.groupby("Подразделение_list")["publications_cnt"].sum().sort_values(ascending=False).index

    fig_pub = px.bar(
        df,
        x="Подразделение_list",
        y="publications_cnt",
        color="ГОД",
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{title}: публикации",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    fig_frac = px.bar(
        df,
        x="Подразделение_list",
        y="fractional_score_sum",
        color="ГОД",
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{title}: фракционный балл",
        color_discrete_sequence=px.colors.qualitative.Safe
    )

    st.plotly_chart(fig_pub, use_container_width=True)
    st.plotly_chart(fig_frac, use_container_width=True)

# --------------------------------------------------
# Вывод графиков
# --------------------------------------------------

tab1, tab2 = st.tabs(["Portal", "Scopus"])

with tab1:
    draw_chart(portal_df, "Portal")

with tab2:
    draw_chart(scopus_df, "Scopus")
