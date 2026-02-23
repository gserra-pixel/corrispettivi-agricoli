import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

st.title("Confronto Corrispettivi - Numbers vs Billy")

numbers_file = st.file_uploader("Carica CSV Numbers (Data, Metodo, Importo)", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    # NUMBERS
    numbers_df = pd.read_csv(numbers_file)
    numbers_df["Data"] = pd.to_datetime(numbers_df["Data"], dayfirst=True)

    # Separiamo per metodo
    contanti_reali = numbers_df[numbers_df["Metodo"] == "Contanti"].groupby("Data")["Importo"].sum()
    pos_reali = numbers_df[numbers_df["Metodo"] == "POS"].groupby("Data")["Importo"].sum()

    numbers_grouped = pd.DataFrame({
        "Contanti_Reale": contanti_reali,
        "POS_Reale": pos_reali
    }).fillna(0).reset_index()

    # BILLY
    billy_df = pd.read_excel(billy_file)
    billy_df["Data"] = pd.to_datetime(billy_df["Data"], dayfirst=True)

    billy_grouped = billy_df.groupby("Data")[["Contanti","POS"]].sum().reset_index()
    billy_grouped.rename(columns={
        "Contanti": "Contanti_Billy",
        "POS": "POS_Billy"
    }, inplace=True)

    # Merge
    confronto = pd.merge(numbers_grouped, billy_grouped, on="Data", how="outer").fillna(0)

    # Differenze
    confronto["Diff_Contanti"] = confronto["Contanti_Reale"] - confronto["Contanti_Billy"]
    confronto["Diff_POS"] = confronto["POS_Reale"] - confronto["POS_Billy"]
    confronto["Diff_Totale"] = confronto["Diff_Contanti"] + confronto["Diff_POS"]

    st.subheader("Tabella Confronto")
    st.dataframe(confronto)

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

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            "Scarica PDF",
            buffer,
            file_name="confronto_corrispettivi.pdf",
            mime="application/pdf"
        )
