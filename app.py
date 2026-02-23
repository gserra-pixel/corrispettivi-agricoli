import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

st.title("Report Corrispettivi da Billy")

file = st.file_uploader("Carica file XLSX di Billy", type=["xlsx"])

if file:

    df = pd.read_excel(file)

    # Assumiamo colonne: Data, Totale, POS, Contanti
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True)

    giornaliero = df.groupby("Data")[["Totale","POS","Contanti"]].sum().reset_index()

    totale_mese = giornaliero["Totale"].sum()

    st.subheader("Riepilogo Giornaliero")
    st.dataframe(giornaliero)

    st.subheader(f"Totale Periodo: € {totale_mese:.2f}")

    if st.button("Genera PDF"):

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Regime Speciale IVA art.34 DPR 633/72", styles["Normal"]))
        elements.append(Spacer(1, 20))

        for _, row in giornaliero.iterrows():
            testo = f"""
            Data: {row['Data'].strftime('%d/%m/%Y')}<br/>
            Totale: € {row['Totale']:.2f}<br/>
            POS: € {row['POS']:.2f}<br/>
            Contanti: € {row['Contanti']:.2f}<br/><br/>
            """
            elements.append(Paragraph(testo, styles["Normal"]))
            elements.append(Spacer(1, 12))

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Totale Periodo: € {totale_mese:.2f}", styles["Heading2"]))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            "Scarica PDF",
            buffer,
            file_name="corrispettivi_billy.pdf",
            mime="application/pdf"
        )
