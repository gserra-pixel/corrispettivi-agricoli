import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

st.title("Confronto Corrispettivi - Numbers vs Billy")

numbers_file = st.file_uploader("Carica CSV Numbers (Data;Metodo;Importo)", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    try:
        # =========================
        # NUMBERS
        # =========================
        numbers_df = pd.read_csv(numbers_file, sep=";")
        numbers_df.columns = numbers_df.columns.str.strip()

        numbers_df["Data"] = pd.to_datetime(numbers_df["Data"], dayfirst=True, errors="coerce")
        numbers_df["Importo"] = pd.to_numeric(numbers_df["Importo"], errors="coerce").fillna(0)

        contanti_reali = (
            numbers_df[numbers_df["Metodo"].str.lower().str.strip() == "contanti"]
            .groupby("Data")["Importo"]
            .sum()
        )

        pos_reali = (
            numbers_df[numbers_df["Metodo"].str.lower().str.strip() == "pos"]
            .groupby("Data")["Importo"]
            .sum()
        )

        numbers_grouped = pd.DataFrame({
            "Contanti_Reale": contanti_reali,
            "POS_Reale": pos_reali
        }).fillna(0).reset_index()

        # =========================
        # BILLY - HEADER AUTOMATICO
        # =========================
        # Leggiamo senza header per trovare la riga giusta
        raw_billy = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=None)

        header_row = None
        for i in range(len(raw_billy)):
            row_values = raw_billy.iloc[i].astype(str).str.strip()
            if "Data" in row_values.values:
                header_row = i
                break

        if header_row is None:
            st.error("Non riesco a trovare la riga con 'Data' nel file Billy.")
            st.stop()

        billy_df = pd.read_excel(
            billy_file,
            sheet_name="Corrispettivi",
            header=header_row
        )

        billy_df.columns = billy_df.columns.str.strip()

        billy_df["Data"] = pd.to_datetime(billy_df["Data"], dayfirst=True, errors="coerce")

        billy_grouped = (
            billy_df.groupby("Data")[["Contanti", "Elettronico", "Totale lordo"]]
            .sum()
            .reset_index()
        )

        billy_grouped.rename(columns={
            "Contanti": "Contanti_Billy",
            "Elettronico": "POS_Billy",
            "Totale lordo": "Totale_Billy"
        }, inplace=True)

        # =================
