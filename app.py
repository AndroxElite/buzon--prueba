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
if "zonas" not in st.session_state:
    st.session_state.zonas = None
if "casos" not in st.session_state:
    st.session_state.casos = None
if "resueltos" not in st.session_state:
    st.session_state.resueltos = set()

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


def limpiar_texto(texto):
    texto = str(texto)
    texto = re.sub(r"_x000[dD]_", " ", texto)
    texto = re.sub(r"_x000[aA]_", " ", texto)
    texto = re.sub(r"[\r\n]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def resumir_comentario(texto, max_palabras=12):
    texto = limpiar_texto(texto)
    if not texto or texto.lower() == "nan":
        return "(sin texto)"
    primera_oracion = re.split(r"(?<=[.!?])\s", texto)[0]
    palabras = primera_oracion.split()
    if len(palabras) > max_palabras:
        return " ".join(palabras[:max_palabras]) + "…"
    return primera_oracion


def procesar_buzon(df_buzon, df_nomina, cats, df_zonas=None):
    df = df_buzon.copy().reset_index(drop=True)
    df["id_caso"] = df.index

    # localizar columnas de texto y rut de forma flexible
    col_comentario = next((c for c in df.columns if norm(c) == "comentario"), None)
    if col_comentario is None:
        col_comentario = next(
            (c for c in df.columns if "coment" in norm(c) and "tipo" not in norm(c)),
            df.columns[-1],
        )
    col_tipo = next((c for c in df.columns if "tipo" in norm(c) and "coment" in norm(c)), None)
    col_rut = next((c for c in df.columns if "rut" in norm(c)), None)

    df["Título"] = df[col_comentario].apply(resumir_comentario)
    df["_texto_norm"] = df[col_comentario].astype(str).apply(norm)
    df["_wc"] = df["_texto_norm"].apply(lambda s: len(s.split()) if s else 0)

    # cruce con nómina
    # homologación de zona / macro-zona por RUT
    if df_zonas is not None and col_rut is not None:
        rut_col_zonas = next((c for c in df_zonas.columns if "rut" in norm(c)), None)
        zh_col = next((c for c in df_zonas.columns if "homolog" in norm(c)), None)
        mz_col = next((c for c in df_zonas.columns if "macro" in norm(c)), None)
        if rut_col_zonas:
            if zh_col:
                zona_map = dict(zip(
                    df_zonas[rut_col_zonas].astype(str).str.strip(),
                    df_zonas[zh_col].astype(str).str.strip(),
                ))
                df["Zona_Homologada"] = df[col_rut].astype(str).str.strip().map(zona_map)
            if mz_col:
                macro_map = dict(zip(
                    df_zonas[rut_col_zonas].astype(str).str.strip(),
                    df_zonas[mz_col].astype(str).str.strip(),
                ))
                df["Macro_Zona"] = df[col_rut].astype(str).str.strip().map(macro_map)

    estado_nomina = pd.Series("Sin verificar", index=df.index)
    if df_nomina is not None and col_rut is not None:
        rut_col_nomina = next((c for c in df_nomina.columns if "rut" in norm(c)), None)
        estado_col_nomina = next((c for c in df_nomina.columns if "estado" in norm(c)), None)
        if rut_col_nomina and estado_col_nomina:
            nomina_map = dict(zip(
                df_nomina[rut_col_nomina].astype(str).str.strip(),
                df_nomina[estado_col_nomina].astype(str).str.strip(),
            ))

            def clasificar_estado(rut):
                estado = nomina_map.get(str(rut).strip())
                if estado is None:
                    # la nómina se trata como "foto" completa y actualizada:
                    # si el RUT no aparece, se entiende como desvinculado
                    return "Ex-colaborador"
                estado_n = norm(estado)
                if estado_n == "activo":
                    return "Activo"
                if estado_n == "pendiente":
                    return "Activo"  # vigente, no es ex-colaborador
                # Inactivo, vacío, typo, o cualquier valor no reconocido -> fail-safe: Ex-colaborador
                return "Ex-colaborador"

            estado_nomina = df[col_rut].apply(clasificar_estado)

    df["Estado_Nomina"] = estado_nomina
    df["Ex_colaborador"] = estado_nomina == "Ex-colaborador"
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
    st.subheader("Reglas de derivación y homologación de zonas")
    st.caption(
        "Sube un Excel con 2 hojas: 'Palabras_clave' (Categoria, Palabra_clave) y "
        "'Zonas' (Rut, Zona_homologada, Macro_zona). Estas reglas se aplican al contenido "
        "real del comentario, no al tipo que la persona eligió."
    )
    file_areas = st.file_uploader("Excel de reglas (.xlsx)", type=["xlsx"], key="up_areas")

    if file_areas is not None:
        try:
            xl_areas = pd.ExcelFile(file_areas)
            hoja_kw = next((s for s in xl_areas.sheet_names if "palabra" in norm(s)), None)
            hoja_zonas = next((s for s in xl_areas.sheet_names if "zona" in norm(s)), None)

            if hoja_kw:
                df_kw = pd.read_excel(xl_areas, sheet_name=hoja_kw)
                col_cat = next((c for c in df_kw.columns if "categ" in norm(c)), None)
                col_palabra = next((c for c in df_kw.columns if "palabra" in norm(c)), None)
                if col_cat and col_palabra:
                    nuevas_cats = {}
                    for _, r in df_kw.dropna(subset=[col_cat, col_palabra]).iterrows():
                        cat = str(r[col_cat]).strip()
                        palabra = str(r[col_palabra]).strip()
                        nuevas_cats.setdefault(cat, []).append(palabra)
                    st.session_state.cats = nuevas_cats
                    st.success(f"Palabras clave cargadas: {len(nuevas_cats)} categorías, "
                               f"{sum(len(v) for v in nuevas_cats.values())} palabras")
                else:
                    st.error("La hoja de palabras clave necesita columnas 'Categoria' y 'Palabra_clave'.")
            else:
                st.warning("No se encontró una hoja de palabras clave (debe contener 'palabra' en el nombre).")

            if hoja_zonas:
                df_zonas = pd.read_excel(xl_areas, sheet_name=hoja_zonas)
                st.session_state.zonas = df_zonas
                st.success(f"Homologación de zonas cargada: {len(df_zonas)} registros")
            else:
                st.warning("No se encontró una hoja de zonas (debe contener 'zona' en el nombre).")
        except Exception as e:
            st.error(f"No se pudo leer el archivo: {e}")

    st.divider()
    st.markdown("**Palabras clave actualmente cargadas:**")
    if st.session_state.cats:
        resumen = pd.DataFrame(
            [(cat, len(kws)) for cat, kws in st.session_state.cats.items()],
            columns=["Categoría", "N° palabras clave"],
        )
        st.dataframe(resumen, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no se ha cargado un archivo de reglas — se están usando las reglas por defecto internas.")

    if st.session_state.zonas is not None:
        st.markdown("**Homologación de zonas cargada:**")
        st.dataframe(st.session_state.zonas.head(10), use_container_width=True, hide_index=True)

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
        st.warning(
            "⚠️ La nómina se trata como una foto **completa y actualizada** del personal vigente. "
            "Si el RUT de un comentario no aparece en esta tabla, se asume que la persona ya no "
            "trabaja en la empresa y el caso se descarta automáticamente. Si subes una nómina "
            "incompleta o desactualizada, comentarios de colaboradores activos reales pueden "
            "descartarse por error. Sube siempre la versión más reciente y completa."
        )

# ---------- PANTALLA BUZÓN ----------
with tab_buzon:
    st.subheader("Comentarios del buzón")
    file_buzon = st.file_uploader("Excel del buzón (.xlsx)", type=["xlsx"], key="up_buzon")

    if file_buzon is not None:
        df_raw = pd.read_excel(file_buzon)
        with st.spinner("Clasificando comentarios..."):
            df_resultado = procesar_buzon(
                df_raw, st.session_state.nomina, st.session_state.cats, st.session_state.zonas
            )
        st.session_state.casos = df_resultado
        st.session_state.resueltos = set()  # nueva carga -> se reinicia el checklist

    if st.session_state.casos is not None:
        df_resultado = st.session_state.casos

        # detección flexible de columnas de contexto
        col_zona = next((c for c in df_resultado.columns if norm(c) == "zona"), None)
        col_sucursal = next((c for c in df_resultado.columns if "sucursal" in norm(c)), None)
        col_nombre = next((c for c in df_resultado.columns if "nombre" in norm(c)), None)
        col_cargo = next((c for c in df_resultado.columns if "cargo" in norm(c)), None)
        col_rut_ui = next((c for c in df_resultado.columns if "rut" in norm(c)), None)
        col_fecha = next((c for c in df_resultado.columns if "fecha" in norm(c) and "ingreso" in norm(c)), None)
        if col_fecha is None:
            col_fecha = next((c for c in df_resultado.columns if "fecha" in norm(c)), None)
        col_comentario_ui = next((c for c in df_resultado.columns if norm(c) == "comentario"), None)
        if col_comentario_ui is None:
            col_comentario_ui = next(
                (c for c in df_resultado.columns if "coment" in norm(c) and "tipo" not in norm(c)), None
            )
        col_tipo_ui = next((c for c in df_resultado.columns if "tipo" in norm(c) and "coment" in norm(c)), None)

        # ---------- Filtros ----------
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            f_zona = st.multiselect(
                "Zona", sorted(df_resultado[col_zona].dropna().unique()) if col_zona else [],
                disabled=col_zona is None,
            )
        with f2:
            f_sucursal = st.multiselect(
                "Sucursal", sorted(df_resultado[col_sucursal].dropna().unique()) if col_sucursal else [],
                disabled=col_sucursal is None,
            )
        with f3:
            f_tipo = st.multiselect(
                "Tipo de comentario", sorted(df_resultado[col_tipo_ui].dropna().unique()) if col_tipo_ui else [],
                disabled=col_tipo_ui is None,
            )
        with f4:
            f_prioridad = st.multiselect(
                "Prioridad", ["Alta", "Media", "Baja", "Descartado"],
            )
        with f5:
            f_responsable = st.multiselect(
                "Responsable", sorted(df_resultado["Derivar a"].dropna().unique()),
            )

        f_texto = st.text_input("🔎 Buscar (comentario, zona, rut o colaborador)")

        df_view = df_resultado.copy()
        if f_zona:
            df_view = df_view[df_view[col_zona].isin(f_zona)]
        if f_sucursal:
            df_view = df_view[df_view[col_sucursal].isin(f_sucursal)]
        if f_tipo:
            df_view = df_view[df_view[col_tipo_ui].isin(f_tipo)]
        if f_prioridad:
            df_view = df_view[df_view["Prioridad"].isin(f_prioridad)]
        if f_responsable:
            df_view = df_view[df_view["Derivar a"].isin(f_responsable)]
        if f_texto:
            campos_busqueda = [c for c in [col_comentario_ui, col_zona, col_rut_ui, col_nombre] if c]
            mascara = pd.Series(False, index=df_view.index)
            for c in campos_busqueda:
                mascara |= df_view[c].astype(str).str.contains(f_texto, case=False, na=False)
            df_view = df_view[mascara]

        # ---------- Indicadores ----------
        total_msj = len(df_view)
        no_derivar_vals = {"No derivar", "No derivar (ex-colaborador)"}
        resueltos_ids = st.session_state.resueltos
        pendientes = df_view[
            (~df_view["id_caso"].isin(resueltos_ids)) & (~df_view["Derivar a"].isin(no_derivar_vals))
        ]
        resueltos_view = df_view[df_view["id_caso"].isin(resueltos_ids)]

        i1, i2, i3 = st.columns(3)
        i1.metric("Total mensajes", total_msj)
        i2.metric("Pendientes", len(pendientes))
        i3.metric("Resueltos", len(resueltos_view))

        st.divider()

        # ---------- Checklist ----------
        df_ordenado = df_view.sort_values("Score_Criticidad", ascending=False)

        if len(df_ordenado) == 0:
            st.info("No hay comentarios que calcen con los filtros seleccionados.")

        for _, row in df_ordenado.iterrows():
            id_caso = row["id_caso"]
            zona_v = row[col_zona] if col_zona else "—"
            sucursal_v = row[col_sucursal] if col_sucursal else "—"
            prioridad_v = row["Prioridad"]
            responsable_v = row["Derivar a"]

            with st.container(border=True):
                col_chk, col_body = st.columns([0.05, 0.95])
                with col_chk:
                    marcado = st.checkbox(
                        "Resuelto", value=id_caso in resueltos_ids,
                        key=f"resuelto_{id_caso}", label_visibility="collapsed",
                    )
                    if marcado:
                        st.session_state.resueltos.add(id_caso)
                    else:
                        st.session_state.resueltos.discard(id_caso)
                with col_body:
                    prioridad_emoji = {"Alta": "🔴", "Media": "🟡", "Baja": "🟢", "Descartado": "⚪"}.get(prioridad_v, "")
                    st.markdown(f"**{row['Título']}**")
                    st.caption(f"📍 {zona_v}  ·  🏢 {sucursal_v}  ·  {prioridad_emoji} {prioridad_v}  ·  👤 {responsable_v}")
                    with st.expander("Ver detalle completo"):
                        st.write(f"**Comentario completo:** {limpiar_texto(row[col_comentario_ui]) if col_comentario_ui else '—'}")
                        st.write(f"**Nombre:** {row[col_nombre] if col_nombre else '—'}")
                        st.write(f"**Rut:** {row[col_rut_ui] if col_rut_ui else '—'}")
                        st.write(f"**Cargo:** {row[col_cargo] if col_cargo else '—'}")
                        st.write(f"**Sucursal:** {sucursal_v}")
                        st.write(f"**Zona:** {zona_v}")
                        st.write(f"**Fecha del comentario:** {row[col_fecha] if col_fecha else '—'}")

        st.divider()
        st.download_button(
            "⬇️ Descargar resultado filtrado (Excel)",
            data=to_excel_bytes(df_view),
            file_name="buzon_clasificado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        st.info("Sube un Excel del buzón para ver la clasificación.")
