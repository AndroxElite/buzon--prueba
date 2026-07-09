"""
Sistema de gestión del Buzón de Sugerencias — Americar
Ejecutar localmente:  streamlit run app.py
"""

import re
import unicodedata
from io import BytesIO

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Buzón de Sugerencias — Americar", layout="wide")

# =========================================================
# Utilidades de texto
# =========================================================

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn")


def norm(s):
    s = strip_accents(str(s).lower())
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def has_kw(txt, kw):
    pattern = r"\b" + re.escape(kw) + r"\b"
    return re.search(pattern, txt) is not None


# =========================================================
# Reglas por defecto (editables desde la pantalla "Áreas")
# =========================================================

CATS_DEFAULT = {
    "Academia Americar": [
        "capacitacion", "capacitaciones", "capacitar", "curso", "cursos", "formacion",
        "induccion", "amonestacion", "amonestaciones", "examen", "certificacion", "entrenamiento",
    ],
    "Logística": [
        "traslado", "traslados", "transporte", "logistica", "movimiento de vehiculo",
        "movimiento de unidades", "stock de vehiculo", "entrega de vehiculo",
        "preparacion de vehiculo", "preparacion de unidades", "patio", "grua", "camion",
        "flota", "despacho de vehiculo", "entre sucursales", "patente", "grabado",
        "permisos de circulacion", "hidrolavadora", "manguera",
    ],
    "HRBP": [
        "estructura organizacional", "organigrama", "cambio de cargo", "funciones del cargo",
        "ascenso", "ascensos", "reestructuracion", "liderazgo", "cambio de funciones",
        "jefatura", "nuevo jefe", "cambio de jefe", "reporte directo", "gerencia de area",
        "movilidad de personal", "mal trato", "falta de respeto", "maltrato laboral",
        "acoso laboral", "acoso", "dotacion", "cambio de puesto", "promocion", "promociones",
        "postular a cargos", "rrhh",
    ],
    "Infraestructura": [
        "techo", "techos", "construccion", "ampliacion", "bano", "banos", "climatizacion",
        "aire acondicionado", "ceramica", "piso", "pisos", "electrico", "electricidad",
        "iluminacion", "estacionamiento", "infraestructura", "filtracion", "gotera",
        "sala de venta", "mantencion del local", "obra", "remodelacion", "humedad",
        "temperatura", "contenedor", "oficina",
    ],
    "Finanzas": [
        "caja chica", "caja", "pago a proveedor", "rendicion de gastos", "presupuesto",
        "flujo de caja", "tesoreria", "viaticos", "reembolso", "anticipo de caja",
        "facturacion", "cuentas por pagar",
    ],
    "Prevención de riesgos": [
        "uniforme", "uniformes", "epp", "seguridad laboral", "prevencion de riesgos",
        "riesgo laboral", "accidente laboral", "accidente", "extintor", "senaletica",
        "casco", "guantes de seguridad", "zapatos de seguridad", "implementos de seguridad",
        "condiciones de seguridad", "peligro", "ropa de trabajo", "tallas",
        "elementos de aseo", "salud mental", "estres laboral", "bienestar laboral",
        "vacunacion", "salud ocupacional",
    ],
    "Inteligencia de negocio": [
        "precio del vehiculo", "precios de vehiculo", "tasacion", "cotizacion de vehiculo",
        "valor comercial del vehiculo", "competencia de precios", "precio de lista",
        "inteligencia de negocio",
    ],
    "Remuneraciones": [
        "sueldo", "sueldos", "salario", "liquidacion", "liquidaciones", "bono", "bonos",
        "comision", "comisiones", "remuneracion", "remuneraciones", "gratificacion",
        "aumento de sueldo", "beneficios economicos", "pago de sueldo", "beneficios",
        "tarjeta de alimentos", "colacion", "aguinaldo", "asignacion familiar",
    ],
    "Reclutamiento y Selección": [
        "proceso de ingreso", "entrevista de trabajo", "contratacion", "nuevo ingreso",
        "induccion de ingreso", "entrega de computador", "entrega de notebook",
        "proceso de seleccion", "reclutamiento", "seleccion de personal", "oferta laboral",
    ],
}

