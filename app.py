import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.title("Registro Corrispettivi - Mercato vs Billy")

numbers_file = st.file_uploader("Carica CSV mercato", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    # ======================
    # LETTURA CSV ROBUSTA
    # ======================
    tuo_df = pd.read_csv(numbers_file, sep=None, engine="python")
    tuo_df.columns = tuo_df.columns.str.strip()

    st.write("DEBUG - CSV letto così:")
    st.dataframe(tuo_df)

    # Normalizziamo nomi colonne
    col_lower = tuo_df.columns.str.lower()

    data_col = tuo_df.columns[col_lower.str.contains("data")][0]
    importo_col = tuo_df.columns[col_lower.str.contains("importo")][0]
    aliquota_col = tuo_df.columns[col_lower.str.contains("aliquota")][0]

    # Pulizia numeri (gestisce 580,00 o 580.00)
    tuo_df[importo_col] = (
        tuo_df[importo_col]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    tuo_df[aliquota_col] = (
        tuo_df[aliquota_col]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    tuo_df["Data"] = pd.to_datetime(tuo_df[data_col], dayfirst=True, errors="coerce")
    tuo_df = tuo_df.dropna(subset=["Data"])
    tuo_df["Data"] = tuo_df["Data"].dt.date

    tuo_df["Importo"] = pd.to_numeric(tuo_df[importo_col], errors="coerce").fillna(0)
    tuo_df["Aliquota"] = pd.to_numeric(tuo_df[aliquota_col], errors="coerce").fillna(0)

    # Calcolo IVA
    tuo_df["Imponibile"] = tuo_df["Importo"] / (1 + tuo_df["Aliquota"] / 100)
    tuo_df["IVA"] = tuo_df["Importo"] - tuo_df["Imponibile"]

    tuo_grouped = (
        tuo_df.groupby(["Data", "Aliquota"])
        .sum(numeric_only=True)
        .reset_index()
    )

    # ======================
    # BILLY
    # ======================
    raw = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=None)

    header_row = None
    for i in range(len(raw)):
        if raw.iloc[i].astype(str).str.contains("Data", case=False).any():
            header_row = i
            break

    billy_df = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=header_row)
    billy_df.columns = billy_df.columns.str.strip()

    billy_df["Data"] = pd.to_datetime(billy_df["Data"], dayfirst=True, errors="coerce")
    billy_df = billy_df.dropna(subset=["Data"])
    billy_df["Data"] = billy_df["Data"].dt.date

    cols_lower = billy_df.columns.str.lower()

    contanti_col = billy_df.columns[cols_lower.str.contains("contanti")][0]
    elettronico_col = billy_df.columns[cols_lower.str.contains("elettron")][0]

    billy_df[contanti_col] = pd.to_numeric(billy_df[contanti_col], errors="coerce").fillna(0)
    billy_df[elettronico_col] = pd.to_numeric(billy_df[elettronico_col], errors="coerce").fillna(0)

    billy_df["Totale_Billy"] = billy_df[contanti_col] + billy_df[elettronico_col]

    billy_grouped = (
        billy_df.groupby("Data")["Totale_Billy"]
        .sum()
        .reset_index()
    )

    # ======================
    # MERGE
    # ======================
    reg = pd.merge(tuo_grouped, billy_grouped, on="Data", how="left").fillna(0)

    reg["Da_Registrare"] = reg["Importo"] - reg["Totale_Billy"]
    reg = reg.sort_values("Data")

    st.subheader("Riepilogo")
    st.dataframe(reg)
