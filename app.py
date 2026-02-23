import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.title("Registro Corrispettivi - Calcolo IVA da CSV")

numbers_file = st.file_uploader("Carica CSV tuo mercato (Data;Importo;Aliquota)", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    # ===== TUO CSV =====
    tuo_df = pd.read_csv(numbers_file, sep=";")
    tuo_df.columns = tuo_df.columns.str.strip()

    tuo_df["Data"] = pd.to_datetime(tuo_df["Data"], dayfirst=True).dt.date
    tuo_df["Importo"] = pd.to_numeric(tuo_df["Importo"], errors="coerce").fillna(0)
    tuo_df["Aliquota"] = pd.to_numeric(tuo_df["Aliquota"], errors="coerce").fillna(0)

    # Calcolo imponibile e IVA
    tuo_df["Imponibile"] = tuo_df["Importo"] / (1 + tuo_df["Aliquota"] / 100)
    tuo_df["IVA"] = tuo_df["Importo"] - tuo_df["Imponibile"]

    tuo_grouped = tuo_df.groupby(["Data", "Aliquota"]).sum(numeric_only=True).reset_index()

    # ===== BILLY =====
    raw = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=None)

    header_row = None
    for i in range(len(raw)):
        if raw.iloc[i].astype(str).str.contains("Data", case=False).any():
            header_row = i
            break

    billy_df = pd.read_excel(billy_file, sheet_name="Corrispettivi", header=header_row)
    billy_df.columns = billy_df.columns.str.strip()

    billy_df["Data"] = pd.to_datetime(billy_df["Data"], dayfirst=True).dt.date
    totale_col = [c for c in billy_df.columns if "totale" in c.lower()][0]

    billy_grouped = billy_df.groupby("Data")[totale_col].sum().reset_index()
    billy_grouped.rename(columns={totale_col: "Totale_Billy"}, inplace=True)

    # ===== MERGE =====
    reg = pd.merge(tuo_grouped, billy_grouped, on="Data", how="left").fillna(0)

    reg["Corrispettivo_Lordo"] = reg["Importo"] - reg["Totale_Billy"]

    st.subheader("Riepilogo")
    st.dataframe(reg)

    # ===== PDF =====
    if st.button("Genera PDF Registro"):

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Registro Corrispettivi", styles["Heading2"]))
        elements.append(Spacer(1, 20))

        data = [["Data", "Aliquota %", "Lordo", "Imponibile", "IVA", "Billy", "Da Registrare"]]

        for _, r in reg.iterrows():
            data.append([
                r["Data"].strftime("%d/%m/%Y"),
                f"{int(r['Aliquota'])}%",
                f"€ {r['Importo']:.2f}",
                f"€ {r['Imponibile']:.2f}",
                f"€ {r['IVA']:.2f}",
                f"€ {r['Totale_Billy']:.2f}",
                f"€ {r['Corrispettivo_Lordo']:.2f}",
            ])

        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        totale_periodo = reg["Corrispettivo_Lordo"].sum()
        elements.append(Paragraph(f"Totale periodo da registrare: € {totale_periodo:.2f}", styles["Heading2"]))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            "Scarica PDF Registro Corrispettivi",
            buffer,
            file_name="registro_corrispettivi.pdf",
            mime="application/pdf"
        )
