import pandas as pd
import streamlit as st
import plotly.express as px
from io import StringIO

# ---------------------
# Константы
# ---------------------
PORTAL_TYPES = ["Статья", "Труды конференций", "Монографии", "Сборники статей", "Рецензия"]
HSE_LIST_ALLOWED = ["A", "B", "A_Book", "A_Conf"]

# ---------------------
# Streamlit
# ---------------------
st.set_page_config(page_title="Публикации НИУ ВШЭ", layout="wide")
st.title("📊 Публикации НИУ ВШЭ")

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
# Преобразование числовых колонок
# ---------------------
df["Фракционный балл"] = pd.to_numeric(df["Фракционный балл"], errors="coerce").fillna(0)
df["Фракционный балл по порталу"] = pd.to_numeric(
    df["Фракционный балл по порталу"], errors="coerce"
).fillna(0)

# ---------------------
# Фильтр по списку НИУ ВШЭ
# ---------------------
df = df[df["Список НИУ ВШЭ"].isin(HSE_LIST_ALLOWED)]

# ---------------------
# Разбор подразделений
# ---------------------
df["Подразделение_list"] = (
    df["Подразделение (широко)"]
    .fillna("")
    .astype(str)
    .apply(lambda x: [i.strip() for i in x.split(";") if i.strip()])
)

df = df.explode("Подразделение_list")

# Полная очистка мусорных значений
df["Подразделение_list"] = df["Подразделение_list"].astype(str).str.strip()

df = df[
    (df["Подразделение_list"] != "") &
    (df["Подразделение_list"].str.lower() != "nan") &
    (df["Подразделение_list"].str.lower() != "none")
]


# ---------------------
# Последние 3 года
# ---------------------
last_three_years = df["ГОД"].max() - 2
df = df[df["ГОД"] >= last_three_years]
df["ГОД"] = df["ГОД"].astype(str)

# ---------------------
# Интерфейс фильтров
# ---------------------
col1, col2 = st.columns([4, 1])

with col2:
    data_source = st.selectbox(
        "Источник данных",
        options=["Portal", "Все публикации"]
    )

    selected_years = st.multiselect(
        "Годы",
        options=sorted(df["ГОД"].unique()),
        default=sorted(df["ГОД"].unique())
    )

    div_options = sorted(df["Подразделение_list"].unique())
    selected_divs = st.multiselect(
        "Подразделения",
        options=div_options,
        default=div_options
    )

    # Фильтр по рецензированию только для "Все публикации"
    if data_source == "Все публикации":
        strict_values = sorted(df["Рец тип строгий"].dropna().unique())
        non_strict_values = sorted(df["Рец тип не строгий"].dropna().unique())

        selected_strict = st.multiselect(
            "Рец тип строгий",
            options=strict_values,
            default=strict_values
        )

        selected_non_strict = st.multiselect(
            "Рец тип не строгий",
            options=non_strict_values,
            default=non_strict_values
        )

# ---------------------
# Фильтрация данных
# ---------------------
df_filtered = df[
    df["ГОД"].isin(selected_years) &
    df["Подразделение_list"].isin(selected_divs)
]

if data_source == "Portal":
    df_filtered = df_filtered[
        df_filtered["Тип (по Portal)"].isin(PORTAL_TYPES)
    ]
    frac_column = "Фракционный балл по порталу"

else:
    df_filtered = df_filtered[
        df_filtered["Рец тип строгий"].isin(selected_strict) &
        df_filtered["Рец тип не строгий"].isin(selected_non_strict)
    ]
    frac_column = "Фракционный балл"

# ---------------------
# Агрегация
# ---------------------
agg_df = df_filtered.groupby(
    ["ГОД", "Подразделение_list"], as_index=False
).agg(
    publications_cnt=("НАЗВАНИЕ", "count"),
    fractional_score_sum=(frac_column, "sum")
)

# ---------------------
# Построение графиков
# ---------------------
if agg_df.empty:
    st.warning("Нет данных для выбранных фильтров")
else:
    order = agg_df.groupby("Подразделение_list")["publications_cnt"] \
                  .sum().sort_values(ascending=False).index

    years = sorted(agg_df["ГОД"].unique())
    colors = px.colors.qualitative.Safe
    color_map = {year: colors[i % len(colors)] for i, year in enumerate(years)}

    fig_pub = px.bar(
        agg_df,
        x="Подразделение_list",
        y="publications_cnt",
        color="ГОД",
        category_orders={"Подразделение_list": order},
        color_discrete_map=color_map,
        barmode="group",
        title=f"{data_source}: количество публикаций",
        labels={
            "Подразделение_list": "Подразделение",
            "publications_cnt": "Количество публикаций",
            "ГОД": "Год"
        }
    )

    fig_frac = px.bar(
        agg_df,
        x="Подразделение_list",
        y="fractional_score_sum",
        color="ГОД",
        category_orders={"Подразделение_list": order},
        color_discrete_map=color_map,
        barmode="group",
        title=f"{data_source}: фракционный балл",
        labels={
            "Подразделение_list": "Подразделение",
            "fractional_score_sum": "Фракционный балл",
            "ГОД": "Год"
        }
    )

    with col1:
        st.plotly_chart(fig_pub, use_container_width=True)
        st.plotly_chart(fig_frac, use_container_width=True)
