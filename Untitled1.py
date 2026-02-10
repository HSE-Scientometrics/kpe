import pandas as pd

# ---------------------
# Загрузка CSV
# ---------------------
file_path = "НЦ_Ежеквартальный_реестр_2025_IV_квартал_полный.csv"
encodings = ["utf-8-sig", "utf-8", "cp1251", "windows-1251"]

for enc in encodings:
    try:
        df = pd.read_csv(file_path, sep=";", encoding=enc)
        print(f"Файл успешно прочитан с кодировкой: {enc}")
        break
    except Exception as e:
        continue
else:
    from io import StringIO
    with open(file_path, "rb") as f:
        raw = f.read().decode("utf-8", errors="ignore")
    df = pd.read_csv(StringIO(raw), sep=";")
    print("Кодировка определена с игнорированием ошибок")

# ---------------------
# Преобразование фракционного балла
# ---------------------
df["Фракционный балл"] = pd.to_numeric(df["Фракционный балл"], errors="coerce").fillna(0)

# ---------------------
# Фильтрация по Список НИУ ВШЭ и Рец тип строгий
# ---------------------
HSE_LIST_ALLOWED = ["A", "B", "A_Book", "A_Conf"]
df = df[df["Список НИУ ВШЭ"].isin(HSE_LIST_ALLOWED)]
df = df[df["Рец тип строгий"] == 1]

# ---------------------
# Разбор подразделений
# ---------------------
df["Подразделение_list"] = df["Подразделение (широко)"].fillna("").apply(
    lambda x: [i.strip() for i in x.split(";") if i.strip()]
)
df = df.explode("Подразделение_list")

# ---------------------
# Убираем подразделения с 'nan' и пустые
# ---------------------
df["Подразделение_list"] = df["Подразделение_list"].astype(str)
df = df[df["Подразделение_list"].str.lower() != "nan"]
df = df[df["Подразделение_list"] != ""]

# ---------------------
# Последние 3 года
# ---------------------
last_three_years = df["ГОД"].max() - 2
df = df[df["ГОД"] >= last_three_years]

# ---------------------
# Таблица 1: Тип (по Portal)
# ---------------------
PORTAL_TYPES = ["Статья", "Труды конференций", "Монографии", 
                "Учебные пособия", "Учебники", "Сборники статей"]

portal_df = df[df["Тип (по Portal)"].isin(PORTAL_TYPES)]

portal_agg = portal_df.groupby(
    ["ГОД", "Подразделение_list"], as_index=False
).agg(
    publications_cnt=('НАЗВАНИЕ', 'nunique'),
    fractional_score_sum=('Фракционный балл', 'sum')
).sort_values(['ГОД', 'publications_cnt'], ascending=[False, False]).reset_index(drop=True)

# ---------------------
# Таблица 2: Тип (по Scopus)
# ---------------------
SCOPUS_TYPES = ["Article", "Conference Paper", "Book"]

scopus_df = df[df["Тип (по Scopus)"].isin(SCOPUS_TYPES)]

scopus_agg = scopus_df.groupby(
    ["ГОД", "Подразделение_list"], as_index=False
).agg(
    publications_cnt=('НАЗВАНИЕ', 'nunique'),
    fractional_score_sum=('Фракционный балл', 'sum')
).sort_values(['ГОД', 'publications_cnt'], ascending=[False, False]).reset_index(drop=True)

# ---------------------
# Вывод
# ---------------------
print("Таблица по Portal:")
display(portal_agg.head(20))

print("Таблица по Scopus:")
display(scopus_agg.head(20))