URGENCY_WORDS = [
    "urgente", "urgencia", "grave", "peligro", "peligroso", "riesgo", "accidente",
    "acoso", "maltrato", "abuso", "discriminacion", "ilegal", "amenaza", "amenazas",
    "injusto", "injusticia", "no contesta", "no responde", "no funciona", "incumplimiento",
    "fraude", "robo", "seguridad",
]
NEGATIVE_WORDS = [
    "mal", "malo", "mala", "pesimo", "terrible", "molesto", "frustrado", "falta",
    "faltan", "problema", "problemas", "error", "errores", "demora", "demoras",
    "reclamo", "queja", "quejas", "nunca", "insuficiente", "deficiente", "lento", "dificil",
]
LOW_CONTENT = {
    "", "nada", "ninguno", "ninguna", "no", "ok", "todo bien", "sin comentario",
    "sin comentarios", "nada que comentar", "gracias", "felicitaciones", "muy bueno",
    "excelente", "bien", "na",
}
CATEGORY_BASE = {
    "reclamo o inquietud": 30, "recomendacion sobre procesos": 20, "sugerencia de mejora": 15,
    "duda o consulta": 10, "otro": 10, "felicitacion o reconocimiento": 0,
}

# =========================================================
# Estado de la sesión (persiste mientras la pestaña está abierta)
# =========================================================

if "cats" not in st.session_state:
    st.session_state.cats = {k: list(v) for k, v in CATS_DEFAULT.items()}
if "nomina" not in st.session_state:
    st.session_state.nomina = None
if "casos" not in st.session_state:
    st.session_state.casos = None

# =========================================================
# Lógica de clasificación
# =========================================================

def classify(txt_norm, cats):
    scores = {cat: 0 for cat in cats}
    for cat, kws in cats.items():
        for kw in kws:
            if has_kw(txt_norm, norm(kw)):
                scores[cat] += 1
    return scores


def is_low_content(txt_norm, wc):
    if wc == 0:
        return True
    if txt_norm in LOW_CONTENT:
        return True
    if re.fullmatch(r"[.\-,\s]*", txt_norm.replace(" ", "")):
        return True
    if wc <= 4 and not any(w in txt_norm for w in URGENCY_WORDS + NEGATIVE_WORDS):
        return True
    return False


def score_row(txt_norm, wc, tipo, descartar):
    if descartar:
        return 0
    cat = norm(tipo)
    score = CATEGORY_BASE.get(cat, 10)
    score += min(wc, 60) / 60 * 20
    urg_hits = sum(1 for w in URGENCY_WORDS if w in txt_norm)
    score += min(urg_hits, 4) * 10
    neg_hits = sum(1 for w in NEGATIVE_WORDS if w in txt_norm)
    score += min(neg_hits, 6) * 5
    return round(min(score, 100), 1)


def prioridad_de(score):
    if score >= 60:
        return "Alta"
    if score >= 25:
        return "Media"
    if score > 0:
        return "Baja"
    return "Descartado"


def procesar_buzon(df_buzon, df_nomina, cats):
    df = df_buzon.copy()

    # localizar columnas de texto y rut de forma flexible
    col_comentario = next((c for c in df.columns if norm(c) == "comentario"), None)
    if col_comentario is None:
        col_comentario = next(
            (c for c in df.columns if "coment" in norm(c) and "tipo" not in norm(c)),
            df.columns[-1],
        )
    col_tipo = next((c for c in df.columns if "tipo" in norm(c) and "coment" in norm(c)), None)
    col_rut = next((c for c in df.columns if "rut" in norm(c)), None)

    df["_texto_norm"] = df[col_comentario].astype(str).apply(norm)
    df["_wc"] = df["_texto_norm"].apply(lambda s: len(s.split()) if s else 0)

    # cruce con nómina
    ex_colaborador = pd.Series(False, index=df.index)
    if df_nomina is not None and col_rut is not None:
        rut_col_nomina = next((c for c in df_nomina.columns if "rut" in norm(c)), None)
        estado_col_nomina = next((c for c in df_nomina.columns if "estado" in norm(c)), None)
        if rut_col_nomina and estado_col_nomina:
            nomina_map = dict(zip(
                df_nomina[rut_col_nomina].astype(str).str.strip(),
                df_nomina[estado_col_nomina].astype(str).str.strip().str.lower(),
            ))
            def check_activo(rut):
                estado = nomina_map.get(str(rut).strip())
                if estado is None:
                    return False
                return "inactiv" in estado or "no" == estado
            ex_colaborador = df[col_rut].apply(check_activo)

    df["Ex_colaborador"] = ex_colaborador
    df["Descartar"] = df.apply(
        lambda r: "Sí" if (r["Ex_colaborador"] or is_low_content(r["_texto_norm"], r["_wc"])) else "No",
        axis=1,
    )

    tipo_series = df[col_tipo] if col_tipo else pd.Series("", index=df.index)
    df["Score_Criticidad"] = [
        score_row(t, wc, tipo, desc == "Sí")
        for t, wc, tipo, desc in zip(df["_texto_norm"], df["_wc"], tipo_series, df["Descartar"])
    ]
    df["Prioridad"] = df["Score_Criticidad"].apply(prioridad_de)

    def derivar(row):
        if row["Ex_colaborador"]:
            return "No derivar (ex-colaborador)"
        if row["Descartar"] == "Sí":
            return "No derivar"
        scores = classify(row["_texto_norm"], cats)
        max_score = max(scores.values())
        if max_score == 0:
            return "Requiere revisión manual"
        top = [c for c, s in scores.items() if s == max_score]
        return top[0]

    df["Derivar a"] = df.apply(derivar, axis=1)
    df = df.drop(columns=["_texto_norm", "_wc"])
    return df


