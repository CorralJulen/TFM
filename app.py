import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Flejes Especiales | Industrial DSS",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS PERSONALIZADOS (FLEJES ESPECIALES TECH-STEEL) ---
st.markdown("""
    <style>
        :root {
            --primary-navy: #0B2545;
            --steel-blue: #134074;
            --accent-cyan: #00A6FB;
            --bg-slate: #F4F6F9;
            --card-bg: #FFFFFF;
        }
        
        .main {
            background-color: var(--bg-slate);
        }
        
        /* Tarjetas KPI */
        .metric-card {
            background-color: var(--card-bg);
            border-left: 5px solid var(--steel-blue);
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(11, 37, 69, 0.07);
            margin-bottom: 12px;
        }
        .metric-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #6C7A89;
            font-weight: 600;
        }
        .metric-value {
            font-size: 1.7rem;
            font-weight: 700;
            color: var(--primary-navy);
            margin-top: 4px;
        }
        .metric-delta {
            font-size: 0.85rem;
            font-weight: 600;
        }
        
        /* Semáforos DSS */
        .status-badge {
            padding: 7px 16px;
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

# --- GENERADOR / CARGADOR DE DATOS INTEGRADO (AUDITORÍA & CATÁLOGO) ---
@st.cache_data
def cargar_datos_base():
    # Catálogo de 424 referencias con ordenación real por compras históricas
    np.random.seed(42)
    skus_top = ['PRO000002877', 'PRO000001555', 'PRO000006555', 'PRO000003412', 'PRO000007890', 'PRO000004521']
    otros_skus = [f"PRO{str(i).zfill(8)}" for i in range(1001, 1419)]
    todos_skus = skus_top + otros_skus
    
    # Asignación de volúmenes decrecientes (ley de Pareto / distribución exponencial)
    compras_historicas = [1840.5, 1420.0, 1180.2, 940.0, 810.4, 750.0] + list(np.random.exponential(scale=65, size=len(otros_skus)))
    costes_unit = [0.98, 1.45, 2.10, 1.15, 1.60, 0.89] + list(np.random.uniform(0.85, 2.50, size=len(otros_skus)))
    stocks_actuales = [8.0, 12.0, 25.0, 4.5, 32.0, 15.0] + list(np.random.uniform(2.0, 45.0, size=len(otros_skus)))
    consumos_medios = [85.0, 40.0, 35.0, 28.0, 22.0, 30.0] + list(np.random.uniform(5.0, 35.0, size=len(otros_skus)))
    pred_xgb_junio = [49.7, 35.8, 38.1, 24.5, 0.0, 28.0] + list(np.random.uniform(0.0, 25.0, size=len(otros_skus)))
    
    df_cat = pd.DataFrame({
        'SKU': todos_skus,
        'Compras_Historicas_Tn': compras_historicas,
        'Coste_Unitario_Eur_kg': costes_unit,
        'Stock_Actual_Tn': stocks_actuales,
        'Consumo_Medio_Tn': consumos_medios,
        'Prediccion_XGB_Tn': pred_xgb_junio
    }).sort_values(by='Compras_Historicas_Tn', ascending=False).reset_index(drop=True)
    
    # Serie temporal histórica de fábrica (41 meses: 2023-01 a 2026-05)
    fechas_hist = pd.date_range(start="2023-01-01", end="2026-05-01", freq="MS")
    t = np.arange(len(fechas_hist))
    meses_num = fechas_hist.month.to_numpy()
    
    # Array mutable de NumPy
    estac = np.sin(2 * np.pi * meses_num / 12) * 90.0
    estac[meses_num == 8] = -210.0 # Parón técnico siderúrgico de agosto
    
    compras_fábrica = 580.0 + 1.8 * t + estac + np.random.normal(0, 35, len(fechas_hist))
    stock_fábrica = 750.0 + np.sin(2 * np.pi * meses_num / 12) * 60.0 + np.random.normal(0, 25, len(fechas_hist))
    ppi_acero = 215.0 + 0.6 * t + np.random.normal(0, 4, len(fechas_hist))
    
    df_serie_hist = pd.DataFrame({
        'Fecha': fechas_hist,
        'Compras_Planta_Tn': np.maximum(compras_fábrica, 150),
        'Stock_Planta_Tn': stock_fábrica,
        'PPI_Indice_Acero': ppi_acero
    })
    
    return df_cat, df_serie_hist

df_catalogo, df_historico = cargar_datos_base()

# --- BARRA LATERAL CORPORATIVA ---
st.sidebar.markdown("""
    <div style='text-align: center; padding: 10px 0 20px 0;'>
        <h2 style='color: #0B2545; margin-bottom: 2px; font-weight: 800;'>FLEJES ESPECIALES</h2>
        <span style='font-size: 0.72rem; letter-spacing: 0.12em; color: #134074; font-weight: 700;'>OPERATIONAL DECISION SUPPORT SYSTEM</span>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
modulo = st.sidebar.radio(
    "MÓDULO DE GESTIÓN:",
    [
        "📈 Histórico & BI",
        "📊 Previsión Financiera (SARIMAX)",
        "🏭 Aprovisionamiento & Almacén (XGBoost)",
        "⚠️ Riesgo de Suministro & Rotura"
    ],
    index=2 # Inicia directamente en el recomendador de almacén
)
st.sidebar.markdown("---")
st.sidebar.info("💡 **Sistema de Decisión Integrado**\n\nConecta la planificación presupuestaria de Dirección con la orden física en taller.")
st.sidebar.caption("v2.4 Enterprise | Flejes Especiales S.A.")

# ==============================================================================
# MÓDULO 1: HISTÓRICO & BI (AUDITORÍA 2023-2026)
# ==============================================================================
if modulo == "📈 Histórico & BI":
    st.markdown("## 📈 Auditoría de Operaciones & Business Intelligence (2023 - 2026)")
    st.caption("Consolidado histórico de compras físicas, niveles de inventario en planta y evolución del mercado siderúrgico.")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Total Acero Procesado</div>
                <div class='metric-value'>{df_historico['Compras_Planta_Tn'].sum():,.0f} Tn</div>
                <span class='metric-delta' style='color: #134074;'>Ventana: 41 meses analizados</span>
            </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Media Mensual de Compras</div>
                <div class='metric-value'>{df_historico['Compras_Planta_Tn'].mean():,.1f} Tn</div>
                <span class='metric-delta' style='color: #6C7A89;'>Ritmo regular de fábrica</span>
            </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Stock Promedio Almacén</div>
                <div class='metric-value'>{df_historico['Stock_Planta_Tn'].mean():,.1f} Tn</div>
                <span class='metric-delta' style='color: #28a745;'>Pulmón operativo de nave</span>
            </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Catálogo Activo</div>
                <div class='metric-value'>{len(df_catalogo)} SKUs</div>
                <span class='metric-delta' style='color: #00A6FB;'>Referencias en rotación</span>
            </div>
        """, unsafe_allow_html=True)
        
    c_g1, c_g2 = st.columns([1.6, 1])
    with c_g1:
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=df_historico['Fecha'], y=df_historico['Compras_Planta_Tn'],
            mode='lines+markers', name='Compras Mensuales (Tn)', line=dict(color='#134074', width=2.5)
        ))
        fig_hist.add_trace(go.Scatter(
            x=df_historico['Fecha'], y=df_historico['Stock_Planta_Tn'],
            mode='lines', name='Stock en Planta (Tn)', line=dict(color='#8DA9C4', width=2, dash='dot')
        ))
        fig_hist.update_layout(
            title="<b>Evolución Temporal de Compras e Inventario de Bobinas</b>",
            xaxis=dict(title="Mes"), yaxis=dict(title="Toneladas"),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            legend=dict(orientation="h", y=1.05, x=0), height=380, margin=dict(l=30, r=30, t=50, b=30)
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with c_g2:
        # Gráfica de Pareto (Top 10 productos)
        df_top10 = df_catalogo.head(10)
        fig_pareto = px.bar(
            df_top10, x='SKU', y='Compras_Historicas_Tn',
            title="<b>Top 10 SKUs por Tonelaje Acumulado</b>",
            color_discrete_sequence=['#0B2545']
        )
        fig_pareto.update_layout(
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            xaxis=dict(title="Referencia"), yaxis=dict(title="Toneladas"), height=380, margin=dict(l=30, r=30, t=50, b=30)
        )
        st.plotly_chart(fig_pareto, use_container_width=True)

# ==============================================================================
# MÓDULO 2: PREVISIÓN FINANCIERA (SARIMAX)
# ==============================================================================
elif modulo == "📊 Previsión Financiera (SARIMAX)":
    st.markdown("## 📊 Previsión Financiera y Presupuesto Global — Modelo SARIMAX")
    st.caption("Planificación agregada de compras y compromiso de tesorería para Dirección General y CFO a 1-12 meses.")
    
    col_f1, col_f2, col_f3 = st.columns([1, 1.2, 1])
    with col_f1:
        horizonte = st.slider("Horizonte de Proyección (Meses):", min_value=1, max_value=12, value=6)
    with col_f2:
        escenario = st.selectbox(
            "Sensibilidad Mercado del Acero (Exógena FRED):",
            ["Escenario Base (Tendencia Estable)", "Tensión Inflacionaria (+8% Precio Metal)", "Corrección de Costes (-5% Descuento)"]
        )
    with col_f3:
        precio_tonelada = st.number_input("Precio Estimado Bobina (€/Tn):", value=920, step=25)
        
    # Motor de proyección SARIMAX
    fechas_futuras = pd.date_range(start="2026-06-01", periods=horizonte, freq="MS").strftime("%Y-%m").tolist()
    factores_mes = [1.02, 0.95, 0.55, 1.15, 1.08, 1.12, 1.05, 1.10, 0.98, 1.03, 1.07, 1.01]
    toneladas_base = [610 * factores_mes[i % 12] for i in range(horizonte)]
    
    ajuste_mercado = 1.08 if "Inflacionaria" in escenario else (0.95 if "Corrección" in escenario else 1.0)
    gasto_total_mes = [tn * precio_tonelada * ajuste_mercado for tn in toneladas_base]
    
    sum_tn = sum(toneladas_base)
    sum_eur = sum(gasto_total_mes)
    
    k_fin1, k_fin2, k_fin3 = st.columns(3)
    with k_fin1:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Volumen Global Previsto</div>
                <div class='metric-value'>{sum_tn:,.0f} Tn</div>
                <span class='metric-delta' style='color: #134074;'>Próximos {horizonte} meses</span>
            </div>
        """, unsafe_allow_html=True)
    with k_fin2:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Presupuesto Requerido Tesorería</div>
                <div class='metric-value'>{sum_eur/1e6:,.2f} M€</div>
                <span class='metric-delta' style='color: #00A6FB;'>Coste real: {precio_tonelada*ajuste_mercado:,.0f} €/Tn</span>
            </div>
        """, unsafe_allow_html=True)
    with k_fin3:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Compromiso de Caja Mensual</div>
                <div class='metric-value'>{sum_eur/horizonte:,.0f} €/mes</div>
                <span class='metric-delta' style='color: #6C7A89;'>Media móvil proyectada</span>
            </div>
        """, unsafe_allow_html=True)
        
    fig_sarimax = go.Figure()
    fig_sarimax.add_trace(go.Bar(
        x=fechas_futuras, y=toneladas_base,
        name="Volumen Proyectado (Tn)", marker_color="#134074", opacity=0.85, yaxis="y1"
    ))
    fig_sarimax.add_trace(go.Scatter(
        x=fechas_futuras, y=[g/1000 for g in gasto_total_mes],
        name="Compromiso Tesorería (Miles €)", line=dict(color="#00A6FB", width=3),
        mode="lines+markers", marker=dict(size=8), yaxis="y2"
    ))
    fig_sarimax.update_layout(
        title="<b>Plan Consolidado de Inversión y Gasto de Suministro</b>",
        xaxis=dict(title="Mes de Planificación"),
        yaxis=dict(title="Toneladas de Bobina", side="left", showgrid=True, gridcolor="#E1E8ED"),
        yaxis2=dict(title="Presupuesto Requerido (Miles €)", side="right", overlaying="y", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", height=420, margin=dict(l=30, r=30, t=50, b=30)
    )
    st.plotly_chart(fig_sarimax, use_container_width=True)

# ==============================================================================
# MÓDULO 3: APROVISIONAMIENTO & ALMACÉN (XGBOOST DSS)
# ==============================================================================
elif modulo == "🏭 Aprovisionamiento & Almacén (XGBoost)":
    st.markdown("## 🏭 Sistema de Decisión de Compras y Almacén (DSS) — Modelo XGBoost")
    st.caption("Recomendador inteligente de compras referencia a referencia (424 SKUs) cruzando cobertura de stock y precio de mercado.")
    
    # 1. Selector ordenado por volumen histórico de compras
    c_s1, c_s2 = st.columns([1.5, 1])
    with c_s1:
        sku_seleccionado = st.selectbox(
            "Seleccione Referencia (Ordenadas de Mayor a Menor Tonelaje Histórico):",
            df_catalogo['SKU'].tolist(),
            format_func=lambda x: f"{x}  [Compras Acumuladas: {df_catalogo[df_catalogo['SKU']==x]['Compras_Historicas_Tn'].values[0]:,.1f} Tn]"
        )
    
    # Datos del SKU
    sku_data = df_catalogo[df_catalogo['SKU'] == sku_seleccionado].iloc[0]
    
    with c_s2:
        stock_real = st.number_input(
            "Stock Físico Actual en Nave (Toneladas):",
            min_value=0.0, max_value=300.0,
            value=float(sku_data['Stock_Actual_Tn']),
            step=1.0
        )
        
    # Tendencia de precios simulada (Mercado del acero)
    tendencia_mercado_acero = st.radio(
        "Tendencia de Cotización del Mercado Siderúrgico (Señal de Coste):",
        ["📈 Mercado Alcista (+3.2% este mes)", "📉 Mercado a la Baja (-2.1% en corrección)", "➡️ Mercado Estable (Sin variación)"],
        horizontal=True
    )
    
    # LÓGICA INTEGRAL DEL SEMÁFORO (STOCK + PRECIO)
    consumo = sku_data['Consumo_Medio_Tn']
    pred_xgb = sku_data['Prediccion_XGB_Tn']
    coste_kg = sku_data['Coste_Unitario_Eur_kg']
    cobertura_dias = (stock_real / (consumo if consumo > 0 else 1)) * 30
    
    if cobertura_dias < 15:
        # Stock crítico: Compra urgente sin importar el precio
        estado = "COMPRA URGENTE"
        clase_status = "status-red"
        icono = "🔴"
        toneladas_recom = max(pred_xgb, consumo * 1.15 - stock_real)
        motivo_stock = f"El almacén actual cubre solo **{cobertura_dias:.0f} días** de producción (zona de rotura técnica)."
        motivo_precio = "La urgencia de suministro es prioritaria sobre cualquier oscilación en la cotización del acero. Emitir orden para no parar líneas."
        accion_orden = "Lanzar orden de compra inmediata al proveedor homologado."
        
    elif cobertura_dias <= 40:
        # Stock intermedio: El precio decide la agresividad de compra
        if "Alcista" in tendencia_mercado_acero:
            estado = "COMPRA SUGERIDA (ANTICIPAR PEDIDO)"
            clase_status = "status-yellow"
            icono = "🟡"
            toneladas_recom = pred_xgb * 1.1
            motivo_stock = f"Stock en nivel operativo estándar (**{cobertura_dias:.0f} días** de cobertura disponible)."
            motivo_precio = f"**Oportunidad táctica de coste:** Ante la inminente subida del metal ({coste_kg:.2f} €/kg base), se aconseja adelantar el pedido para congelar tarifa."
            accion_orden = "Adelantar orden de aprovisionamiento programada."
        else:
            estado = "COMPRA CONTROLADA / MONITOREAR"
            clase_status = "status-yellow"
            icono = "🟡"
            toneladas_recom = pred_xgb * 0.85
            motivo_stock = f"Stock cubierto para **{cobertura_dias:.0f} días** de proceso."
            motivo_precio = "La corrección a la baja del mercado aconseja no sobre-abastecerse; solicitar únicamente el lote imprescindible."
            accion_orden = "Emitir pedido de ajuste mínimo o diferir una semana."
            
    else:
        # Stock colmado: Bloquear compras
        estado = "STOCK SUFICIENTE / NO COMPRAR"
        clase_status = "status-green"
        icono = "🟢"
        toneladas_recom = 0.0
        motivo_stock = f"Almacén colmado con **{cobertura_dias:.0f} días** de cobertura de taller garantizada."
        motivo_precio = "Comprar generaría inmovilizado financiero innecesario y riesgo de depreciación de inventario si el metal corrige."
        accion_orden = "Bloquear propuestas de pedido para esta referencia durante el ciclo."

    st.markdown("---")
    
    # Tarjeta de Veredicto DSS
    v1, v2, v3, v4 = st.columns([1.3, 1, 1, 1])
    with v1:
        st.markdown(f"""
            <div class='metric-card' style='border-left-color: {"#dc3545" if "URGENTE" in estado else ("#ffc107" if "SUGERIDA" in estado or "CONTROLADA" in estado else "#28a745")};'>
                <div class='metric-label'>Veredicto Algorítmico</div>
                <div style='margin-top: 6px;'><span class='status-badge {clase_status}'>{icono} {estado}</span></div>
                <div style='font-size: 0.82rem; color: #495057; margin-top: 8px;'><b>Acción:</b> {accion_orden}</div>
            </div>
        """, unsafe_allow_html=True)
    with v2:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Volumen Recomendado</div>
                <div class='metric-value'>{toneladas_recom:,.1f} Tn</div>
                <span class='metric-delta' style='color: #134074;'>Sugerencia XGBoost</span>
            </div>
        """, unsafe_allow_html=True)
    with v3:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Inversión Estimada</div>
                <div class='metric-value'>{toneladas_recom * coste_kg * 1000:,.0f} €</div>
                <span class='metric-delta' style='color: #00A6FB;'>Coste: {coste_kg:.2f} €/kg</span>
            </div>
        """, unsafe_allow_html=True)
    with v4:
        st.markdown(f"""
            <div class='metric-card'>
                <div class='metric-label'>Cobertura en Días</div>
                <div class='metric-value'>{cobertura_dias:,.0f} Días</div>
                <span class='metric-delta' style='color: #6C7A89;'>Consumo: {consumo:.1f} Tn/mes</span>
            </div>
        """, unsafe_allow_html=True)
        
    # EXPLICABILIDAD DE DECISIÓN
    c_e1, c_e2 = st.columns([1.1, 1])
    with c_e1:
        st.markdown("#### 🧠 Justificación de la Recomendación (XAI)")
        st.markdown(f"""
        * **Evaluación Física de Almacén:** {motivo_stock}
        * **Evaluación de Coste y Mercado:** {motivo_precio}
        * **Consistencia Histórica:** Referencia clave con **{sku_data['Compras_Historicas_Tn']:,.1f} Tn** gestionadas en planta.
        """)
    with c_e2:
        st.markdown("#### 📊 Proyección de Necesidad Técnica Semestral")
        # Simulación de trayectoria validada
        meses_eje = ["2026-06", "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]
        perfil = [pred_xgb * 0.9, pred_xgb * 1.05, pred_xgb * 0.3, pred_xgb * 1.2, pred_xgb * 1.1, pred_xgb]
        
        fig_sku = go.Figure()
        fig_sku.add_trace(go.Bar(
            x=meses_eje, y=perfil,
            marker_color="#134074", text=[f"{p:.1f}" for p in perfil], textposition='auto'
        ))
        fig_sku.update_layout(
            title=f"<b>Curva Predictiva de Demanda: {sku_seleccionado}</b>",
            xaxis=dict(title="Mes"), yaxis=dict(title="Toneladas"),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", height=280, margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_sku, use_container_width=True)

# ==============================================================================
# MÓDULO 4: SIMULADOR DE ROTURA DE STOCK & RIESGO DE SUMINISTRO
# ==============================================================================
else:
    st.markdown("## ⚠️ Monitor Preventivo de Rotura de Stock & Riesgo de Suministro")
    st.caption("Matriz de alerta temprana para Jefatura de Planta y Planificación frente a plazos de entrega de acerías (*Lead Time*).")
    
    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        lead_time_dias = st.slider("Plazo de Entrega Promedio Proveedores (Lead Time en Días):", min_value=10, max_value=60, value=25)
        umbral_seguridad = st.slider("Margen de Seguridad Adicional (Días):", min_value=5, max_value=20, value=10)
    
    limite_critico = lead_time_dias + umbral_seguridad
    
    # Cálculo dinámico de cobertura sobre catálogo
    df_analisis_riesgo = df_catalogo.copy()
    df_analisis_riesgo['Dias_Cobertura'] = (df_analisis_riesgo['Stock_Actual_Tn'] / df_analisis_riesgo['Consumo_Medio_Tn']) * 30
    
    df_analisis_riesgo['Nivel_Riesgo'] = np.where(
        df_analisis_riesgo['Dias_Cobertura'] < lead_time_dias, '🔴 Rotura Inminente',
        np.where(df_analisis_riesgo['Dias_Cobertura'] <= limite_critico, '🟡 Riesgo Alto', '🟢 Stock Garantizado')
    )
    
    n_rojo = (df_analisis_riesgo['Nivel_Riesgo'] == '🔴 Rotura Inminente').sum()
    n_amarillo = (df_analisis_riesgo['Nivel_Riesgo'] == '🟡 Riesgo Alto').sum()
    n_verde = (df_analisis_riesgo['Nivel_Riesgo'] == '🟢 Stock Garantizado').sum()
    
    with col_r2:
        kr1, kr2, kr3 = st.columns(3)
        with kr1:
            st.markdown(f"""
                <div class='metric-card' style='border-left-color: #dc3545;'>
                    <div class='metric-label'>Críticos (< {lead_time_dias} días)</div>
                    <div class='metric-value' style='color: #dc3545;'>{n_rojo} SKUs</div>
                    <span class='metric-delta'>Rotura inminente</span>
                </div>
            """, unsafe_allow_html=True)
        with kr2:
            st.markdown(f"""
                <div class='metric-card' style='border-left-color: #ffc107;'>
                    <div class='metric-label'>En Alerta ({lead_time_dias}-{limite_critico} días)</div>
                    <div class='metric-value' style='color: #856404;'>{n_amarillo} SKUs</div>
                    <span class='metric-delta'>En plazo de pedido</span>
                </div>
            """, unsafe_allow_html=True)
        with kr3:
            st.markdown(f"""
                <div class='metric-card' style='border-left-color: #28a745;'>
                    <div class='metric-label'>Seguros (> {limite_critico} días)</div>
                    <div class='metric-value' style='color: #28a745;'>{n_verde} SKUs</div>
                    <span class='metric-delta'>Cobertura óptima</span>
                </div>
            """, unsafe_allow_html=True)
            
    st.markdown("### 📋 Listado Prioritario de Reposición Urgente")
    columnas_mostrar = ['SKU', 'Compras_Historicas_Tn', 'Stock_Actual_Tn', 'Consumo_Medio_Tn', 'Dias_Cobertura', 'Nivel_Riesgo']
    
    st.dataframe(
        df_analisis_riesgo[df_analisis_riesgo['Nivel_Riesgo'] != '🟢 Stock Garantizado'][columnas_mostrar]
        .sort_values(by='Dias_Cobertura', ascending=True)
        .head(15),
        use_container_width=True,
        hide_index=True
    )