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
    # BILLY - TROVA HEADER AUTOMATICO
    # =========================
    raw_billy = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=None)

    header_row = None
    for i in range(len(raw_billy)):
        if raw_billy.iloc[i].astype(str).str.contains("Data", case=False).any():
            header_row = i
            break

    if header_row is None:
        st.error("Non riesco a trovare la riga intestazione nel file Billy.")
        st.stop()

    billy_df = pd.read_excel(
        billy_file,
        sheet_name="Corrispettivi",
        header=header_row
    )

    billy_df.columns = billy_df.columns.str.strip()
    cols = billy_df.columns.str.lower()

    # Trova colonne dinamicamente
    data_col = billy_df.columns[cols.str.contains("data")][0]
    contanti_col = billy_df.columns[cols.str.contains("contanti")][0]
    elettronico_col = billy_df.columns[cols.str.contains("elettron")][0]

    billy_df[data_col] = pd.to_datetime(billy_df[data_col], dayfirst=True, errors="coerce")

    billy_grouped = (
        billy_df.groupby(data_col)[[contanti_col, elettronico_col]]
        .sum()
        .reset_index()
    )

    billy_grouped.columns = [
        "Data",
        "Contanti_Billy",
        "POS_Billy"
    ]

    # Ricalcolo totale
    billy_grouped["Totale_Billy"] = (
        billy_grouped["Contanti_Billy"] + billy_grouped["POS_Billy"]
    )

    # =========================
    # MERGE
    # =========================
    confronto = pd.merge(
        numbers_grouped,
        billy_grouped,
        on="Data",
        how="outer"
    ).fillna(0)

    confronto["Diff_Contanti"] = confronto["Contanti_Reale"] - confronto["Contanti_Billy"]
    confronto["Diff_POS"] = confronto["POS_Reale"] - confronto["POS_Billy"]
    confronto["Diff_Totale"] = confronto["Diff_Contanti"] + confronto["Diff_POS"]

    confronto = confronto.sort_values("Data")

    st.subheader("Tabella Confronto")
    st.dataframe(confronto)

    totale_diff = confronto["Diff_Totale"].sum()
    st.subheader(f"Differenza Totale Periodo: € {totale_diff:.2f}")

    # =========================
    # PDF
    # =========================
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
            Totale Billy: € {row['Totale_Billy']:.2f}<br/>
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
