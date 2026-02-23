import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

st.title("Confronto Totale Mercato vs Billy")

numbers_file = st.file_uploader("Carica CSV tuo totale mercato (Data;Importo)", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    # ===== NUMBERS (TUO TOTALE MERCATO) =====
    numbers_df = pd.read_csv(numbers_file, sep=";")
    numbers_df.columns = numbers_df.columns.str.strip()

    numbers_df["Data"] = pd.to_datetime(numbers_df["Data"], dayfirst=True, errors="coerce").dt.date
    numbers_df["Importo"] = pd.to_numeric(numbers_df["Importo"], errors="coerce").fillna(0)

    numbers_grouped = numbers_df.groupby("Data")["Importo"].sum().reset_index()
    numbers_grouped.rename(columns={"Importo": "Totale_Tuo"}, inplace=True)

    # ===== BILLY =====
    raw_billy = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=None)

    header_row = None
    for i in range(len(raw_billy)):
        if raw_billy.iloc[i].astype(str).str.contains("Data", case=False).any():
            header_row = i
            break

    billy_df = pd.read_excel(
        billy_file,
        sheet_name="Corrispettivi",
        header=header_row
    )

    billy_df.columns = billy_df.columns.str.strip()
    cols = billy_df.columns.str.lower()

    data_col = billy_df.columns[cols.str.contains("data")][0]
    totale_col = billy_df.columns[cols.str.contains("totale")][0]

    billy_df[data_col] = pd.to_datetime(billy_df[data_col], dayfirst=True, errors="coerce").dt.date

    billy_grouped = billy_df.groupby(data_col)[totale_col].sum().reset_index()
    billy_grouped.columns = ["Data", "Totale_Billy"]

    # ===== MERGE =====
    confronto = pd.merge(
        numbers_grouped,
        billy_grouped,
        on="Data",
        how="outer"
    ).fillna(0)

    confronto["Differenza"] = confronto["Totale_Tuo"] - confronto["Totale_Billy"]

    confronto = confronto.sort_values("Data")

    st.subheader("Confronto Giornaliero")
    st.dataframe(confronto)

    totale_diff = confronto["Differenza"].sum()
    st.subheader(f"Differenza Totale Periodo: € {totale_diff:.2f}")

    # ===== PDF =====
    if st.button("Genera PDF"):

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Confronto Totale Mercato vs Billy", styles["Normal"]))
        elements.append(Spacer(1, 20))

        for _, row in confronto.iterrows():
            testo = f"""
            Data: {row['Data'].strftime('%d/%m/%Y')}<br/>
            Totale Tuo: € {row['Totale_Tuo']:.2f}<br/>
            Totale Billy: € {row['Totale_Billy']:.2f}<br/>
            Differenza: € {row['Differenza']:.2f}<br/><br/>
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
            file_name="confronto_totali.pdf",
            mime="application/pdf"
        )