def to_excel_bytes(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultado")
    return buf.getvalue()


# =========================================================
# Interfaz
# =========================================================

st.title("📮 Sistema de gestión — Buzón de Sugerencias")

tab_buzon, tab_nomina, tab_areas = st.tabs(["📬 Buzón", "🧑‍💼 Nómina", "🗂️ Áreas"])

# ---------- PANTALLA ÁREAS ----------
with tab_areas:
    st.subheader("Reglas de derivación por palabra clave")
    st.caption(
        "Edita las palabras clave de cada categoría. Una palabra o frase por línea. "
        "Estas reglas se aplican al contenido real del comentario, no al tipo que la persona eligió."
    )
    cols = st.columns(2)
    cat_names = list(st.session_state.cats.keys())
    for i, cat in enumerate(cat_names):
        with cols[i % 2]:
            text_val = "\n".join(st.session_state.cats[cat])
            new_val = st.text_area(cat, value=text_val, height=140, key=f"cat_{cat}")
            st.session_state.cats[cat] = [w.strip() for w in new_val.split("\n") if w.strip()]

# ---------- PANTALLA NÓMINA ----------
with tab_nomina:
    st.subheader("Plantilla de personal")
    st.caption(
        "Sube la nómina completa vigente (RUT + estado laboral). Se usa para descartar "
        "automáticamente comentarios de personas que ya no trabajan en la empresa."
    )
    file_nomina = st.file_uploader("Excel de nómina (.xlsx)", type=["xlsx"], key="up_nomina")
    if file_nomina is not None:
        st.session_state.nomina = pd.read_excel(file_nomina)
        st.success(f"Nómina cargada: {len(st.session_state.nomina)} registros")
    if st.session_state.nomina is not None:
        st.dataframe(st.session_state.nomina, use_container_width=True, height=300)
        st.info(
            "La columna de estado debe contener valores como 'Activo' / 'Inactivo'. "
            "Se detecta automáticamente cualquier columna que contenga 'estado' y cualquiera que contenga 'rut'."
        )

# ---------- PANTALLA BUZÓN ----------
with tab_buzon:
    st.subheader("Comentarios del buzón")
    file_buzon = st.file_uploader("Excel del buzón (.xlsx)", type=["xlsx"], key="up_buzon")

    if file_buzon is not None:
        df_raw = pd.read_excel(file_buzon)
        with st.spinner("Clasificando comentarios..."):
            df_resultado = procesar_buzon(df_raw, st.session_state.nomina, st.session_state.cats)
        st.session_state.casos = df_resultado

    if st.session_state.casos is not None:
        df_resultado = st.session_state.casos

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            f_prioridad = st.multiselect(
                "Prioridad", sorted(df_resultado["Prioridad"].dropna().unique()),
            )
        with c2:
            f_derivar = st.multiselect(
                "Derivar a", sorted(df_resultado["Derivar a"].dropna().unique()),
            )
        with c3:
            f_descartar = st.selectbox("Mostrar descartados", ["No", "Sí", "Todos"])
        with c4:
            f_texto = st.text_input("Buscar texto en comentario")

        df_view = df_resultado.copy()
        if f_prioridad:
            df_view = df_view[df_view["Prioridad"].isin(f_prioridad)]
        if f_derivar:
            df_view = df_view[df_view["Derivar a"].isin(f_derivar)]
        if f_descartar == "No":
            df_view = df_view[df_view["Descartar"] == "No"]
        elif f_descartar == "Sí":
            df_view = df_view[df_view["Descartar"] == "Sí"]
        if f_texto:
            col_comentario = next((c for c in df_view.columns if norm(c) == "comentario"), None)
            if col_comentario is None:
                col_comentario = next(
                    (c for c in df_view.columns if "coment" in norm(c) and "tipo" not in norm(c)),
                    None,
                )
            if col_comentario:
                df_view = df_view[df_view[col_comentario].astype(str).str.contains(f_texto, case=False, na=False)]

        st.caption(f"{len(df_view)} de {len(df_resultado)} comentarios")
        st.dataframe(
            df_view.sort_values("Score_Criticidad", ascending=False),
            use_container_width=True,
            height=500,
        )

        st.download_button(
            "⬇️ Descargar resultado (Excel)",
            data=to_excel_bytes(df_view),
            file_name="buzon_clasificado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Sube un Excel del buzón para ver la clasificación.")
