"""Flejes Especiales · Sistema de soporte a la decisión de compras de bobina de acero (prototipo del TFM, ESIC).
import sys
from pathlib import Path

# Agrega el directorio donde está este archivo al path de búsqueda
sys.path.append(str(Path(__file__).parent.resolve()))

Pantallas por usuario: compras (qué pedir), finanzas (recepciones y pagos), dirección (ahorro de inventario) y
analista de datos (panel del modelo). Los cálculos están en nucleo.py.

Ejecutar en local:  streamlit run app.py
"""
import sys
from pathlib import Path

# Agrega el directorio donde está este archivo al path de búsqueda
sys.path.append(str(Path(__file__).parent.resolve()))

import nucleo as n
from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import nucleo as n

st.set_page_config(page_title='Flejes Especiales · Compras de bobina', page_icon='⚙️', layout='wide',
                   initial_sidebar_state='expanded')

# --- Estilo (identidad visual de la versión anterior) --------------------------------------------
NAVY, STEEL, GRIS, GRID = '#0B2545', '#134074', '#b9b8b2', '#e6e8ec'
FAM_COLOR = dict(zip(n.FAMILIAS, ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4']))
SEMAFORO = {'urgente': ('🔴', 'COMPRA URGENTE', 'status-red', '#dc3545'),
            'sugerida': ('🟡', 'PEDIR', 'status-yellow', '#e0a800'),
            'no comprar': ('🟢', 'NO PEDIR', 'status-green', '#28a745')}

st.markdown("""
<style>
  .block-container {padding-top: 2rem; max-width: 1200px;}
  h1 {color: #0B2545; font-size: 1.85rem !important;}
  .sub {color: #495057; font-size: 1.02rem; margin-top: -0.5rem; margin-bottom: 1.3rem;}
  .card {background: #fff; border-left: 5px solid #134074; padding: 14px 18px; border-radius: 8px;
         box-shadow: 0 2px 8px rgba(11,37,69,0.08); margin-bottom: 12px;}
  .card .lab {font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.07em; color: #6C7A89; font-weight: 600;}
  .card .val {font-size: 1.75rem; font-weight: 700; color: #0B2545; margin-top: 4px; line-height: 1.2;}
  .card .sub2 {font-size: 0.86rem; color: #495057; margin-top: 4px;}
  .grande {font-size: 1.7rem; font-weight: 700; color: #0B2545;}
  .badge {padding: 5px 13px; border-radius: 20px; font-weight: 700; display: inline-block; font-size: 0.86rem;}
  .status-green {background: #D4EDDA; color: #155724; border: 1px solid #C3E6CB;}
  .status-yellow {background: #FFF3CD; color: #856404; border: 1px solid #FFEEBA;}
  .status-red {background: #F8D7DA; color: #721C24; border: 1px solid #F5C6CB;}
  .status-blue {background: #DCEBFA; color: #134074; border: 1px solid #C2DAF3;}
  .fila {background: #fff; border: 1px solid #e3e6ea; border-left: 5px solid; border-radius: 8px; padding: 12px 16px;
         margin-bottom: 10px;}
  .fila .fam {font-weight: 700; color: #0B2545; font-size: 1.05rem; margin-bottom: 4px;}
  .fila .cant {font-size: 1.6rem; font-weight: 700; color: #0B2545;}
  .fila .por {color: #495057; font-size: 0.92rem;}
  .nota {color: #6C7A89; font-size: 0.85rem;}
  .marca {text-align:center; padding: 4px 0 14px 0;}
</style>
""", unsafe_allow_html=True)


def num(x, dec=0):
    if x is None or pd.isna(x):
        return '–'
    return f'{x:,.{dec}f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def eur(x):
    return f'{num(x)} €'


def meur(x):
    return f'{num(x / 1e6, 2)} M€'


MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
         'noviembre', 'diciembre']


def mes(d, corto=False):
    m = MESES[d.month - 1]
    return f'{m[:3]}-{d:%y}' if corto else f'{m} {d.year}'


def card(col, etiqueta, valor, sub='', color=STEEL):
    col.markdown(f"<div class='card' style='border-left-color:{color}'><div class='lab'>{etiqueta}</div>"
                 f"<div class='val'>{valor}</div><div class='sub2'>{sub}</div></div>", unsafe_allow_html=True)


def grafico(fig, alto=340, eje='toneladas', leyenda=True, y0=True):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor='#ffffff', paper_bgcolor='#ffffff',
                      font=dict(family='system-ui, -apple-system, Segoe UI, sans-serif', color='#495057', size=13),
                      separators=',.', showlegend=leyenda, hoverlabel=dict(bgcolor='white'),
                      legend=dict(orientation='h', y=1.02, yanchor='bottom', x=0, title=None))
    fig.update_xaxes(showgrid=False, linecolor='#c3c2b7', tickfont=dict(color='#6C7A89'))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, rangemode='tozero' if y0 else 'normal', title=eje,
                     tickformat=',.0f', title_font=dict(size=12, color='#6C7A89'), tickfont=dict(color='#6C7A89'))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


def ejes_mes(fig, fechas, paso=1):
    v = pd.DatetimeIndex(fechas)[::paso]
    fig.update_xaxes(tickvals=v, ticktext=[mes(d, True) for d in v])


