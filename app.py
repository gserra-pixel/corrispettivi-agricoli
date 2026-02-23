import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

st.title("Registro Corrispettivi - Versione Completa")

numbers_file = st.file_uploader("Carica CSV mercato (Data;Importo;Aliquota)", type=["csv"])
billy_file = st.file_uploader("Carica XLSX Billy", type=["xlsx"])

if numbers_file and billy_file:

    # ======================
    # TUO CSV
    # ======================
    tuo_df = pd.read_csv(numbers_file, sep=None, engine="python")
    tuo_df.columns = tuo_df.columns.str.strip()

    data_col = [c for c in tuo_df.columns if "data" in c.lower()][0]
    importo_col = [c for c in tuo_df.columns if "importo" in c.lower()][0]
    aliquota_col = [c for c in tuo_df.columns if "aliquota" in c.lower()][0]

    tuo_df[data_col] = tuo_df[data_col].astype(str).str.strip()

    def fix_year(d):
        if "/" in d:
            parts = d.split("/")
            if len(parts[-1]) == 2:
                giorno, mese, anno = parts
                anno = "20" + anno
                return f"{giorno}/{mese}/{anno}"
        return d

    tuo_df[data_col] = tuo_df[data_col].apply(fix_year)

    tuo_df["Data"] = pd.to_datetime(tuo_df[data_col], dayfirst=True, errors="coerce")
    tuo_df = tuo_df.dropna(subset=["Data"])
    tuo_df["Data"] = tuo_df["Data"].dt.date

    tuo_df["Importo"] = (
        tuo_df[importo_col]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )
    tuo_df["Importo"] = pd.to_numeric(tuo_df["Importo"], errors="coerce").fillna(0)
    tuo_df["Aliquota"] = pd.to_numeric(tuo_df[aliquota_col], errors="coerce").fillna(0)

    totale_giorno = tuo_df.groupby("Data")["Importo"].sum().reset_index()
    totale_giorno.rename(columns={"Importo": "Totale_Tuo_Giorno"}, inplace=True)

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
    billy_totale = billy_df.groupby("Data")["Totale_Billy"].sum().reset_index()

    giorni = totale_giorno.merge(billy_totale, on="Data", how="left").fillna(0)
    giorni["Residuo_Giorno"] = giorni["Totale_Tuo_Giorno"] - giorni["Totale_Billy"]

    registro = tuo_df.merge(giorni[["Data", "Totale_Tuo_Giorno", "Residuo_Giorno"]], on="Data")

    registro["Quota"] = registro["Importo"] / registro["Totale_Tuo_Giorno"]
    registro["Lordo_Residuo"] = registro["Residuo_Giorno"] * registro["Quota"]

    registro["Imponibile"] = registro["Lordo_Residuo"] / (1 + registro["Aliquota"] / 100)
    registro["IVA"] = registro["Lordo_Residuo"] - registro["Imponibile"]

    registro = registro.sort_values(["Data", "Aliquota"])

    # ======================
    # RIEPILOGO PER ALIQUOTA
    # ======================
    riepilogo_aliquota = registro.groupby("Aliquota").agg({
        "Lordo_Residuo": "sum",
        "Imponibile": "sum",
        "IVA": "sum"
    }).reset_index()

    st.subheader("Dettaglio Giornaliero")
    st.dataframe(registro)

    st.subheader("Riepilogo IVA per Aliquota")
    st.dataframe(riepilogo_aliquota)

    # ======================
    # PDF
    # ======================
    if st.button("Genera PDF Registro"):

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("AZIENDA AGRICOLA PEDRA E LUNA", styles["Heading1"]))
        elements.append(Paragraph("Registro Corrispettivi - Regime Speciale Art.34 DPR 633/72", styles["Normal"]))
        elements.append(Spacer(1, 20))

        data = [["Data", "Aliquota", "Lordo Residuo", "Imponibile", "IVA"]]

        for _, r in registro.iterrows():
            data.append([
                r["Data"].strftime("%d/%m/%Y"),
                f"{int(r['Aliquota'])}%",
                f"€ {r['Lordo_Residuo']:.2f}",
                f"€ {r['Imponibile']:.2f}",
                f"€ {r['IVA']:.2f}",
            ])

        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("RIEPILOGO IVA PER ALIQUOTA", styles["Heading2"]))
        elements.append(Spacer(1, 10))

        data2 = [["Aliquota", "Totale Lordo", "Imponibile", "IVA"]]

        for _, r in riepilogo_aliquota.iterrows():
            data2.append([
                f"{int(r['Aliquota'])}%",
                f"€ {r['Lordo_Residuo']:.2f}",
                f"€ {r['Imponibile']:.2f}",
                f"€ {r['IVA']:.2f}",
            ])

        table2 = Table(data2)
        table2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ]))

        elements.append(table2)

        totale_periodo = registro["Lordo_Residuo"].sum()

        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Totale periodo da registrare: € {totale_periodo:.2f}", styles["Heading2"]))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            "Scarica PDF Registro Completo",
            buffer,
            file_name="registro_corrispettivi_completo.pdf",
            mime="application/pdf"
        )
