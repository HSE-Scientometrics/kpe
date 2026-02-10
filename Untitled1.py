import pandas as pd
import streamlit as st
import plotly.express as px
from io import StringIO

# --------------------------------------------------
# Настройки типов публикаций
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
# Функция загрузки CSV
# --------------------------------------------------
def load_csv(uploaded_file):
    encodings = ["utf-8-sig", "utf-8", "cp1251", "windows-1251"]
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, sep=";", encoding=enc)
        except:
            continue
    uploaded_file.seek(0)
    raw = uploaded_file.read().decode("utf-8", errors="ignore")
    return pd.read_csv(StringIO(raw), sep=";")

df = load_csv(uploaded_file)

# --------------------------------------------------
# Обработка данных
# --------------------------------------------------
df["Фракционный балл"] = pd.to_numeric(df["Фракционный балл"], errors="coerce").fillna(0)
df["Подразделение_list"] = df["Подразделение (широко)"].fillna("").apply(lambda x: [i.strip() for i in x.split(";") if i.strip()])
df = df.explode("Подразделение_list")
div_cnt = df.groupby("НАЗВАНИЕ")["Подразделение_list"].transform("count").replace(0,1)
df["fractional_score_adj"] = df["Фракционный балл"] / div_cnt

# --------------------------------------------------
# Отбор последних 3 лет
# --------------------------------------------------
df = df[df["ГОД"] >= df["ГОД"].max() - 2]

# --------------------------------------------------
# Фильтры справа
# --------------------------------------------------
st.subheader("Фильтры")

col1, col2 = st.columns([4,1])  # левая зона для графиков, правая для фильтров
with col2:
    selected_years = st.multiselect(
        "Выберите годы",
        options=sorted(df["ГОД"].unique()),
        default=sorted(df["ГОД"].unique())
    )
    selected_divs = st.multiselect(
        "Подразделения",
        options=sorted(df["Подразделение_list"].unique()),
        default=sorted(df["Подразделение_list"].unique())
    )

df = df[df["ГОД"].isin(selected_years) & df["Подразделение_list"].isin(selected_divs)]

# --------------------------------------------------
# Агрегация данных
# --------------------------------------------------
def aggregate_data(df, types_list, portal=True):
    if portal:
        df_filtered = df[df["Тип (по Portal)"].isin(types_list)]
    else:
        df_filtered = df[df["Тип (по Scopus)"].isin(types_list)]
    agg = df_filtered.groupby(["ГОД", "Подразделение_list"], as_index=False).agg(
        publications_cnt=("НАЗВАНИЕ", "nunique"),
        fractional_score_sum=("fractional_score_adj", "sum")
    )
    return agg

portal_df = aggregate_data(df, PORTAL_TYPES, portal=True)
scopus_df = aggregate_data(df, SCOPUS_TYPES, portal=False)

# --------------------------------------------------
# Построение графиков
# --------------------------------------------------
def draw_chart(df, title):
    if df.empty:
        st.warning(f"Нет данных для {title}")
        return

    order = df.groupby("Подразделение_list")["publications_cnt"].sum().sort_values(ascending=False).index
    years = sorted(df["ГОД"].unique())
    colors = px.colors.qualitative.Safe  # фиксированная палитра
    color_map = {year: colors[i % len(colors)] for i, year in enumerate(years)}

    fig_pub = px.bar(
        df,
        x="Подразделение_list",
        y="publications_cnt",
        color="ГОД",
        color_discrete_map=color_map,
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{title}: публикации"
    )

    fig_frac = px.bar(
        df,
        x="Подразделение_list",
        y="fractional_score_sum",
        color="ГОД",
        color_discrete_map=color_map,
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{title}: фракционный балл"
    )

    with col1:
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