# --- Datos y modelo -----------------------------------------------------------------------------
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def precio_acero():
    try:
        return n.descargar_ipri_ine(), 'API del INE'
    except Exception:
        return n.cargar_ipri_csv(), 'copia local del INE'


@st.cache_resource(show_spinner='Actualizando la previsión con el último mes cerrado…')
def calcular(vals, fechas):
    ipri = pd.Series(vals, index=pd.to_datetime(fechas))
    R = n.cargar_recepciones()
    corte = R.index.max()
    return R, n.prever(R['Total'], ipri, corte), n.simular_monitorizacion(R['Total'], R, ipri, corte, n.cargar_ficha())


FICHA = n.cargar_ficha()
IPRI, FUENTE = precio_acero()
R, P, MON = calcular(tuple(float(v) for v in IPRI.values), tuple(IPRI.index.strftime('%Y-%m-%d')))
Y, CORTE = R['Total'], R.index.max()
PESOS = n.pesos_familia(R, CORTE)
STOCK = n.cargar_stock()
COSTE_T = 1035   # coste medio de compra abr-2025 a mar-2026 (albaranes del ERP)
MESES_PREV = P['mensual'].index
CTRL = n.controles(P['ajuste'], FICHA)
ALERTAS_DATOS = n.alertas_datos(Y, P['X'], P['Xf'], CORTE)
ESTADO, ALERTAS = n.estado_monitorizacion(MON, CTRL, ALERTAS_DATOS, FICHA)
ESTADO_ESTILO = {'En seguimiento': ('🔵', 'status-blue'), 'Correcto': ('🟢', 'status-green'),
                 'Vigilar': ('🟡', 'status-yellow'), 'Revisar': ('🔴', 'status-red')}
PEND = n.cargar_pendiente()                     # pedidos abiertos en la fecha de la extracción del ERP
FOTO = PEND['fecha_foto']
CIERRE_STOCK = STOCK.index[STOCK.index <= FOTO.to_period('M').to_timestamp()][-1]   # cierre del mes de la foto
FECHA_FOTO = (CIERRE_STOCK + pd.offsets.MonthEnd(0)).date()
ATRASADO = {f: v for f, v in PEND['atrasado_t'].items() if v >= 1}


def ajustes():
    return st.session_state.get('plazo_v', 3), st.session_state.get('ns_v', 0.95)


def entrada_actual():
    if 'entrada' not in st.session_state:   # se conserva al cambiar de pantalla
        st.session_state.entrada = pd.DataFrame({
            'Familia': n.FAMILIAS,
            'En almacén (t)': STOCK.loc[CIERRE_STOCK, n.FAMILIAS].round(0).values,
            'Pedido y sin llegar (t)': [round(PEND['pendiente_t'][f]) for f in n.FAMILIAS]})
    return st.session_state.entrada


def propuesta(entrada, plazo, ns):
    filas = []
    for _, r in entrada.iterrows():
        f = r['Familia']
        prev = P['totales'][plazo]['prevision'] * PESOS[f]
        ss = n.seguridad(f, plazo, ns)
        stock, pend = float(r['En almacén (t)']), float(r['Pedido y sin llegar (t)'])
        cant, _, estado = n.recomendar(prev, ss, stock, pend)
        roll = R.loc[:CORTE, f].rolling(plazo).sum().dropna()
        filas.append(dict(familia=f, prev=prev, ss=ss, stock=stock, pend=pend, cant=cant, estado=estado,
                          pequena=f not in n.FAMILIAS_GRANDES, media_h=roll.mean(), p90_h=roll.quantile(0.9)))
    return pd.DataFrame(filas).set_index('familia')


def barra_lateral():
    with st.sidebar:
        st.markdown("<div class='marca'><h2 style='color:#0B2545;margin-bottom:0;font-weight:800'>FLEJES ESPECIALES</h2>"
                    "<span style='font-size:0.72rem;letter-spacing:0.12em;color:#134074;font-weight:700'>"
                    "SOPORTE A LA DECISIÓN DE COMPRAS</span></div>", unsafe_allow_html=True)
        st.markdown('---')
        st.markdown(f"**Datos actualizados**  \nRecepciones (ERP): hasta {mes(CORTE)}  \n"
                    f"Pedidos abiertos (ERP): {FOTO:%d/%m/%Y}  \nPrecio del acero (INE): hasta {mes(IPRI.index.max())}  \n"
                    f"Inventario (Business Central): hasta {mes(STOCK.index.max())}")
        ic, _ = ESTADO_ESTILO[ESTADO]
        st.markdown(f"**Estado del modelo:** {ic} {ESTADO}")
        st.markdown('---')
        st.caption('Prototipo del TFM (ESIC) con datos reales del pasado. Su validación con datos nuevos es el objetivo del '
                   'piloto (capítulo 7). Propone decisiones; el pedido lo decide siempre el responsable de compras.')


# ================================================================================================
# RESUMEN DEL MES
# ================================================================================================
def bloque(titulo, grande, nota, pagina, enlace):
    with st.container(border=True):
        st.markdown(f'#### {titulo}')
        st.markdown(f"<div class='grande'>{grande}</div><div class='nota'>{nota}</div>", unsafe_allow_html=True)
        st.page_link(pagina, label=enlace, icon='➡️')


