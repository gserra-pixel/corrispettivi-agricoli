import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

st.title("Gestione Corrispettivi - Azienda Agricola")

st.write("Carica i tre file CSV per generare il report.")

note_file = st.file_uploader("Carica file NOTE (Data, Metodo, Importo)", type="csv")
sumup_file = st.file_uploader("Carica file SUMUP", type="csv")
billy_file = st.file_uploader("Carica file BILLY", type="csv")

if note_file and sumup_file and billy_file:

    note_df = pd.read_csv(note_file)
    sumup_df = pd.read_csv(sumup_file)
    billy_df = pd.read_csv(billy_file)

    # Standardizza date
    note_df["Data"] = pd.to_datetime(note_df["Data"], dayfirst=True)
    billy_df["Data"] = pd.to_datetime(billy_df["Data"], dayfirst=True)
    sumup_df["Date"] = pd.to_datetime(sumup_df["Date"], dayfirst=True)

    # Totali NOTE
    note_totali = note_df.groupby("Data")["Importo"].sum().reset_index()

    # Totali BILLY
    billy_totali = billy_df.groupby("Data")["Totale"].sum().reset_index()

    # Merge confronto
    confronto = pd.merge(note_totali, billy_totali, on="Data", how="outer")
    confronto = confronto.fillna(0)
    confronto["Differenza"] = confronto["Importo"] - confronto["Totale"]

    st.subheader("Confronto Giornaliero")
    st.dataframe(confronto)

    # Generazione PDF
    if st.button("Genera PDF"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Regime Speciale IVA art.34 DPR 633/72", styles["Normal"]))
        elements.append(Spacer(1, 20))

        for index, row in confronto.iterrows():
            testo = f"""
            Data: {row['Data'].strftime('%d/%m/%Y')}<br/>
            Totale Note: € {row['Importo']:.2f}<br/>
            Totale Billy: € {row['Totale']:.2f}<br/>
            Differenza: € {row['Differenza']:.2f}<br/><br/>
            """
            elements.append(Paragraph(testo, styles["Normal"]))
            elements.append(Spacer(1, 12))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            label="Scarica PDF",
            data=buffer,
            file_name="corrispettivi_report.pdf",
            mime="application/pdf"
        )
