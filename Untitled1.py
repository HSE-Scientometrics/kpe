import pandas as pd
import streamlit as st
import plotly.express as px
from io import StringIO

# --------------------------------------------------
# Функция безопасной загрузки CSV
# --------------------------------------------------

def load_csv_safely(uploaded_file):
    encodings = ["utf-8-sig", "utf-8", "cp1251", "windows-1251"]

    for enc in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=";", encoding=enc)
            st.success(f"Файл успешно прочитан с кодировкой: {enc}")
            return df
        except UnicodeDecodeError:
            continue

    # если ничего не сработало — читаем как байты и игнорируем ошибки
    uploaded_file.seek(0)
    raw = uploaded_file.read().decode("utf-8", errors="ignore")
    df = pd.read_csv(StringIO(raw), sep=";")
    st.warning("⚠️ Кодировка определена с игнорированием ошибок (errors='ignore')")
    return df

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

REQUIRED_COLUMNS = [
    "Список НИУ ВШЭ",
    "Рец тип строгий",
    "ГОД",
    "Подразделение (широко)",
    "НАЗВАНИЕ",
    "Фракционный балл",
    "Тип (по Portal)",
    "Тип (по Scopus)"
]

# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.set_page_config(
    page_title="Диагностика реестра НИУ ВШЭ",
    layout="wide"
)

st.title("Диагностика и визуализация реестра НИУ ВШЭ")

uploaded_file = st.file_uploader(
    "Загрузите CSV-файл реестра (разделитель ;)",
    type=["csv"]
)

if uploaded_file is None:
    st.info("⬆️ Сначала загрузите CSV-файл")
    st.stop()

# --------------------------------------------------
# Загрузка файла (с диагностикой)
# --------------------------------------------------

st.subheader("1️⃣ Загрузка файла")

try:
    reestr = load_csv_safely(uploaded_file)
    st.success("Файл успешно прочитан")
except Exception as e:
    st.error("❌ Ошибка при чтении CSV")
    st.exception(e)
    st.stop()

st.write("Первые строки файла:")
st.dataframe(reestr.head())

# --------------------------------------------------
# Проверка колонок
# --------------------------------------------------

st.subheader("2️⃣ Проверка структуры файла")

st.write("Найденные колонки:")
st.code(reestr.columns.tolist())

missing_cols = [c for c in REQUIRED_COLUMNS if c not in reestr.columns]

if missing_cols:
    st.error("❌ В файле отсутствуют обязательные колонки:")
    st.code(missing_cols)
    st.stop()
else:
    st.success("Все необходимые колонки присутствуют")

# --------------------------------------------------
# Подготовка данных
# --------------------------------------------------

st.subheader("3️⃣ Применение фильтров методики")

try:
    reestr = reestr[
        (reestr["Список НИУ ВШЭ"].isin(HSE_LIST_ALLOWED)) &
        (reestr["Рец тип строгий"] == 1)
    ]
    st.success(f"После фильтрации осталось строк: {len(reestr)}")
except Exception as e:
    st.error("❌ Ошибка при фильтрации")
    st.exception(e)
    st.stop()

# --------------------------------------------------
# Проверка годов
# --------------------------------------------------

st.subheader("4️⃣ Проверка колонки ГОД")

try:
    st.write("Уникальные годы:", sorted(reestr["ГОД"].unique()))
    max_year = reestr["ГОД"].max()
    reestr = reestr[reestr["ГОД"] >= max_year - 2]
    st.success(f"Используются годы: {sorted(reestr['ГОД'].unique())}")
except Exception as e:
    st.error("❌ Проблема с колонкой ГОД")
    st.exception(e)
    st.stop()

# --------------------------------------------------
# Подразделения
# --------------------------------------------------

st.subheader("5️⃣ Разбор подразделений")

try:
    reestr["Подразделение_list"] = (
        reestr["Подразделение (широко)"]
        .fillna("")
        .apply(lambda x: [i.strip() for i in x.split(";") if i.strip()])
    )
    st.success("Подразделения успешно разобраны")
except Exception as e:
    st.error("❌ Ошибка при разборе подразделений")
    st.exception(e)
    st.stop()

# --------------------------------------------------
# Взрыв + фракционный балл
# --------------------------------------------------

st.subheader("6️⃣ Фракционный учёт")

try:
    reestr = reestr.explode("Подразделение_list")

    div_cnt = (
        reestr.groupby("НАЗВАНИЕ")["Подразделение_list"]
        .transform("count")
    )

    reestr["fractional_score_adj"] = reestr["Фракционный балл"] / div_cnt
    st.success("Фракционный балл рассчитан")
except Exception as e:
    st.error("❌ Ошибка при расчёте фракционного балла")
    st.exception(e)
    st.stop()

# --------------------------------------------------
# Агрегации
# --------------------------------------------------

st.subheader("7️⃣ Агрегации")

try:
    portal_df = (
        reestr[reestr["Тип (по Portal)"].isin(PORTAL_TYPES)]
        .groupby(["ГОД", "Подразделение_list"], as_index=False)
        .agg(
            publications_cnt=("НАЗВАНИЕ", "nunique"),
            fractional_score_sum=("fractional_score_adj", "sum")
        )
    )

    scopus_df = (
        reestr[reestr["Тип (по Scopus)"].isin(SCOPUS_TYPES)]
        .groupby(["ГОД", "Подразделение_list"], as_index=False)
        .agg(
            publications_cnt=("НАЗВАНИЕ", "nunique"),
            fractional_score_sum=("fractional_score_adj", "sum")
        )
    )

    st.success("Агрегации построены")
except Exception as e:
    st.error("❌ Ошибка при агрегациях")
    st.exception(e)
    st.stop()

# --------------------------------------------------
# Графики
# --------------------------------------------------

st.subheader("8️⃣ Графики")

def draw_charts(df, title):
    order = (
        df.groupby("Подразделение_list")["publications_cnt"]
        .sum()
        .sort_values(ascending=False)
        .index
    )

    fig_pub = px.bar(
        df,
        x="Подразделение_list",
        y="publications_cnt",
        color="ГОД",
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{title}: публикации"
    )

    fig_frac = px.bar(
        df,
        x="Подразделение_list",
        y="fractional_score_sum",
        color="ГОД",
        category_orders={"Подразделение_list": order},
        barmode="group",
        title=f"{title}: фракционный балл"
    )

    st.plotly_chart(fig_pub, use_container_width=True)
    st.plotly_chart(fig_frac, use_container_width=True)

tab1, tab2 = st.tabs(["Portal", "Scopus"])

with tab1:
    draw_charts(portal_df, "Portal")

with tab2:
    draw_charts(scopus_df, "Scopus")

st.success("✅ Приложение отработало без ошибок")
