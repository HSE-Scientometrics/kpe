import pandas as pd
import streamlit as st
import plotly.express as px
from io import StringIO

# ---------------------
# Настройки типов публикаций
# ---------------------
PORTAL_TYPES = [
    "Статья", "Труды конференций", "Монографии",
    "Учебные пособия", "Учебники", "Сборники статей"
]
SCOPUS_TYPES = ["Article", "Conference Paper", "Book"]

# ---------------------
# Streamlit
# ---------------------
st.set_page_config(page_title="График публикаций НИУ ВШЭ", layout="wide")
st.title("📊 Публикации НИУ ВШЭ: Portal и Scopus")

uploaded_file = st.file_uploader("Загрузите CSV-файл (разделитель ;)", type=["csv"])
if uploaded_file is None:
    st.stop()

# ---------------------
# Загрузка CSV
# ---------------------
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

# ---------------------
# Обработка
# ---------------------
df["Фракционный балл"] = pd.to_numeric(df["Фракционный балл"], errors="coerce").fillna(0)
df["Подразделение_list"] = df["Подразделение (широко)"].fillna("").apply(lambda x: [i.strip() for i in x.split(";") if i.strip()])
df = df.explode("Подразделение_list")
div_cnt = df.groupby("НАЗВАНИЕ")["Подразделение_list"].transform("count").replace(0,1)
df["fractional_score_adj"] = df["Фракционный балл"] / div_cnt

# Берём последние 3 года
df = df[df["ГОД"] >= df["ГОД"].max() - 2]

# Преобразуем ГОД и Подразделение в строку (для категориальных цветов)
df["ГОД"] = df["ГОД"].astype(str)
df["Подразделение_list"] = df["Подразделение_list"].astype(str)

# ---------------------
# Фильтры справа (выпадающие списки)
# ---------------------
col1, col2 = st.columns([4,1])
with col2:
    selected_portal_scopus = st.selectbox(
        "Источник данных",
        options=["Portal", "Scopus"]
    )

    selected_years = st.multiselect(
        "Годы",
        options=sorted(df["ГОД"].unique()),
        default=sorted(df["ГОД"].unique())
    )

    # Фильтр подразделений без "nan"
    div_options = sorted([x for x in df["Подразделение_list"].unique() if str(x).lower() != "nan"])
    selected_divs = st.multiselect(
    "Подразделения",
    options=div_options,
    default=div_options
    )


    # Тип публикации зависит от выбора Portal/Scopus
    types_options = PORTAL_TYPES if selected_portal_scopus == "Portal" else SCOPUS_TYPES
    selected_types = st.multiselect(
        f"Тип публикаций ({selected_portal_scopus})",
        options=types_options,
        default=types_options
    )

# ---------------------
# Фильтрация данных
# ---------------------
df_filtered = df[df["ГОД"].isin(selected_years) & df["Подразделение_list"].isin(selected_divs)]
df_filtered = df_filtered[df_filtered["Тип (по Portal)" if selected_portal_scopus == "Portal" else "Тип (по Scopus)"].isin(selected_types)]

# ---------------------
# Агрегация
# ---------------------
agg_df = df_filtered.groupby(["ГОД", "Подразделение_list"], as_index=False).agg(
    publications_cnt=("НАЗВАНИЕ", "nunique"),
    fractional_score_sum=("fractional_score_adj", "sum")
)

# ---------------------
# Построение графика с русскими подписями
# ---------------------
if agg_df.empty:
    st.warning("Нет данных для выбранных фильтров")
else:
    order = agg_df.groupby("Подразделение_list")["publications_cnt"].sum().sort_values(ascending=False).index
    years = sorted(agg_df["ГОД"].unique())
    colors = px.colors.qualitative.Safe
    color_map = {year: colors[i % len(colors)] for i, year in enumerate(years)}

    fig_pub = px.bar(
        agg_df,
        x="Подразделение_list",
        y="publications_cnt",
        color="ГОД",
        color_discrete_map=color_map,
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{selected_portal_scopus}: публикации",
        labels={"Подразделение_list": "Подразделение", "publications_cnt": "Количество публикаций", "ГОД": "Год"}
    )

    fig_frac = px.bar(
        agg_df,
        x="Подразделение_list",
        y="fractional_score_sum",
        color="ГОД",
        color_discrete_map=color_map,
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{selected_portal_scopus}: фракционный балл",
        labels={"Подразделение_list": "Подразделение", "fractional_score_sum": "Фракционный балл", "ГОД": "Год"}
    )

    with col1:
        st.plotly_chart(fig_pub, use_container_width=True)
        st.plotly_chart(fig_frac, use_container_width=True)
