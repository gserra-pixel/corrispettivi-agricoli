import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.title("Registro Corrispettivi - Sottrazione Billy per Data")

numbers_file = st.file_uploader("Carica CSV mercato (Data;Importo)", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    # ======================
    # TUO CSV
    # ======================
    tuo_df = pd.read_csv(numbers_file, sep=None, engine="python")
    tuo_df.columns = tuo_df.columns.str.strip()

    data_col = [c for c in tuo_df.columns if "data" in c.lower()][0]
    importo_col = [c for c in tuo_df.columns if "importo" in c.lower()][0]

    tuo_df["Data"] = pd.to_datetime(tuo_df[data_col], dayfirst=True, errors="coerce")
    tuo_df = tuo_df.dropna(subset=["Data"])
    tuo_df["Data"] = tuo_df["Data"].dt.date

    tuo_df["Importo"] = (
        tuo_df[importo_col]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )
    tuo_df["Importo"] = pd.to_numeric(tuo_df["Importo"], errors="coerce").fillna(0)

    # SOMMA PER DATA
    tuo_totali = tuo_df.groupby("Data")["Importo"].sum().reset_index()
    tuo_totali.rename(columns={"Importo": "Totale_Tuo"}, inplace=True)

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

    billy_totali = billy_df.groupby("Data")["Totale_Billy"].sum().reset_index()

    # ======================
    # MERGE PER DATA
    # ======================
    registro = pd.merge(
        tuo_totali,
        billy_totali,
        on="Data",
        how="left"
    ).fillna(0)

    registro["Da_Registrare"] = registro["Totale_Tuo"] - registro["Totale_Billy"]

    registro = registro.sort_values("Data")

    st.subheader("Riepilogo finale per il PDF")
    st.dataframe(registro)

    # ======================
    # PDF
    # ======================
    if st.button("Genera PDF Registro"):

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Registro Corrispettivi", styles["Heading2"]))
        elements.append(Spacer(1, 20))

        data = [["Data", "Totale Mercato", "Totale Billy", "Da Registrare"]]

        for _, r in registro.iterrows():
            data.append([
                r["Data"].strftime("%d/%m/%Y"),
                f"€ {r['Totale_Tuo']:.2f}",
                f"€ {r['Totale_Billy']:.2f}",
                f"€ {r['Da_Registrare']:.2f}",
            ])

        table = Table(data, hAlign='LEFT')
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        totale_periodo = registro["Da_Registrare"].sum()
        elements.append(Paragraph(f"Totale periodo da registrare: € {totale_periodo:.2f}", styles["Heading2"]))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            "Scarica PDF Registro Corrispettivi",
            buffer,
            file_name="registro_corrispettivi.pdf",
            mime="application/pdf"
        )
