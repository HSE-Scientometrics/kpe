#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd
import streamlit as st
import plotly.express as px

# --------------------------------------------------
# Константы методики
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

HSE_LIST_ALLOWED = ["A", "B", "A_Book", "A_Conf"]

DATA_PATH = "НЦ_Ежеквартальный_реестр_2025_IV_квартал_полный.csv"


# --------------------------------------------------
# Загрузка и подготовка данных
# --------------------------------------------------

@st.cache_data
def load_and_prepare_data():
    reestr = pd.read_csv(DATA_PATH, sep=";")

    # фильтры методики
    reestr = reestr[
        (reestr["Список НИУ ВШЭ"].isin(HSE_LIST_ALLOWED)) &
        (reestr["Рец тип строгий"] == 1)
    ]

    # последние 3 года
    max_year = reestr["ГОД"].max()
    reestr = reestr[reestr["ГОД"] >= max_year - 2]

    # подразделения
    reestr["Подразделение_list"] = (
        reestr["Подразделение (широко)"]
        .fillna("")
        .apply(lambda x: [i.strip() for i in x.split(";") if i.strip()])
    )

    return reestr


def explode_and_fraction(reestr: pd.DataFrame) -> pd.DataFrame:
    reestr = reestr.explode("Подразделение_list")

    div_cnt = (
        reestr.groupby("НАЗВАНИЕ")["Подразделение_list"]
        .transform("count")
    )

    reestr["fractional_score_adj"] = reestr["Фракционный балл"] / div_cnt
    reestr["publication_unit"] = 1 / div_cnt

    return reestr


def aggregate(reestr: pd.DataFrame) -> pd.DataFrame:
    return (
        reestr.groupby(
            ["ГОД", "Подразделение_list"], as_index=False
        )
        .agg(
            publications_cnt=("НАЗВАНИЕ", "nunique"),
            fractional_score_sum=("fractional_score_adj", "sum")
        )
    )


def build_portal_agg(reestr):
    df = reestr[reestr["Тип (по Portal)"].isin(PORTAL_TYPES)]
    df = explode_and_fraction(df)
    return aggregate(df)


def build_scopus_agg(reestr):
    df = reestr[reestr["Тип (по Scopus)"].isin(SCOPUS_TYPES)]
    df = explode_and_fraction(df)
    return aggregate(df)


# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.set_page_config(
    page_title="Публикационная активность НИУ ВШЭ",
    layout="wide"
)

st.title("Публикационная активность по подразделениям НИУ ВШЭ")

reestr = load_and_prepare_data()
portal_df = build_portal_agg(reestr)
scopus_df = build_scopus_agg(reestr)

tab1, tab2 = st.tabs(["Portal", "Scopus"])


def render_tab(df, title_prefix):
    years = sorted(df["ГОД"].unique())
    divisions = sorted(df["Подразделение_list"].unique())

    col1, col2, col3 = st.columns([2, 4, 2])

    with col1:
        selected_years = st.multiselect(
            "Годы",
            years,
            default=years
        )

    with col2:
        selected_divs = st.multiselect(
            "Подразделения",
            divisions,
            default=divisions
        )

    with col3:
        top_n = st.selectbox(
            "Показать подразделений",
            [10, 15, 20, "Все"],
            index=0
        )

    filtered = df[
        (df["ГОД"].isin(selected_years)) &
        (df["Подразделение_list"].isin(selected_divs))
    ]

    order = (
        filtered.groupby("Подразделение_list")["publications_cnt"]
        .sum()
        .sort_values(ascending=False)
    )

    if top_n != "Все":
        order = order.head(top_n)

    filtered = filtered[
        filtered["Подразделение_list"].isin(order.index)
    ]

    # --- Публикации ---
    st.subheader(f"{title_prefix}: количество публикаций")

    fig_pub = px.bar(
        filtered,
        x="Подразделение_list",
        y="publications_cnt",
        color="ГОД",
        category_orders={"Подразделение_list": order.index.tolist()},
        barmode="group"
    )

    fig_pub.update_layout(
        xaxis_title="Подразделение",
        yaxis_title="Количество публикаций",
        legend_title="Год",
        height=450
    )

    st.plotly_chart(fig_pub, use_container_width=True)

    # --- Фракционный балл ---
    st.subheader(f"{title_prefix}: фракционный балл")

    fig_frac = px.bar(
        filtered,
        x="Подразделение_list",
        y="fractional_score_sum",
        color="ГОД",
        category_orders={"Подразделение_list": order.index.tolist()},
        barmode="group"
    )

    fig_frac.update_layout(
        xaxis_title="Подразделение",
        yaxis_title="Сумма фракционного балла",
        legend_title="Год",
        height=450
    )

    st.plotly_chart(fig_frac, use_container_width=True)


with tab1:
    render_tab(portal_df, "Portal")

with tab2:
    render_tab(scopus_df, "Scopus")


# In[ ]:




