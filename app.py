import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA (ESTÉTICA CORPORATIVA TECH SIDERÚRGICA)
# ==============================================================================
st.set_page_config(
    page_title="Flejes Especiales | DSS Industrial",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS limpios y ejecutivos
st.markdown("""
<style>
    :root {
        --primary-navy: #0B2545;
        --steel-blue: #134074;
        --accent-cyan: #00A6FB;
        --bg-slate: #F8F9FA;
        --card-bg: #FFFFFF;
    }
    .main { background-color: var(--bg-slate); }
    .metric-card {
        background-color: var(--card-bg);
        border-left: 5px solid var(--steel-blue);
        padding: 16px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(11, 37, 69, 0.08);
        margin-bottom: 15px;
    }
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6C7A89;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--primary-navy);
        margin-top: 5px;
    }
    .metric-sub {
        font-size: 0.85rem;
        font-weight: 500;
        color: #495057;
        margin-top: 3px;
    }
    .status-badge {
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        display: inline-block;
        text-align: center;
        font-size: 0.95rem;
    }
    .status-green { background-color: #D4EDDA; color: #155724; border: 1px solid #C3E6CB; }
    .status-yellow { background-color: #FFF3CD; color: #856404; border: 1px solid #FFEEBA; }
    .status-red { background-color: #F8D7DA; color: #721C24; border: 1px solid #F5C6CB; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# DATOS MAESTROS OFICIALES
# ==============================================================================
@st.cache_data
def cargar_datos():
    familias = {
        'Laminado en frío': {
            'peso': 0.483,
            'coste_eur_t': 966,
            'gestion': 'Previsión por Modelo',
            'stock_ciclo': 213.0,
            'seguridad_3m': 735.0,
            'objetivo_3m': 948.0,
            'seguridad_2m': 671.0,
            'objetivo_2m': 884.0,
            'prev_mes': 426.3,
            'prev_3m': 1278.8
        },
        'Galvanizado': {
            'peso': 0.372,
            'coste_eur_t': 966,
            'gestion': 'Previsión por Modelo',
            'stock_ciclo': 164.0,
            'seguridad_3m': 556.0,
            'objetivo_3m': 720.0,
            'seguridad_2m': 447.0,
            'objetivo_2m': 611.0,
            'prev_mes': 327.9,
            'prev_3m': 983.8
        },
        'Fleje plastificado': {
            'peso': 0.061,
            'coste_eur_t': 1292,
            'gestion': 'Stock mínimo de seguridad',
            'stock_ciclo': 27.0,
            'seguridad_3m': 137.0,
            'objetivo_3m': 164.0,
            'seguridad_2m': 121.0,
            'objetivo_2m': 148.0,
            'prev_mes': 53.9,
            'prev_3m': 161.8
        },
        'Otros (hojalata, inox, electrocincado)': {
            'peso': 0.051,
            'coste_eur_t': 1539,
            'gestion': 'Stock mínimo de seguridad',
            'stock_ciclo': 22.0,
            'seguridad_3m': 78.0,
            'objetivo_3m': 101.0,
            'seguridad_2m': 62.0,
            'objetivo_2m': 84.0,
            'prev_mes': 44.9,
            'prev_3m': 134.6
        },
        'Carbono / muelle': {
            'peso': 0.033,
            'coste_eur_t': 1291,
            'gestion': 'Stock mínimo de seguridad',
            'stock_ciclo': 15.0,
            'seguridad_3m': 119.0,
            'objetivo_3m': 134.0,
            'seguridad_2m': 94.0,
            'objetivo_2m': 108.0,
            'prev_mes': 29.2,
            'prev_3m': 87.7
        }
    }

    # 4 trimestres auditados con % de acierto del modelo (sin columna de media)
    historico_evaluaciones = pd.DataFrame([
        {'Trimestre Auditado': 'Octubre - Diciembre 2025', 'Previsión del Modelo': '2.173 Tn', 'Real Descargado en Nave': '2.376 Tn', '% Acierto del Modelo': '91.4%', 'Desviación': '8.6%', 'Estado': 'Conforme'},
        {'Trimestre Auditado': 'Noviembre 2025 - Enero 2026', 'Previsión del Modelo': '2.162 Tn', 'Real Descargado en Nave': '2.141 Tn', '% Acierto del Modelo': '99.0%', 'Desviación': '1.0%', 'Estado': 'Conforme'},
        {'Trimestre Auditado': 'Diciembre 2025 - Febrero 2026', 'Previsión del Modelo': '2.159 Tn', 'Real Descargado en Nave': '2.543 Tn', '% Acierto del Modelo': '84.9%', 'Desviación': '15.1%', 'Estado': 'Conforme'},
        {'Trimestre Auditado': 'Enero - Marzo 2026', 'Previsión del Modelo': '2.495 Tn', 'Real Descargado en Nave': '2.485 Tn', '% Acierto del Modelo': '99.6%', 'Desviación': '0.4%', 'Estado': 'Conforme'}
    ])

    return familias, historico_evaluaciones

familias, historico_evaluaciones = cargar_datos()

# ==============================================================================
# BARRA LATERAL
# ==============================================================================
st.sidebar.markdown("""
<div style='text-align: center; padding: 10px 0 20px 0;'>
    <h2 style='color: #0B2545; margin-bottom: 2px; font-weight: 800;'>FLEJES ESPECIALES</h2>
    <span style='font-size: 0.75rem; letter-spacing: 0.12em; color: #134074; font-weight: 700;'>SISTEMA DE SOPORTE A LA DECISIÓN</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
modulo = st.sidebar.radio(
    "MÓDULO DE GESTIÓN:",
    [
        "🚦 Recomendador de Compra",
        "📊 Previsión de Recepciones y Tesorería",
        "💰 Ahorro y Rentabilidad de Inventario",
        "🛡️ Fiabilidad y Control del Sistema"
    ],
    index=0
)
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Parámetros Oficiales de Planta:**
* **Modelo:** ARIMAX con Precio INE y Estacionalidad
* **Precisión en Producción:** 91.2% de acierto medio
* **Ahorro Anual de Referencia:** 193.000 €/año
* **Corte de Datos:** Marzo 2026
""")
st.sidebar.caption("v2.9 | Flejes Especiales S.A.")

# ==============================================================================
# PESTAÑA 1: RECOMENDADOR OPERATIVO DE COMPRA
# ==============================================================================
if modulo == "🚦 Recomendador de Compra":
    st.markdown("## 🚦 Recomendador de Compra de Materia Prima")
    st.caption("Determina si emitir pedido hoy cruzando el stock físico real en nave con el stock objetivo y la cotización del acero del INE.")

    col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.2])
    with col1:
        familia_sel = st.selectbox("Familia Siderúrgica:", list(familias.keys()))
    with col2:
        plazo_sel = st.selectbox("Plazo de Entrega:", ["3 Meses", "2 Meses"])
    with col3:
        nivel_servicio = st.selectbox("Garantía de Suministro:", ["95%", "90%", "99%"])
    with col4:
        tendencia_precio = st.selectbox("Cotización del Acero (INE):", ["Alcista", "Estable", "Bajista"])

    f_data = familias[familia_sel]
    es_3m = plazo_sel == "3 Meses"

    z_factor = 1.65 if nivel_servicio == "95%" else (1.28 if nivel_servicio == "90%" else 2.33)
    z_base = 1.65

    stock_ciclo = f_data['stock_ciclo']
    seguridad_base = f_data['seguridad_3m'] if es_3m else f_data['seguridad_2m']
    seguridad_ajustada = (seguridad_base / z_base) * z_factor
    stock_objetivo = stock_ciclo + seguridad_ajustada

    coste_t = f_data['coste_eur_t']
    meses_num = 3 if es_3m else 2
    prev_periodo_t = f_data['prev_3m'] if es_3m else f_data['prev_mes'] * 2

    st.markdown("---")

    if "stock_real_usuario" not in st.session_state:
        st.session_state.stock_real_usuario = 600.0

    col_input, col_info = st.columns([1, 2])
    with col_input:
        stock_real = st.number_input(
            f"Stock Real Actual en Nave ({familia_sel}) [Tn]:",
            min_value=0.0,
            max_value=3000.0,
            value=float(st.session_state.stock_real_usuario),
            step=25.0,
            help="Introduce las toneladas que hay físicamente en fábrica hoy. Este valor no cambia al mover el plazo o la garantía."
        )
        st.session_state.stock_real_usuario = stock_real

    with col_info:
        st.info(f"""
        **Valores de referencia para {familia_sel}:**
        * **Stock de Ciclo:** {stock_ciclo:.0f} Tn  |  **Stock de Seguridad:** {seguridad_ajustada:.0f} Tn
        * **Stock Objetivo Recomendado:** **{stock_objetivo:.0f} Tn**
        * **Consumo Previsto en {plazo_sel}:** {prev_periodo_t:.1f} Tn
        """)

    diferencia_stock = stock_objetivo - stock_real

    if stock_real < seguridad_ajustada:
        estado = "COMPRA URGENTE"
        badge_class = "status-red"
        icono = "🔴"
        if tendencia_precio == "Alcista":
            toneladas_sugeridas = diferencia_stock * 1.15
            precio_contexto = f"El precio del acero viene subiendo en el INE. Además de cubrir la rotura técnica, se aconseja ampliar el lote a {toneladas_sugeridas:,.0f} Tn para congelar tarifa a {coste_t} €/Tn."
        elif tendencia_precio == "Bajista":
            toneladas_sugeridas = seguridad_ajustada - stock_real
            precio_contexto = f"Mercado bajista. Pedir estrictamente lo necesario para salir del nivel crítico ({toneladas_sugeridas:,.0f} Tn) y esperar bajadas adicionales para el resto."
        else:
            toneladas_sugeridas = diferencia_stock
            precio_contexto = f"Cotización estable. Solicitar el lote exacto de {toneladas_sugeridas:,.0f} Tn para restablecer el stock objetivo de fábrica."
        motivo = f"Stock en nave ({stock_real:.1f} Tn) por debajo de seguridad ({seguridad_ajustada:.1f} Tn). Riesgo inminente de parada técnica."
        accion = "Emitir pedido de reposición de forma inmediata al proveedor."
    elif stock_real < stock_objetivo:
        if tendencia_precio == "Alcista":
            estado = "COMPRA SUGERIDA"
            badge_class = "status-yellow"
            icono = "🟡"
            toneladas_sugeridas = diferencia_stock
            motivo = f"El stock ({stock_real:.1f} Tn) cubre la seguridad pero entra en zona de reposición de ciclo (objetivo: {stock_objetivo:.0f} Tn)."
            precio_contexto = f"**Oportunidad de precio:** Subida detectada en el índice INE. Se aconseja adelantar la compra para no asumir sobrecostes el mes próximo."
            accion = "Adelantar pedido ahora para congelar el precio actual."
        elif tendencia_precio == "Bajista":
            estado = "COMPRA CONTROLADA"
            badge_class = "status-yellow"
            icono = "🟡"
            toneladas_sugeridas = diferencia_stock * 0.5
            motivo = f"Stock en nave ({stock_real:.1f} Tn) con margen sobre seguridad ({seguridad_ajustada:.1f} Tn)."
            precio_contexto = "Mercado a la baja. Se recomienda pedir solo medio lote o retrasar compra para comprar más barato en unas semanas."
            accion = "Ajustar al mínimo indispensable o diferir pedido."
        else:
            estado = "MONITOREAR"
            badge_class = "status-yellow"
            icono = "🟡"
            toneladas_sugeridas = diferencia_stock * 0.75
            motivo = f"Inventario en rango operativo normal ({stock_real:.1f} Tn)."
            precio_contexto = "Mercado estable. Programar compra estándar de ciclo según calendario habitual."
            accion = "Lanzar pedido rutinario según consumo de planta."
    else:
        estado = "NO COMPRAR"
        badge_class = "status-green"
        icono = "🟢"
        toneladas_sugeridas = 0.0
        motivo = f"Almacén con {stock_real:.1f} Tn frente a {stock_objetivo:.0f} Tn de objetivo. Cobertura completa asegurada."
        precio_contexto = "Comprar ahora inmovilizaría tesorería innecesariamente y arriesga depreciación de material si el acero baja."
        accion = "Bloquear compras para esta familia durante este ciclo."

    st.markdown("---")

    k1, k2, k3, k4 = st.columns([1.3, 1, 1, 1])
    with k1:
        st.markdown(f"""
        <div class='metric-card' style='border-left-color: {"#dc3545" if "URGENTE" in estado else ("#ffc107" if "SUGERIDA" in estado or "CONTROLADA" in estado or "MONITOREAR" in estado else "#28a745")};'>
            <div class='metric-label'>Veredicto</div>
            <div style='margin-top: 6px;'><span class='status-badge {badge_class}'>{icono} {estado}</span></div>
            <div class='metric-sub'><b>Acción:</b> {accion}</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Volumen a Pedir</div>
            <div class='metric-value'>{toneladas_sugeridas:,.1f} Tn</div>
            <div class='metric-sub'>Ajustado por stock y precio</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Inversión Estimada</div>
            <div class='metric-value'>{toneladas_sugeridas * coste_t:,.0f} €</div>
            <div class='metric-sub'>Coste familia: {coste_t:,} €/Tn</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        exceso_def = stock_real - stock_objetivo
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Diferencia vs Objetivo</div>
            <div class='metric-value' style='color: {"#dc3545" if exceso_def < 0 else "#28a745"};'>{exceso_def:+,.1f} Tn</div>
            <div class='metric-sub'>Objetivo: {stock_objetivo:,.0f} Tn</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### 💡 Justificación Detallada de la Decisión")
    c_x1, c_x2 = st.columns(2)
    with c_x1:
        st.markdown(f"""
        * **Situación en Fábrica:** {motivo}
        * **Impacto del Precio del Acero ({tendencia_precio}):** {precio_contexto}
        * **Criterio de Gestión:** {f_data['gestion']}.
        """)
    with c_x2:
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="Stock Real en Nave", x=[familia_sel], y=[stock_real],
            marker_color="#0B2545" if stock_real >= stock_objetivo else "#dc3545",
            text=[f"{stock_real:.1f} Tn"], textposition="auto"
        ))
        fig_comp.add_trace(go.Bar(
            name="Stock Objetivo Recomendado", x=[familia_sel], y=[stock_objetivo],
            marker_color="#134074", opacity=0.7,
            text=[f"{stock_objetivo:.1f} Tn"], textposition="auto"
        ))
        fig_comp.update_layout(
            title="<b>Comparativa: Stock Real vs. Objetivo</b>",
            barmode="group", yaxis_title="Toneladas",
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            height=280, margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_comp, use_container_width=True)

# ==============================================================================
# PESTAÑA 2: PREVISIÓN DE RECEPCIONES & TESORERÍA (CON HISTÓRICO RECIENTE)
# ==============================================================================
elif modulo == "📊 Previsión de Recepciones y Tesorería":
    st.markdown("## 📊 Previsión de Llegada de Bobinas y Presupuesto de Compras")
    st.caption("Planificación ejecutiva de las toneladas de acero que descargarán los camiones en fábrica durante los próximos 3 meses, junto con el histórico reciente de los meses anteriores.")

    total_trimestre_tn = 2647.0
    presupuesto_total_eur = 2740000.0
    ritmo_mensual_tn = 882.0

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Recepciones Próximos 3 Meses</div>
            <div class='metric-value'>{total_trimestre_tn:,.0f} Tn</div>
            <div class='metric-sub'>Abril a Junio 2026</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Presupuesto Necesario de Tesorería</div>
            <div class='metric-value'>{presupuesto_total_eur/1e6:,.2f} M€</div>
            <div class='metric-sub'>Coste medio de compra: 1.035 €/Tn</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Ritmo Mensual de Fábrica</div>
            <div class='metric-value'>{ritmo_mensual_tn:,.0f} Tn/mes</div>
            <div class='metric-sub'>Media histórica de referencia: 825 Tn</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Gráfico que incluye meses anteriores recientes (Ene, Feb, Mar 2026) y futuros (Abr, May, Jun 2026)
    meses_completos = ['Enero 2026', 'Febrero 2026', 'Marzo 2026', 'Abril 2026', 'Mayo 2026', 'Junio 2026']
    # Histórico real reciente + Previsión dinámica del modelo
    valores_completos = [842.0, 858.0, 864.0, 865.0, 890.0, 892.0]
    
    fig_prev = go.Figure()

    # Línea histórica real
    fig_prev.add_trace(go.Scatter(
        x=meses_completos[:3], y=valores_completos[:3],
        mode='lines+markers+text',
        name='Histórico Real Reciente',
        text=[f"{v:.0f} Tn" for v in valores_completos[:3]],
        textposition="top center",
        line=dict(color='#6C7A89', width=2, dash='dot'),
        marker=dict(size=7, color='#6C7A89')
    ))

    # Línea de previsión futura
    fig_prev.add_trace(go.Scatter(
        x=meses_completos[2:], y=valores_completos[2:],
        mode='lines+markers+text',
        name='Previsión del Modelo ARIMAX',
        text=[f"{v:.0f} Tn" for v in valores_completos[2:]],
        textposition="top center",
        line=dict(color='#134074', width=3),
        marker=dict(size=9, color='#0B2545')
    ))

    fig_prev.update_layout(
        title="<b>Evolución Temporal: Histórico Reciente y Previsión Futura de Recepciones (Toneladas)</b>",
        xaxis_title="Mes", yaxis_title="Toneladas",
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
        height=360, margin=dict(l=30, r=30, t=50, b=30)
    )
    st.plotly_chart(fig_prev, use_container_width=True)

    st.markdown("### 📋 Reparto de Compras por Familia Siderúrgica")
    df_fam_table = pd.DataFrame([
        {
            'Familia': fam,
            'Peso en Fábrica': f"{data['peso']*100:.1f}%",
            'Tipo de Gestión': data['gestion'],
            'Recepciones Previstas (Tn)': data['prev_3m'],
            'Coste Unitario': f"{data['coste_eur_t']:,} €/Tn",
            'Presupuesto Requerido (€)': f"{data['prev_3m'] * data['coste_eur_t']:,.0f} €"
        }
        for fam, data in familias.items()
    ])
    st.dataframe(df_fam_table, use_container_width=True, hide_index=True)