def pag_resumen():
    st.title('Resumen del mes')
    st.markdown(f"<div class='sub'>Previsión desde {mes(MESES_PREV[0])}. Lo más importante de cada área; entra en tu "
                f"pantalla para ver el detalle.</div>", unsafe_allow_html=True)
    guardado = st.session_state.get('guardado')
    t3 = P['totales'][3]
    ic, cls = ESTADO_ESTILO[ESTADO]

    c = st.columns(2)
    with c[0]:
        if guardado:
            pr = propuesta(guardado['entrada'], guardado['plazo'], guardado['ns'])
            urg, sug = int((pr['estado'] == 'urgente').sum()), int((pr['estado'] == 'sugerida').sum())
            bloque('🛒 Compras', f"{num(pr['cant'].sum())} t a pedir",
                   f"Con el stock del {guardado['fecha']:%d/%m/%Y}: {urg} {'familia' if urg == 1 else 'familias'} con "
                   f"compra urgente y {sug} con pedido propuesto", PAGS['compras'], 'Ver qué pedir')
        else:
            bloque('🛒 Compras', 'Falta el stock de hoy',
                   'Introduce el stock en almacén y lo pedido que aún no ha llegado para calcular cuánto pedir.',
                   PAGS['compras'], 'Introducir el stock')
    with c[1]:
        bloque('💶 Finanzas', f"{meur(t3['prevision'] * COSTE_T)} en 3 meses",
               f"Pago estimado por {num(t3['prevision'])} t de {mes(MESES_PREV[0])} a {mes(MESES_PREV[2])}. "
               f"Escenario alto: {meur(t3['superior'] * COSTE_T)}", PAGS['finanzas'], 'Ver recepciones y pagos')
    c = st.columns(2)
    with c[0]:
        ult = STOCK.index.max()
        exc_ult = STOCK.loc[ult, n.FAMILIAS] - n.stock_objetivo(3, 0.95)['objetivo']
        bloque('📦 Dirección', f"{num(exc_ult.sum())} t por encima del objetivo",
               f"Cierre de {mes(ult)}: {num(STOCK.loc[ult, 'Total'])} t en almacén frente a un objetivo de "
               f"{num(n.stock_objetivo(3, 0.95)['objetivo'].sum())} t (≈ {eur(round(valor_exceso(exc_ult), -3))} inmovilizados)",
               PAGS['direccion'], 'Ver inventario')
    with c[1]:
        with st.container(border=True):
            st.markdown('#### 🛡️ Analista de datos')
            st.markdown(f"<span class='badge {cls}'>{ic} {ESTADO.upper()}</span><div class='nota' style='margin-top:8px'>"
                        f"{MON['vencidas']} de 6 previsiones cerradas para evaluar el modelo. Controles del último "
                        f"reentrenamiento: {'todos correctos' if all(ok for ok, _ in CTRL.values()) else 'alguno falla'}."
                        f"</div>", unsafe_allow_html=True)
            st.page_link(PAGS['analista'], label='Ver panel del modelo', icon='➡️')


