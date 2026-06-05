import io, base64
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from PIL import Image as PILImage
import config

PDF_MODULO1    = "Annuncio Imposte alla Fonte 1 - 2024.pdf"
PDF_MODULO1A   = "1A_Attestazione_statuto_vecchio_frontaliere_in_caso_di_assunzione_dal_18072023_vecchio_frontaliere.pdf"
PDF_MODULO1908 = "Modulo - Formulario 1908 - Dati personali del collaboratore.pdf"


def _firma_pil(firma_b64: str) -> PILImage.Image:
    data = base64.b64decode(firma_b64.split(",")[1])
    return PILImage.open(io.BytesIO(data))


def _overlay(page_w, page_h, elementi) -> PdfReader:
    import tempfile, os
    packet = io.BytesIO()
    c = rl_canvas.Canvas(packet, pagesize=(page_w, page_h))
    tmp_files = []
    for el in elementi:
        if el["tipo"] == "testo" and el.get("testo"):
            c.setFont("Helvetica", el.get("size", 8))
            c.drawString(float(el["x"]), float(el["y"]), str(el["testo"]))
        elif el["tipo"] == "firma" and el.get("b64"):
            try:
                data = base64.b64decode(el["b64"].split(",")[1])
                img = PILImage.open(io.BytesIO(data))
                # Salva su file temporaneo perché reportlab non accetta BytesIO
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.save(tmp.name, format="PNG")
                tmp.close()
                tmp_files.append(tmp.name)
                c.drawImage(tmp.name, el["x"], el["y"],
                            width=el["w"], height=el["h"], mask="auto")
            except Exception as e:
                pass
    c.save()
    # Pulisci file temporanei
    for f in tmp_files:
        try:
            os.unlink(f)
        except Exception:
            pass
    packet.seek(0)
    return PdfReader(packet)


def _t(x, y, testo, size=8):
    return {"tipo": "testo", "x": x, "y": y, "testo": testo, "size": size}


def _x(cx, cy, size=7):
    return {"tipo": "testo", "x": cx - 2.5, "y": cy - 3, "testo": "X", "size": size}


def _f(x, y, w, h, b64):
    return {"tipo": "firma", "x": x, "y": y, "w": w, "h": h, "b64": b64}


def _fmt(d: str) -> str:
    if not d:
        return ""
    d = str(d).strip()
    if len(d) == 10 and d[4] == "-":
        try:
            y, m, g = d.split("-")
            return f"{g}/{m}/{y}"
        except Exception:
            return d
    return d