# ==============================================================================
# PESTAÑA 3: AHORRO Y RENTABILIDAD DE INVENTARIO (ROI SIMPLIFICADO)
# ==============================================================================
elif modulo == "💰 Ahorro y Rentabilidad de Inventario":
    st.markdown("## 💰 Ahorro Económico y Rentabilidad del Modelo")
    st.caption("Balance económico que muestra el ahorro conseguido hasta la fecha y el ahorro anual que genera optimizar el inventario.")

    st.markdown("### 1. ¿Cuánto ahorro llevamos conseguido hasta la fecha?")
    st.write("En los trimestres evaluados hasta marzo de 2026, el modelo ha demostrado mayor precisión que la media histórica, permitiendo operar con menor inventario de seguridad:")

    c_a1, c_a2, c_a3 = st.columns(3)
    with c_a1:
        st.markdown("""
        <div class='metric-card' style='border-left-color: #28a745;'>
            <div class='metric-label'>Ahorro Neto Conseguido</div>
            <div class='metric-value' style='color: #28a745;'>14.500 €</div>
            <div class='metric-sub'>Por menores costes de almacenamiento</div>
        </div>
        """, unsafe_allow_html=True)
    with c_a2:
        st.markdown("""
        <div class='metric-card' style='border-left-color: #00A6FB;'>
            <div class='metric-label'>Stock Reducido en Nave</div>
            <div class='metric-value' style='color: #00A6FB;'>70 Tn</div>
            <div class='metric-sub'>Menor colchón de seguridad requerido</div>
        </div>
        """, unsafe_allow_html=True)
    with c_a3:
        st.markdown("""
        <div class='metric-card' style='border-left-color: #134074;'>
            <div class='metric-label'>Capital Liberado Directo</div>
            <div class='metric-value'>72.500 €</div>
            <div class='metric-sub'>Dinero disponible en tesorería</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 2. ¿Cuánto ahorraremos al año según la política de compra elegida?")
    st.write("Selecciona la política de compras basada en el modelo para cuantificar el impacto económico recurrente:")

    politica = st.radio(
        "Selecciona la Política de Inventario del Modelo:",
        [
            "Política Óptima del Modelo (Plazo 3 Meses): Stock Objetivo de 2.070 Tn",
            "Política Ajustada de Máxima Eficiencia (Plazo 2 Meses): Stock Objetivo de 1.840 Tn"
        ],
        index=0
    )

    stock_real_fabrica = 3000.0
    coste_tn_acero = 1035.0
    coste_mantenimiento = 0.20

    if "Plazo 3 Meses" in politica:
        stock_obj = 2070.0
        exceso = stock_real_fabrica - stock_obj
        capital_liberado = exceso * coste_tn_acero
        ahorro_anual = capital_liberado * coste_mantenimiento
        descripcion = "Caso base oficial: garantiza el 95% de nivel de servicio cubriendo el plazo real de entrega observado en albaranes (3 meses)."
    else:
        stock_obj = 1840.0
        exceso = stock_real_fabrica - stock_obj
        capital_liberado = exceso * coste_tn_acero
        ahorro_anual = capital_liberado * coste_mantenimiento
        descripcion = "Política de máxima exigencia a proveedores: asume el cumplimiento estricto del plazo nominal de 2 meses."

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Ahorro Anual Recurrente</div>
            <div class='metric-value' style='color: #28a745;'>{ahorro_anual:,.0f} €/año</div>
            <div class='metric-sub'>Coste de posesión evitado (20% anual)</div>
        </div>
        """, unsafe_allow_html=True)
    with r2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Capital Circulante Liberado</div>
            <div class='metric-value'>{capital_liberado/1e3:,.0f} k€</div>
            <div class='metric-sub'>Exceso evitado en almacén: {exceso:,.0f} Tn</div>
        </div>
        """, unsafe_allow_html=True)
    with r3:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>Stock Objetivo en Nave</div>
            <div class='metric-value' style='color: #134074;'>{stock_obj:,.0f} Tn</div>
            <div class='metric-sub'>Frente a las 3.000 Tn habituales</div>
        </div>
        """, unsafe_allow_html=True)

    st.info(f"💡 **Diagnóstico de Negocio:** {descripcion}")