# ================================================================================================
# COMPRAS · QUÉ PEDIR
# ================================================================================================
def pag_compras():
    st.title('¿Qué hay que pedir?')
    st.markdown("<div class='sub'>Revisa el stock y lo que ya está pedido. La aplicación calcula cuánto pedir de cada "
                "familia; la decisión final es tuya.</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2], gap='large')
    with c1:
        st.markdown('**1. Stock en almacén y pedidos que aún no han llegado**')
        fecha = st.date_input('Fecha del stock', value=st.session_state.get('fecha_stock', FECHA_FOTO),
                              format='DD/MM/YYYY')
        st.session_state.fecha_stock = fecha
        ed = st.data_editor(entrada_actual(), hide_index=True, use_container_width=True, disabled=['Familia'], key='editor',
                            column_config={'En almacén (t)': st.column_config.NumberColumn(min_value=0, step=10, format='%d'),
                                           'Pedido y sin llegar (t)': st.column_config.NumberColumn(min_value=0, step=10, format='%d')})
        st.session_state.entrada = ed
        atr = ', '.join(f'{f.lower()} {num(v)} t' for f, v in ATRASADO.items())
        st.caption(f"Valores iniciales: foto real de finales de {mes(CIERRE_STOCK)}. Stock del cierre del mes (Business "
                   f"Central) y {num(sum(PEND['pendiente_t'].values()))} t pedidas y sin llegar en {PEND['pedidos']} pedidos "
                   f"abiertos del ERP" + (f"; de ellas, {num(sum(ATRASADO.values()))} t ya tenían la fecha prevista pasada "
                   f"({atr})" if ATRASADO else '') + '. Una vez implantada, la aplicación las leería cada día del ERP.')
    with c2:
        st.markdown('**2. Plazo y seguridad**')
        p0, ns0 = ajustes()
        st.session_state.plazo_v = st.radio('Plazo de entrega del proveedor', [3, 2], index=[3, 2].index(p0),
                 format_func=lambda k: f'{k} meses', horizontal=True,
                 help='2 meses es el plazo que dan los proveedores; 3 meses deja un mes de margen, porque casi 4 de cada 10 '
                      'entregas llegan al menos un mes tarde.')
        st.session_state.ns_v = st.select_slider('Seguridad contra roturas', options=[0.90, 0.95, 0.975, 0.99], value=ns0,
                         format_func=lambda v: {0.90: 'Baja (90 %)', 0.95: 'Normal (95 %)', 0.975: 'Alta (97,5 %)',
                                                0.99: 'Muy alta (99 %)'}[v],
                         help='Probabilidad de no quedarse sin material. Más seguridad = más stock.')

    plazo, ns = ajustes()
    guardado = st.session_state.get('guardado')
    cambios = guardado is None or not (guardado['entrada'].equals(ed) and guardado['fecha'] == fecha
                                       and guardado['plazo'] == plazo and guardado['ns'] == ns)
    g1, g2 = st.columns([1, 3], vertical_alignment='center')
    if g1.button(f'Guardar stock del {fecha:%d/%m/%Y}', type='primary', disabled=not cambios):
        st.session_state.guardado = {'fecha': fecha, 'entrada': ed.copy(), 'plazo': plazo, 'ns': ns}
        st.rerun()
    if guardado is None:
        g2.info(f'Estás viendo la **foto real de finales de {mes(CIERRE_STOCK)}**. Cámbiala por el stock y lo pendiente '
                f'de hoy y guárdala para que la propuesta aparezca en el resumen.', icon='✏️')
    elif cambios:
        g2.warning(f"Hay cambios sin guardar. El resumen sigue usando el stock del {guardado['fecha']:%d/%m/%Y}.", icon='✏️')
    else:
        g2.success(f"Stock del {guardado['fecha']:%d/%m/%Y} guardado. El resumen usa estos datos.", icon='✅')

    pr = propuesta(ed, plazo, ns)
    st.markdown('**3. Propuesta de pedido**')
    for f, r in pr.iterrows():
        ic, txt, cls, color = SEMAFORO[r['estado']]
        if r['estado'] == 'urgente' and r['cant'] <= 0:
            txt = 'VIGILAR LO PENDIENTE'
            porque = (f"Hay {num(r['stock'])} t en almacén, por debajo del mínimo de seguridad ({num(r['ss'])} t). "
                      f"<b>No hace falta pedir más</b>: vienen {num(r['pend'])} t en camino que cubren lo previsto en "
                      f"{plazo} meses y el colchón. Comprueba que llegan a tiempo; si se retrasan, hay riesgo de rotura.")
        elif r['estado'] == 'urgente':
            porque = (f"Hay {num(r['stock'])} t en almacén, por debajo del mínimo de seguridad ({num(r['ss'])} t): "
                      f"riesgo de quedarse sin material. Pide ya o adelanta lo pendiente. La cantidad cubre las "
                      f"{num(r['prev'])} t previstas en {plazo} meses y el colchón.")
        elif r['estado'] == 'sugerida':
            porque = (f"En {plazo} meses se prevé recibir unas {num(r['prev'])} t. Con {num(r['stock'])} t en almacén y "
                      f"{num(r['pend'])} t en camino no se cubre eso más el colchón de {num(r['ss'])} t.")
        else:
            porque = (f"Con {num(r['stock'])} t en almacén y {num(r['pend'])} t en camino ya se cubren las {num(r['prev'])} t "
                      f"previstas en {plazo} meses y el colchón de {num(r['ss'])} t.")
        if r['pequena']:
            porque += (f" <span class='nota'>Familia pequeña e irregular: el colchón hace de stock mínimo. En {plazo} meses "
                       f"suelen llegar unas {num(r['media_h'])} t (hasta {num(r['p90_h'])} t en periodos altos).</span>")
        importe = f"≈ {eur(round(r['cant'] * COSTE_T, -3))}" if r['cant'] > 0 else 'sin pedido'
        st.markdown(f"""<div class='fila' style='border-left-color:{color}'>
          <div style='display:flex;gap:22px;align-items:center;flex-wrap:wrap'>
            <div style='min-width:180px'><div class='fam'>{f}</div><span class='badge {cls}'>{ic} {txt}</span></div>
            <div style='min-width:140px'><div class='cant'>{num(r['cant'])} t</div><div class='nota'>{importe}</div></div>
            <div class='por' style='flex:1;min-width:260px'>{porque}</div>
          </div></div>""", unsafe_allow_html=True)

    tot = pr['cant'].sum()
    c = st.columns(3)
    card(c[0], 'Total a pedir', f'{num(tot)} t', f'{int((pr["cant"] > 0).sum())} de 5 familias', NAVY)
    card(c[1], 'Importe estimado', eur(round(tot * COSTE_T, -3)), f'Coste medio de compra: {num(COSTE_T)} €/t', NAVY)
    card(c[2], f'Recepciones previstas en {plazo} meses', f"{num(P['totales'][plazo]['prevision'])} t",
         'Total de las 5 familias')

    with st.expander('¿Cómo se calcula la cantidad?'):
        st.markdown(f"**Cantidad a pedir = recepciones previstas en el plazo + colchón de seguridad − stock en almacén − "
                    f"pedido y sin llegar**\n\n"
                    f"- Las **recepciones previstas** salen del modelo de previsión: el total de bobina que se espera recibir "
                    f"en {plazo} meses, repartido por el peso habitual de cada familia. Se usan como aproximación de lo que "
                    f"se va a gastar.\n"
                    f"- El **colchón de seguridad** cubre el error de la previsión durante el plazo. Es mayor en las familias "
                    f"grandes y sube si se pide más seguridad.\n"
                    f"- Se resta lo que **ya está pedido**, para no comprar dos veces.\n\n"
                    f"El precio del acero no cambia la propuesta: el modelo lo usa para saber cuánto suele llegar, no para "
                    f"decir si conviene comprar antes de una subida. Eso queda a criterio del comprador.")
        tabla = pr[['prev', 'ss', 'stock', 'pend', 'cant']].copy()
        tabla.columns = [f'Previsto en {plazo} meses', 'Colchón', 'En almacén', 'En camino', 'A pedir']
        st.dataframe(tabla.style.format(lambda v: f'{num(v)} t'), use_container_width=True)


# ================================================================================================
# FINANZAS · RECEPCIONES Y PAGOS
# ================================================================================================
def pag_finanzas():
    st.title('¿Cuánto vamos a recibir y pagar?')
    st.markdown("<div class='sub'>Bobina de acero que llegará en los próximos meses y su importe, para el presupuesto de "
                "compras y la previsión de tesorería.</div>", unsafe_allow_html=True)
    plazo = st.radio('Periodo', [3, 2], format_func=lambda k: f'Próximos {k} meses', horizontal=True)
    t = P['totales'][plazo]
    periodo = f"{mes(MESES_PREV[0])} a {mes(MESES_PREV[plazo - 1])}"
    c = st.columns(4)
    card(c[0], 'Toneladas previstas', f"{num(t['prevision'])} t", periodo)
    card(c[1], 'Importe estimado', meur(t['prevision'] * COSTE_T), f'a {num(COSTE_T)} €/t', NAVY)
    card(c[2], 'Escenario alto', meur(t['superior'] * COSTE_T), f"{num(t['superior'])} t · tesorería a reservar", '#dc3545')
    card(c[3], 'Escenario bajo', meur(t['inferior'] * COSTE_T), f"{num(t['inferior'])} t", '#28a745')
    st.caption('Hay un 95 % de probabilidad de que lo recibido quede entre el escenario bajo y el alto. Cada mes suelto '
               'varía mucho (un mes puede llegar el doble que otro), así que conviene presupuestar con el total del '
               'periodo y reservar el escenario alto.')

    st.markdown('#### Mes a mes')
    hist = Y.loc[CORTE - pd.DateOffset(months=11):]
    m = P['mensual'].iloc[:plazo]
    fig = go.Figure()
    fig.add_bar(x=hist.index, y=hist.values, name='Recibido', marker_color=GRIS,
                hovertemplate='%{x|%m/%Y}: %{y:,.0f} t<extra>Recibido</extra>')
    fig.add_bar(x=m.index, y=m['prevision'], name='Previsto (con su rango)', marker_color=STEEL,
                error_y=dict(type='data', symmetric=False, array=m['superior'] - m['prevision'],
                             arrayminus=m['prevision'] - m['inferior'], color=NAVY, thickness=1.3, width=6),
                hovertemplate='%{x|%m/%Y}: %{y:,.0f} t<extra>Previsto</extra>')
    fig.update_layout(bargap=0.25)
    ejes_mes(fig, list(hist.index) + list(m.index), 1)
    grafico(fig, 320)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('**Por mes**')
        tm = pd.DataFrame({'Mes': [mes(d) for d in m.index], 'Toneladas': m['prevision'].values,
                           'Importe': m['prevision'].values * COSTE_T})
        st.dataframe(tm.style.format({'Toneladas': lambda v: f'{num(v)} t', 'Importe': eur}),
                     hide_index=True, use_container_width=True)
    with c2:
        st.markdown('**Por familia**')
        fam = pd.DataFrame({'Familia': n.FAMILIAS, 'Toneladas': [t['prevision'] * PESOS[f] for f in n.FAMILIAS]})
        fam['Importe'] = fam['Toneladas'] * COSTE_T
        st.dataframe(fam.style.format({'Toneladas': lambda v: f'{num(v)} t', 'Importe': eur}),
                     hide_index=True, use_container_width=True)
    st.caption(f'Importe con el coste medio de compra de los últimos 12 meses según los albaranes ({num(COSTE_T)} €/t); es '
               f'orientativo, porque cambia con el precio del acero. La previsión es parecida todos los meses porque solo '
               f'cambia con el precio del acero y en agosto y diciembre, cuando llega menos.')


# ================================================================================================
# DIRECCIÓN · AHORRO DE INVENTARIO
# ================================================================================================
CORTO = dict(zip(n.FAMILIAS, ['Laminado', 'Galvanizado', 'Plastificado', 'Otros', 'Carbono']))


def valor_exceso(exceso):
    return float(sum(exceso[f] * n.VALOR_EUR_T[f] for f in n.FAMILIAS))


def pag_direccion():
    st.title('¿Cuánto inventario tenemos de más?')
    st.markdown("<div class='sub'>Stock real de bobina de acero en cada cierre de mes frente al stock objetivo, y dinero "
                "inmovilizado por encima de ese objetivo.</div>", unsafe_allow_html=True)
    meses = list(STOCK.index)
    cierre = st.select_slider('Cierre de inventario', options=meses, value=meses[-1], format_func=lambda d: mes(d, True))
    so = n.stock_objetivo(3, 0.95)
    stock = STOCK.loc[cierre, n.FAMILIAS]
    exceso = stock - so['objetivo']
    medio_base = pd.Series(n.STOCK_MEDIO_CAP6)
    ns_cierre, _ = n.nivel_servicio_implicito(stock.sum(), so['ciclo'].sum())

    c = st.columns(4)
    card(c[0], f'Stock a fin de {mes(cierre)}', f"{num(STOCK.loc[cierre, 'Total'])} t", f'Objetivo: {num(so["objetivo"].sum())} t')
    card(c[1], 'Por encima del objetivo', f'{num(exceso.sum())} t', f'{num(exceso.sum() / stock.sum() * 100)} % del stock', NAVY)
    card(c[2], 'Dinero inmovilizado de más', eur(round(valor_exceso(exceso), -3)), 'al valor por tonelada del ERP', NAVY)
    card(c[3], 'Seguridad que cubre ese stock', f'{num(ns_cierre * 100, 1)} %', 'frente al 95 % del objetivo')

    st.markdown('#### Evolución del stock')
    fig = go.Figure()
    for f in n.FAMILIAS:
        fig.add_bar(x=STOCK.index, y=STOCK[f], name=CORTO[f], marker_color=FAM_COLOR[f],
                    hovertemplate=f'{f}: %{{y:,.0f}} t<extra></extra>')
    fig.add_hline(y=so['objetivo'].sum(), line_dash='dash', line_color=NAVY, line_width=1.5,
                  annotation_text=f"Objetivo {num(so['objetivo'].sum())} t", annotation_position='bottom right',
                  annotation_bgcolor='white')
    fig.add_hline(y=medio_base.sum(), line_dash='dot', line_color='#eb6834', line_width=1.5,
                  annotation_text=f'Punto de partida {num(medio_base.sum())} t', annotation_position='top left',
                  annotation_bgcolor='white')
    fig.update_layout(barmode='stack', bargap=0.25)
    ejes_mes(fig, STOCK.index)
    grafico(fig, 330)

    st.markdown(f'#### Por familia · {mes(cierre)}')
    c1, c2 = st.columns([1, 1], gap='large')
    with c1:
        fig = go.Figure()
        fig.add_bar(x=list(CORTO.values()), y=stock.values, name='Stock real', marker_color=GRIS,
                    hovertemplate='%{x}: %{y:,.0f} t<extra>Real</extra>')
        fig.add_bar(x=list(CORTO.values()), y=so['objetivo'].values, name='Stock objetivo', marker_color=STEEL,
                    hovertemplate='%{x}: %{y:,.0f} t<extra>Objetivo</extra>')
        for f in n.FAMILIAS:
            fig.add_annotation(x=CORTO[f], y=max(stock[f], so.loc[f, 'objetivo']), yshift=12, showarrow=False,
                               text=f"{'+' if exceso[f] >= 0 else '−'}{num(abs(exceso[f]))} t", font=dict(size=12))
        fig.update_layout(barmode='group', bargap=0.3)
        grafico(fig, 300)
    with c2:
        tf = pd.DataFrame({'Real': stock, 'Objetivo': so['objetivo'], 'Diferencia': exceso,
                           'Valor (€)': exceso * pd.Series(n.VALOR_EUR_T)})
        tf.index = list(CORTO.values())
        tf.loc['Total'] = [STOCK.loc[cierre, 'Total'], so['objetivo'].sum(), exceso.sum(), valor_exceso(exceso)]
        st.dataframe(tf.style.format({'Real': lambda v: f'{num(v)} t', 'Objetivo': lambda v: f'{num(v)} t',
                                      'Diferencia': lambda v: f"{'+' if v >= 0 else '−'}{num(abs(v))} t", 'Valor (€)': eur}),
                     use_container_width=True)
        st.caption('Una diferencia negativa indica stock por debajo del objetivo en esa familia: el stock de una familia no '
                   'cubre la falta de otra.')

    st.caption(f"Fuente: informe «Valoración inventario» de Business Central, stock físico a fin de mes. Objetivo con un 95 % de "
               f"seguridad y un plazo de 3 meses (stock de ciclo + stock de seguridad por familia). Desde la puesta en marcha, "
               f"el ahorro se medirá comparando cada cierre con el punto de partida ({num(medio_base.sum())} t, media de ago-25 "
               f"a jul-26), valorado al €/t de ese punto para que los cambios de precio del acero no se confundan con ahorro.")


# ================================================================================================
# ANALISTA · PANEL DEL MODELO
# ================================================================================================
def leg(s):
    for a, b in [('precio_l2', 'precio'), ('precio_l1', 'precio (1 mes)'), ('ago_dic', 'ago/dic'),
                 ('ini_trim', 'inicio trimestre'), ('dias_lab', 'días laborables'), (' [orden TFM]', ' (borrador)'),
                 ('XGBoost (retardos + calendario + precio)', 'XGBoost con precio')]:
        s = s.replace(a, b)
    return s


def pag_analista():
    st.title('Panel del modelo')
    st.markdown("<div class='sub'>Seguimiento mensual del modelo de previsión: error frente a lo recibido, controles del "
                "reentrenamiento y calidad de los datos de entrada.</div>", unsafe_allow_html=True)
    ic, cls = ESTADO_ESTILO[ESTADO]
    expl = {'En seguimiento': f"{MON['vencidas']} de 6 previsiones cerradas: el error se muestra, pero aún no se juzga.",
            'Correcto': 'El modelo mejora a la media y su error está dentro de lo esperado.',
            'Vigilar': 'Hay alguna señal que revisar el mes que viene.',
            'Revisar': 'Volver a la fase de experimentación.'}[ESTADO]
    c = st.columns(4)
    c[0].markdown(f"<div class='card'><div class='lab'>Estado</div><div style='margin-top:8px'>"
                  f"<span class='badge {cls}'>{ic} {ESTADO.upper()}</span></div><div class='sub2'>{expl}</div></div>",
                  unsafe_allow_html=True)
    card(c[1], 'Error en previsiones cerradas', f"{num(MON.get('error_modelo'), 1)} %",
         f"Media histórica: {num(MON.get('error_media'), 1)} %")
    card(c[2], 'Error en la validación', f"{num(FICHA['metricas']['cv_total3'], 1)} %",
         f"Media: {num(FICHA['referencia_media']['cv_total3'], 1)} % · total a 3 meses, 2022–2025")
    card(c[3], 'Último reentrenamiento', mes(CORTE, True), f"{len(Y)} meses · precio: {FUENTE}")
    for a in ALERTAS:
        st.warning(a, icon='⚠️')

    t1, t2, t3, t4 = st.tabs(['Previsiones frente a lo recibido', 'Reentrenamiento y datos', 'Elección del modelo',
                              'Series de entrada'])
    with t1:
        tab = MON['tabla'].copy()
        x = [mes(c_, True) for c_ in tab['corte']]
        fig = go.Figure()
        fig.add_bar(x=x, y=tab['prevision'], name='Modelo', marker_color=STEEL, customdata=tab['meses'],
                    hovertemplate='Ejecución %{x} (%{customdata}): %{y:,.0f} t<extra>Modelo</extra>')
        fig.add_bar(x=x, y=tab['media'], name='Media histórica', marker_color='#f3b79b', customdata=tab['meses'],
                    hovertemplate='Ejecución %{x} (%{customdata}): %{y:,.0f} t<extra>Media</extra>')
        fig.add_scatter(x=x, y=tab['real'], name='Recibido', mode='markers',
                        marker=dict(color='#0b0b0b', size=11, symbol='diamond'),
                        hovertemplate='Recibido: %{y:,.0f} t<extra></extra>')
        fig.update_layout(barmode='group', bargap=0.3)
        grafico(fig, 320, 'toneladas en 3 meses')
        err_m = (tab['real'] - tab['prevision']).abs() / tab['real'] * 100
        err_r = (tab['real'] - tab['media']).abs() / tab['real'] * 100
        tv = pd.DataFrame({'Ejecución': [mes(c_) for c_ in tab['corte']], 'Meses previstos': tab['meses'],
                           'Modelo (t)': tab['prevision'], 'Media (t)': tab['media'], 'Recibido (t)': tab['real'],
                           'Error modelo': err_m, 'Error media': err_r,
                           'Estado': np.where(tab['vencida'], 'Cerrada', 'Pendiente')})
        for col_ in ['Modelo (t)', 'Media (t)', 'Recibido (t)']:
            tv[col_] = [num(v) for v in tv[col_]]
        for col_ in ['Error modelo', 'Error media']:
            tv[col_] = [f'{num(v, 1)} %' if pd.notna(v) else '–' for v in tv[col_]]
        st.dataframe(tv, hide_index=True, use_container_width=True)
        st.caption('Ejecuciones mensuales simuladas desde septiembre de 2025, cada una con la información disponible en su '
                   'fecha. Con pocas ventanas solapadas los meses altos y bajos se compensan y todos los métodos salen con '
                   'poco error; la comparación fiable es la validación del capítulo 4. Reglas: en seguimiento con menos de '
                   '6 previsiones cerradas; correcto si el error ≤ media y ≤ 1,5 × la validación; vigilar si supera 1,5 × '
                   'la validación o los datos se salen de lo observado; revisar si, con 6 o más, es peor que la media o '
                   'falla un control.')
    with t2:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('**Controles para pasar a producción**')
            for nombre, (ok, det) in CTRL.items():
                st.markdown(f"{'✅' if ok else '❌'} {nombre} · <span class='nota'>{det}</span>", unsafe_allow_html=True)
            aj = P['ajuste']
            coef = pd.DataFrame({'Coeficiente': aj.params.drop('sigma2').values, 'p-valor': aj.pvalues.drop('sigma2').values,
                                 'Fase 1': [FICHA['coeficientes_entrenamiento'][k] for k in ('const', 'precio_l2', 'ago_dic')]},
                                index=['Constante (t/mes)', 'Precio del acero (t por punto)', 'Agosto y diciembre (t)'])
            st.markdown('**Coeficientes del ARIMAX(0,0,0)**')
            st.dataframe(coef.style.format({'Coeficiente': lambda v: num(v, 1), 'p-valor': lambda v: num(v, 4),
                                            'Fase 1': lambda v: num(v, 1)}), use_container_width=True)
        with c2:
            st.markdown('**Datos de entrada**')
            con = P['conocido']
            checks = [('Último mes del ERP completo', True, mes(CORTE)),
                      ('Ningún mes sin recepciones', bool((Y > 0).all()), f'{len(Y)} meses'),
                      ('Precio del INE disponible', IPRI.index.max() >= con, f'necesario hasta {mes(con, True)}'),
                      ('Precio dentro del rango histórico', not any('rango' in a for a in ALERTAS_DATOS),
                       f"{num(P['Xf']['precio_l2'].iloc[0], 1)} %"),
                      ('Nivel de recepciones estable', not any('nivel' in a for a in ALERTAS_DATOS),
                       f"{num(Y.iloc[-12:].mean())} frente a {num(Y.iloc[:-12].mean())} t/mes")]
            for nombre, ok, det in checks:
                st.markdown(f"{'✅' if ok else '⚠️'} {nombre} · <span class='nota'>{det}</span>", unsafe_allow_html=True)
    with t3:
        rm = n.cargar_resumen_modelos().copy()
        rm['cumple'] = (rm['p_max'] < 0.05) & (rm['lb_p12'] > 0.05)
        sel = pd.concat([rm[rm['fase'] != 'referencia'].nsmallest(9, 'cv_total3'),
                         rm[rm['cumple'] & (rm['fase'] != 'referencia')], rm.loc[['Media', 'Media por mes']],
                         rm[rm.index.str.startswith('XGBoost')].nsmallest(1, 'cv_total3')])
        sel = sel[~sel.index.duplicated()].sort_values('cv_total3', ascending=False)
        color = [STEEL if i == FICHA['nombre'] else ('#eb6834' if r['fase'] == 'referencia' else
                 ('#86b6ef' if r['cumple'] else '#c3c2b7')) for i, r in sel.iterrows()]
        fig = go.Figure(go.Bar(y=[leg(i) for i in sel.index], x=sel['cv_total3'], orientation='h', marker_color=color,
                               text=[f'{num(v, 1)} %' for v in sel['cv_total3']], textposition='outside',
                               hovertemplate='%{y}: %{x:.1f} %<extra></extra>'))
        fig.update_layout(height=560, margin=dict(l=330, r=20, t=10, b=10), plot_bgcolor='white', showlegend=False,
                          separators=',.', font=dict(size=12, color='#495057'))
        fig.update_xaxes(visible=False, range=[0, sel['cv_total3'].max() * 1.15])
        st.markdown('**Error del total a 3 meses en la validación cruzada.** ' + ' &nbsp; '.join(
            f"<span style='display:inline-block;width:11px;height:11px;background:{c_};border-radius:2px;vertical-align:-1px'>"
            f"</span> <span class='nota'>{e_}</span>" for e_, c_ in [('Elegido', STEEL), ('Cumple la regla', '#86b6ef'),
                                                                    ('No cumple', '#c3c2b7'), ('Referencia', '#eb6834')]),
            unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, theme=None, config={'displayModeBar': False})
        st.caption('Regla fijada antes de mirar el test: variables significativas, residuos sin autocorrelación y menor '
                   'error. Los que tienen algo menos de error añaden términos no significativos.')
    with t4:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('**Recepciones mensuales de bobina de acero (t)**')
            fig = go.Figure(go.Scatter(x=Y.index, y=Y.values, mode='lines', line=dict(color=STEEL, width=2),
                                       hovertemplate='%{x|%m/%Y}: %{y:,.0f} t<extra></extra>'))
            fig.add_hline(y=Y.mean(), line_dash='dot', line_color='#eb6834',
                          annotation_text=f'Media {num(Y.mean())} t', annotation_bgcolor='white')
            grafico(fig, 300, None, leyenda=False)
        with c2:
            st.markdown('**Precio del acero: variación a 3 meses (%)**')
            v = (IPRI.pct_change(3) * 100).dropna().loc['2018':]
            fig = go.Figure(go.Scatter(x=v.index, y=v.values, mode='lines', line=dict(color=STEEL, width=2),
                                       hovertemplate='%{x|%m/%Y}: %{y:.1f} %<extra></extra>'))
            fig.add_hline(y=0, line_color='#c3c2b7')
            grafico(fig, 300, None, leyenda=False, y0=False)


# --- Navegación por usuario ---------------------------------------------------------------------
PAGS = {
    'resumen': st.Page(pag_resumen, title='Resumen del mes', icon='🏠', default=True),
    'compras': st.Page(pag_compras, title='Qué pedir', icon='🛒', url_path='compras'),
    'finanzas': st.Page(pag_finanzas, title='Recepciones y pagos', icon='💶', url_path='finanzas'),
    'direccion': st.Page(pag_direccion, title='Inventario', icon='📦', url_path='direccion'),
    'analista': st.Page(pag_analista, title='Panel del modelo', icon='🛡️', url_path='analista'),
}
nav = st.navigation({'Inicio': [PAGS['resumen']], 'Compras': [PAGS['compras']], 'Finanzas': [PAGS['finanzas']],
                     'Dirección': [PAGS['direccion']], 'Analista de datos': [PAGS['analista']]})
barra_lateral()
nav.run()