def _si(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ("si", "sì", "yes", "true", "1")
    return bool(v)


# ═══════════════════════════════════════════════════════════════
# MODULO 1
# ═══════════════════════════════════════════════════════════════
def genera_modulo1(dati: dict, firma_b64: str) -> bytes:
    reader = PdfReader(PDF_MODULO1)
    writer = PdfWriter()
    writer.append(reader)

    W, H = 595.28, 841.89

    # ── PAGINA 1 ──
    el_p1 = [
        _t(223.6, 478.6, dati.get("cognome", "")),
        _t(224.0, 461.7, dati.get("nome", "")),
        _t(224.2, 446.0, _fmt(dati.get("data_nascita", ""))),
        _t(224.4, 357.6, dati.get("numero_avs", "")),
        _t(430.1, 394.1, _fmt(dati.get("permesso_rilascio", ""))),
        _t(223.5, 50.2,  _fmt(dati.get("permesso_rilascio", ""))),
        _t(224.0, 303.0, dati.get("domicilio_via", "")),
        _t(223.9, 236.1, f"{dati.get('domicilio_cap','')} {dati.get('domicilio_localita','')}".strip()),
        _t(223.4, 219.7, dati.get("luogo_nascita", "")),
        _t(223.4, 202.0, dati.get("codice_fiscale", "")),
        _t(223.9, 185.7, dati.get("cellulare", "")),
    ]

    # Sesso
    if dati.get("sesso") == "Maschile":
        el_p1.append(_x(422.3, 450.6))
    else:
        el_p1.append(_x(517.5, 450.6))

    # Permesso
    mappa_perm = {
        "B (Dimora)":              (228.6, 432.7),
        "G (Frontaliere)":         (322.5, 432.9),
        "L (Dimora breve durata)": (421.3, 432.7),
        "Solo notifica":           (228.4, 416.8),
        "No, svizzero/a":          (322.5, 415.8),
        "Nessun permesso":         (322.5, 415.8),
    }
    if dati.get("permesso") in mappa_perm:
        el_p1.append(_x(*mappa_perm[dati["permesso"]]))

    # Rientro
    if dati.get("rientro") == "Rientro giornaliero":
        el_p1.append(_x(228.8, 381.4))
    elif dati.get("rientro") == "Rientro settimanale":
        el_p1.append(_x(322.5, 381.8))

    # Nazione domicilio
    mappa_naz = {
        "Italia":                       (228.8, 344.4),
        "Italia (Comuni di Frontiera)": (322.5, 344.4),
        "Francia":                      (422.3, 343.6),
        "Svizzera":                     (517.9, 344.0),
        "Germania":                     (228.8, 327.0),
        "Austria":                      (322.5, 325.8),
        "Altra":                        (422.3, 326.6),
    }
    if dati.get("domicilio_nazione") in mappa_naz:
        el_p1.append(_x(*mappa_naz[dati["domicilio_nazione"]]))

    # Stato civile
    mappa_sc = {
        "Celibe/Nubile":                (229.1, 73.0),
        "Coniugato/Partner registrato": (304.4, 73.4),
        "Vedovo":                       (422.3, 72.6),
        "Separato/Separato di fatto":   (422.3, 72.6),
        "Divorziato":                   (422.3, 72.6),
    }
    if dati.get("stato_civile") in mappa_sc:
        el_p1.append(_x(*mappa_sc[dati["stato_civile"]]))

    # Convivenza
    if _si(dati.get("convivenza")):
        el_p1.append(_x(305.1, 40.1))
    else:
        el_p1.append(_x(352.0, 40.5))

    layer1 = _overlay(W, H, el_p1)
    writer.pages[0].merge_page(layer1.pages[0])

    # ── PAGINA 2 ──
    el_p2 = [
        # Coniuge
        _t(224.0, 769.6, dati.get("coniuge_cognome", "")),
        _t(224.0, 752.7, dati.get("coniuge_nome", "")),
        _t(223.7, 736.7, _fmt(dati.get("coniuge_nascita", ""))),
        _t(439.5, 735.7, dati.get("coniuge_avs", "")),
        # Dati professionali
        _t(267.1, 296.7, _fmt(dati.get("data_inizio", ""))),
        _t(478.1, 296.7, _fmt(dati.get("data_fine", ""))),
        _t(375.4, 244.6, str(dati.get("grado_occupazione", ""))),
        _t(375.9, 229.4, str(dati.get("grado_occupazione", ""))),
        # Data e luogo — campo rect [92,34.6,264.9,50.5]
        _t(92.0, 36.6, f"Manno, {_fmt(dati.get('data_firma', ''))}"),
    ]

    # Coniuge lavora
    if _si(dati.get("coniuge_lavora")):
        el_p2.append(_x(157.3, 605.1))
    else:
        el_p2.append(_x(189.8, 605.1))

    # Rendite
    if _si(dati.get("altre_attivita")):
        el_p2.append(_x(469.9, 265.4))
    else:
        el_p2.append(_x(543.2, 265.4))

    # Nazione coniuge
    mappa_naz_con = {
        "Italia":                       (229.5, 723.8),
        "Italia (Comuni di Frontiera)": (326.3, 723.4),
        "Francia":                      (423.4, 724.2),
        "Svizzera":                     (519.8, 724.2),
        "Germania":                     (229.5, 708.3),
        "Austria":                      (325.9, 708.0),
        "Altra":                        (423.4, 708.0),
    }
    if dati.get("coniuge_nazione", "Italia") in mappa_naz_con:
        el_p2.append(_x(*mappa_naz_con[dati.get("coniuge_nazione", "Italia")]))

    # Reddito coniuge in CH/estero
    if _si(dati.get("coniuge_lavora")):
        if _si(dati.get("coniuge_lavora_ch")):
            el_p2.append(_x(156.9, 572.3))
        else:
            el_p2.append(_x(325.9, 573.0))

    # Convivenza sezione 4
    if _si(dati.get("convivenza")):
        if _si(dati.get("figli_convivenza")):
            el_p2.append(_x(394.7, 525.0))
        else:
            el_p2.append(_x(427.6, 525.8))
        ap = dati.get("autorita_parentale", "No")
        if ap in ("Si", "Sì"):
            el_p2.append(_x(326.1, 509.9))
        elif ap in ("Si congiunta", "Sì congiunta"):
            el_p2.append(_x(366.7, 509.5))
        else:
            el_p2.append(_x(427.6, 509.1))
        if _si(dati.get("reddito_maggiore")):
            el_p2.append(_x(395.1, 491.8))
        else:
            el_p2.append(_x(427.6, 492.1))

    # Figli
    y_figli = [427.3, 411.3, 393.7, 376.7, 359.8, 343.1]
    x_cols  = [
        (23.4,  237.7, 357.6, 477.6),
        (23.2,  237.9, 357.6, 477.6),
        (23.2,  238.3, 357.1, 478.1),
        (23.3,  238.5, 357.6, 477.6),
        (23.5,  238.5, 357.1, 477.6),
        (23.2,  238.0, 357.6, 478.5),
    ]
    for i, f in enumerate(dati.get("figli", [])[:6]):
        y = y_figli[i]
        xn, xd, xi, xf = x_cols[i]
        el_p2 += [
            _t(xn, y, f.get("nome", "")),
            _t(xd, y, _fmt(f.get("nascita", ""))),
            _t(xi, y, _fmt(f.get("inizio", ""))),
            _t(xf, y, _fmt(f.get("fine", ""))),
        ]

    # Firma — "Firma del dipendente" è a PDF_y=94.2, campo firma subito sotto
    # Posizioniamo la firma a destra della pagina, y circa 60-90
    if firma_b64:
        el_p2.append(_f(310, 55, 150, 35, firma_b64))

    layer2 = _overlay(W, H, el_p2)
    writer.pages[1].merge_page(layer2.pages[0])

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ═══════════════════════════════════════════════════════════════
# MODULO 1A
# ═══════════════════════════════════════════════════════════════
def genera_modulo1a(dati: dict, firma_b64: str) -> bytes:
    az = config.AZIENDA
    reader = PdfReader(PDF_MODULO1A)
    writer = PdfWriter()
    writer.append(reader)

    W, H = 595.28, 841.89

    el_p1 = [
        # Sezione 2 — contribuente
        _t(225.0, 474.0, dati.get("cognome", "")),
        _t(224.0, 458.0, dati.get("nome", "")),
        _t(224.0, 440.0, _fmt(dati.get("data_nascita", ""))),

        # Periodo attivita
        _t(223.0, 291.0, _fmt(dati.get("prev_dal", ""))),
        _t(388.0, 292.0, _fmt(dati.get("prev_al", ""))),

        # Sezione 3 — precedente datore
        _t(150.0, 211.0, dati.get("prev_datore", "")),
        _t(151.0, 196.0, dati.get("prev_datore_indirizzo", "")),

        # Frase finale NPA + Comune
        _t(262.0, 90.0, dati.get("npa_residenza", "")),
        _t(357.0, 91.0, dati.get("comune_residenza_frontiera", "")),
    ]

    # Sesso — Maschile rect [416,437,427,448] centro (421.5,442.5)
    #          Femminile rect [512,437,523,448] centro (517.5,442.5)
    if dati.get("sesso") == "Maschile":
        el_p1.append(_x(421.5, 442.5))
    else:
        el_p1.append(_x(517.5, 442.5))

    # Permesso — G rect [222,418,233,429] centro (227.5,423.5)
    #            Solo notifica rect [317,418,328,429] centro (322.5,423.5)
    #            Svizzero rect [418,419,429,430] centro (423.5,424.5)
    permesso = dati.get("permesso", "")
    if permesso == "G (Frontaliere)":
        el_p1.append(_x(227.5, 423.5))
    elif permesso == "Solo notifica":
        el_p1.append(_x(322.5, 423.5))
    elif permesso in ("No, svizzero/a", "Nessun permesso"):
        el_p1.append(_x(423.5, 424.5))

    layer1 = _overlay(W, H, el_p1)
    writer.pages[0].merge_page(layer1.pages[0])

    # ── PAGINA 2 ──
    # "Data e luogo" — da pdfplumber: 'Data' top=226.2 PDF_y=615.7
    # Campo data rect [140,613,239,624], campo firma rect [358,612,457,623]
    # "Manno," e' gia' prestampato — scriviamo solo la data nel campo
    # Firma nel campo firma a destra

    el_p2 = [
        _t(140.0, 615.0, _fmt(dati.get("data_firma", ""))),
    ]

    if firma_b64:
        # Campo firma rect [358,612,457,623] — larghezza 99, altezza 11
        # Allarghiamo un po' la firma per renderla leggibile
        el_p2.append(_f(355, 605, 110, 22, firma_b64))

    layer2 = _overlay(W, H, el_p2)
    writer.pages[1].merge_page(layer2.pages[0])

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


# ═══════════════════════════════════════════════════════════════
# MODULO 1908
# ═══════════════════════════════════════════════════════════════
def genera_modulo1908(dati: dict, firma_b64: str) -> bytes:
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)

    T = ParagraphStyle("T", fontSize=12, fontName="Helvetica-Bold",
                       spaceAfter=4, alignment=TA_CENTER)
    S = ParagraphStyle("S", fontSize=9, fontName="Helvetica-Bold",
                       spaceAfter=4, spaceBefore=10,
                       textColor=colors.HexColor("#1a1a2e"))
    N = ParagraphStyle("N", fontSize=9, fontName="Helvetica", spaceAfter=2)

    def riga(label, val):
        return [Paragraph(f"<b>{label}</b>", N),
                Paragraph(str(val) if val else "—", N)]

    def tab(righe):
        t = Table(righe, colWidths=[6*cm, 10*cm])
        t.setStyle(TableStyle([
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        return t

    padre = f"{dati.get('padre_cognome','')} {dati.get('padre_nome','')}".strip()
    madre = f"{dati.get('madre_cognome','')} {dati.get('madre_nome','')}".strip()

    e = []
    e.append(Paragraph("FORMULARIO 1908 GROUP SA", T))
    e.append(Paragraph("DATI PERSONALI DEL COLLABORATORE", T))
    e.append(HRFlowable(width="100%", thickness=2,
                        color=colors.HexColor("#1a1a2e"), spaceAfter=8))

    e.append(Paragraph("DATI PERSONALI", S))
    e.append(tab([
        riga("Cognome",            dati.get("cognome","")),
        riga("Nome",               dati.get("nome","")),
        riga("Via",                dati.get("domicilio_via","")),
        riga("CAP",                dati.get("domicilio_cap","")),
        riga("Localita",           dati.get("domicilio_localita","")),
        riga("Cellulare",          dati.get("cellulare","")),
        riga("E-mail privata",     dati.get("email_privata","")),
        riga("Data di nascita",    _fmt(dati.get("data_nascita",""))),
        riga("Comune di nascita",  dati.get("luogo_nascita","")),
        riga("Nazione di nascita", dati.get("nazione_nascita","")),
        riga("Nazionalita",        dati.get("nazionalita","")),
        riga("Religione",          dati.get("religione","")),
        riga("Permesso",           dati.get("permesso","")),
        riga("Rilasciato il",      _fmt(dati.get("permesso_rilascio",""))),
        riga("Scadenza",           _fmt(dati.get("permesso_scadenza",""))),
        riga("Codice fiscale",     dati.get("codice_fiscale","")),
        riga("N. AVS",             dati.get("numero_avs","")),
        riga("Stato civile",       dati.get("stato_civile","")),
        riga("Data matrimonio",    _fmt(dati.get("data_matrimonio",""))),
        riga("Data divorzio/sep.", _fmt(dati.get("data_divorzio",""))),
        riga("Patente guida B",    "Si" if _si(dati.get("patente")) else "No"),
    ]))

    e.append(Paragraph("CONTRATTO DI LAVORO", S))
    e.append(tab([
        riga("Qualifica",              dati.get("qualifica","")),
        riga("Percentuale di impiego", f"{dati.get('grado_occupazione','')}%"),
        riga("Data inizio attivita",   _fmt(dati.get("data_inizio",""))),
    ]))

    e.append(Paragraph("DATI CONIUGE / PARTNER", S))
    e.append(tab([
        riga("Cognome",            dati.get("coniuge_cognome","")),
        riga("Nome",               dati.get("coniuge_nome","")),
        riga("Data di nascita",    _fmt(dati.get("coniuge_nascita",""))),
        riga("Numero AVS",         dati.get("coniuge_avs","")),
        riga("Luogo di nascita",   dati.get("coniuge_luogo_nascita","")),
        riga("Nazionalita",        dati.get("coniuge_nazionalita","")),
        riga("Residenza estera",   "Si" if _si(dati.get("coniuge_residenza_estera")) else "No"),
        riga("Dove",               dati.get("coniuge_dove","")),
        riga("Lavora",             dati.get("coniuge_lavora","No")),
        riga("Lavora in Svizzera", dati.get("coniuge_lavora_ch","No")),
    ]))

    e.append(Paragraph("FIGLI A CARICO", S))
    figli_validi = [f for f in dati.get("figli",[]) if f.get("nome","").strip()]
    if figli_validi:
        rf = [[Paragraph("<b>Nome e cognome</b>", N),
               Paragraph("<b>Data di nascita</b>", N),
               Paragraph("<b>Inizio diritto assegno</b>", N),
               Paragraph("<b>Fine diritto assegno</b>", N)]]
        for f in figli_validi:
            rf.append([
                Paragraph(f.get("nome",""), N),
                Paragraph(_fmt(f.get("nascita","")), N),
                Paragraph(_fmt(f.get("inizio","")), N),
                Paragraph(_fmt(f.get("fine","")), N),
            ])
        t = Table(rf, colWidths=[5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        t.setStyle(TableStyle([
            ("FONTSIZE",     (0,0), (-1,-1), 9),
            ("BOTTOMPADDING",(0,0), (-1,-1), 4),
            ("LINEBELOW",    (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
            ("BACKGROUND",   (0,0), (-1,0),  colors.HexColor("#f0f0f0")),
        ]))
        e.append(t)
    else:
        e.append(Paragraph("Nessun figlio a carico.", N))

    e.append(tab([riga("Assegni famigliari",
                       "Si" if _si(dati.get("assegni_famigliari")) else "No")]))

    e.append(Paragraph("GENITORI", S))
    e.append(tab([
        riga("Nome e cognome padre",  padre),
        riga("Data di nascita padre", _fmt(dati.get("padre_nascita",""))),
        riga("Nome e cognome madre",  madre),
        riga("Data di nascita madre", _fmt(dati.get("madre_nascita",""))),
    ]))

    e.append(Paragraph("DATI BANCARI", S))
    e.append(tab([
        riga("Banca",     dati.get("banca_nome","")),
        riga("Citta",     dati.get("banca_citta","")),
        riga("Titolare",  dati.get("banca_titolare","")),
        riga("IBAN",      dati.get("iban","")),
        riga("SWIFT/BIC", dati.get("swift","")),
    ]))

    e.append(Paragraph("SICUREZZA SUL LAVORO", S))
    e.append(tab([
        riga("Videosorveglianza",       "Si" if _si(dati.get("videosorveglianza")) else "No"),
        riga("Formazione CCNL Alb. CH", dati.get("formazione_ccnl","No")),
        riga("Quale formazione",        dati.get("formazione_quale","")),
        riga("Consenso dati personali", "Si" if _si(dati.get("consenso_dati")) else "No"),
    ]))

    e.append(Spacer(1, 0.5*cm))
    if firma_b64:
        try:
            img = _firma_pil(firma_b64)
            ib = io.BytesIO()
            img.save(ib, format="PNG")
            ib.seek(0)
            from reportlab.platypus import Image as RLImage
            e.append(RLImage(ib, width=6*cm, height=2*cm))
        except Exception:
            pass

    e.append(Spacer(1, 0.3*cm))
    e.append(Paragraph(f"Lugano, {_fmt(dati.get('data_firma',''))}", N))
    e.append(Spacer(1, 1*cm))
    ft = Table([
        [Paragraph("Firma del/la dipendente", N),
         Paragraph("Firma della 1908 Group SA", N)]
    ], colWidths=[8*cm, 8*cm])
    ft.setStyle(TableStyle([
        ("LINEABOVE",  (0,0), (-1,-1), 0.5, colors.black),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    e.append(ft)

    doc.build(e)
    return buf.getvalue()