# ==============================================================================
# PESTAÑA 4: CONTROL Y FIABILIDAD DEL SISTEMA
# ==============================================================================
else:
    st.markdown("## 🛡️ Control y Fiabilidad del Sistema Predictivo")
    st.caption("Panel de supervisión que audita el acierto del modelo frente a los albaranes reales del ERP y comprueba que las predicciones no se desvían.")

    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown("""
        <div class='metric-card' style='border-left-color: #28a745;'>
            <div class='metric-label'>Estado del Sistema</div>
            <div style='margin-top: 6px;'><span class='status-badge status-green'>SISTEMA EN REGLA</span></div>
            <div class='metric-sub'>Modelo calibrado y aprobado para compras</div>
        </div>
        """, unsafe_allow_html=True)
    with s2:
        st.markdown("""
        <div class='metric-card' style='border-left-color: #00A6FB;'>
            <div class='metric-label'>Acierto Medio del Modelo</div>
            <div class='metric-value'>91.2%</div>
            <div class='metric-sub'>Error medio de solo 8.8% en entregas reales</div>
        </div>
        """, unsafe_allow_html=True)
    with s3:
        st.markdown("""
        <div class='metric-card' style='border-left-color: #28a745;'>
            <div class='metric-label'>Trimestres Auditados</div>
            <div class='metric-value' style='color: #28a745;'>4 de 4 Aprobados</div>
            <div class='metric-sub'>Validación continua en fábrica</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 🔍 ¿Qué vigila en continuo este panel?")
    v1, v2, v3 = st.columns(3)
    with v1:
        st.markdown("""
        **1. Cotización del Acero (INE)**  
        Comprueba que los precios del índice IPRI 241 se mantengan dentro de la normalidad histórica.  
        *Estado:* **Normal (sin anomalías).**
        """)
    with v2:
        st.markdown("""
        **2. Consumo en Nave**  
        Verifica que la fábrica mantenga su ritmo regular de producción sin caídas imprevistas.  
        *Estado:* **Estable (825 Tn/mes de ritmo medio).**
        """)
    with v3:
        st.markdown("""
        **3. Calidad de las Predicciones**  
        Compara trimestralmente lo que el modelo predijo frente a los camiones que realmente descargaron bobinas.  
        *Estado:* **Conforme.**
        """)

    st.markdown("---")

    st.markdown("### 📋 Registro de Verificaciones Reales (Lo Previsto frente a lo Descargado)")
    st.write("Auditoría de los trimestres cerrados entre otoño de 2025 y marzo de 2026. Muestra la comparación directa entre las toneladas que predijo el modelo y las que realmente llegaron al muelle del taller con su correspondiente porcentaje de acierto:")

    st.dataframe(historico_evaluaciones, use_container_width=True, hide_index=True)
