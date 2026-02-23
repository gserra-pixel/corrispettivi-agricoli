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
        # ===== NUMBERS =====
        numbers_df = pd.read_csv(numbers_file, sep=";")
        numbers_df.columns = numbers_df.columns.str.strip()

        numbers_df["Data"] = pd.to_datetime(numbers_df["Data"], dayfirst=True, errors="coerce")
        numbers_df["Importo"] = pd.to_numeric(numbers_df["Importo"], errors="coerce").fillna(0)

        contanti_reali = (
            numbers_df[numbers_df["Metodo"].str.strip().str.lower() == "contanti"]
            .groupby("Data")["Importo"]
            .sum()
        )

        pos_reali = (
            numbers_df[numbers_df["Metodo"].str.strip().str.lower() == "pos"]
            .groupby("Data")["Importo"]
            .sum()
        )

        numbers_grouped = pd.DataFrame({
            "Contanti_Reale": contanti_reali,
            "POS_Reale": pos_reali
        }).fillna(0).reset_index()

        # ===== BILLY =====
        billy_df = pd.read_excel(billy_file)
        billy_df.columns = billy_df.columns.str.strip()

        billy_df["Data"] = pd.to_datetime(billy_df["Data"], dayfirst=True, errors="coerce")

        billy_grouped = (
            billy_df.groupby("Data")[["Contanti", "POS"]]
            .sum()
            .reset_index()
        )

        billy_grouped.rename(columns={
            "Contanti": "Contanti_Billy",
            "POS": "POS_Billy"
        }, inplace=True)

        # ===== MERGE =====
        confronto = pd.merge(
            numbers_grouped,
            billy_grouped,
            on="Data",
            how="outer"
        ).fillna(0)

        # ===== DIFFERENZE =====
        confronto["Diff_Contanti"] = confronto["Contanti_Reale"] - confronto["Contanti_Billy"]
        confronto["Diff_POS"] = confronto["POS_Reale"] - confronto["POS_Billy"]
        confronto["Diff_Totale"] = confronto["Diff_Contanti"] + confronto["Diff_POS"]

        confronto = confronto.sort_values("Data")

        st.subheader("Tabella Confronto")
        st.dataframe(confronto)

        totale_diff = confronto["Diff_Totale"].sum()
        st.subheader(f"Differenza Totale Periodo: € {totale_diff:.2f}")

        # ===== PDF =====
        if st.button("Genera PDF"):

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph("Confronto Corrispettivi Numbers vs Billy", styles["Normal"]))
            elements.append(Spacer(1, 20))

            for _, row in confronto.iterrows():
                testo = f"""
                Data: {row['Data'].strftime('%d/%m/%Y')}<br/>
                Contanti Reali: € {row['Contanti_Reale']:.2f}<br/>
                Contanti Billy: € {row['Contanti_Billy']:.2f}<br/>
                POS Reale: € {row['POS_Reale']:.2f}<br/>
                POS Billy: € {row['POS_Billy']:.2f}<br/>
                Differenza Totale: € {row['Diff_Totale']:.2f}<br/><br/>
                """
                elements.append(Paragraph(testo, styles["Normal"]))
                elements.append(Spacer(1, 12))

            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"Differenza Totale Periodo: € {totale_diff:.2f}", styles["Heading2"]))

            doc.build(elements)
            buffer.seek(0)

            st.download_button(
                "Scarica PDF",
                buffer,
                file_name="confronto_corrispettivi.pdf",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Errore durante l'elaborazione: {e}")
