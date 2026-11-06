"""Lógica de la aplicación: modelo, previsión, regla de compra, monitorización y retorno económico.

Reproduce el pipeline de producción de la fase 2 (fase2_pipeline_produccion.ipynb) sobre los datos
agregados de datos/, y los cálculos de los capítulos 5 y 6 del TFM. No depende de Streamlit, así que
se puede probar por separado.
"""
import json
import os
import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings('ignore')
BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = BASE

FAMILIAS = ['Laminado en frío', 'Galvanizado', 'Fleje plastificado', 'Otros', 'Carbono y muelle']
FAMILIAS_GRANDES = ['Laminado en frío', 'Galvanizado']   # peso >= 10 %: gestión por previsión
INE_URL = 'https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/61524?nult=150'
INE_COD = 'IPR37378'   # IPRI, grupo 241, mercado interior

# ---------------------------------------------------------------------------------------------
# Parámetros del TFM (capítulos 5 y 6). Se dejan juntos para poder revisarlos de un vistazo.
# ---------------------------------------------------------------------------------------------
Z_95 = float(stats.norm.ppf(0.95))   # 1,645: al 95 % el stock de seguridad es exactamente el de la tabla
# Stock de seguridad al 95 % (capítulo 5, Tabla 48): z x error típico de cada familia en el plazo
SEGURIDAD_95 = {
    3: {'Laminado en frío': 735, 'Galvanizado': 556, 'Fleje plastificado': 137, 'Otros': 78, 'Carbono y muelle': 119},
    2: {'Laminado en frío': 671, 'Galvanizado': 447, 'Fleje plastificado': 121, 'Otros': 62, 'Carbono y muelle': 94},
}
# Stock objetivo medio al 95 % (capítulo 5, Tabla 48; previsión de abril a junio de 2026). El de ciclo es la diferencia
OBJETIVO_95 = {
    3: {'Laminado en frío': 948, 'Galvanizado': 720, 'Fleje plastificado': 164, 'Otros': 101, 'Carbono y muelle': 134},
    2: {'Laminado en frío': 884, 'Galvanizado': 611, 'Fleje plastificado': 148, 'Otros': 84, 'Carbono y muelle': 108},
}
OBJETIVO_MEDIA_95_3M = 2145   # stock objetivo si se planificara con la media en lugar del modelo (capítulo 5)

# Inventario real (informe «Valoración inventario» de Business Central, capítulo 6)
VALOR_EUR_T = {'Laminado en frío': 952, 'Galvanizado': 966, 'Fleje plastificado': 1257, 'Otros': 1420, 'Carbono y muelle': 1295}

# Stock medio real del periodo base (ago-2025 a jul-2026) con la precisión del capítulo 6 (Tabla 52: valor del
# exceso de cada familia / su valor por tonelada + stock objetivo). Los CSV mensuales vienen redondeados a la tonelada.
STOCK_MEDIO_CAP6 = {'Laminado en frío': 948 + 217663 / 952, 'Galvanizado': 720 + 52185 / 966,
                    'Fleje plastificado': 164 - 64471 / 1257, 'Otros': 101 + 82936 / 1420,
                    'Carbono y muelle': 134 + 91994 / 1295}

# Costes de la implantación (capítulo 6, consultora con alcance mínimo)
CONSULTORA = [  # perfil, tareas, horas, €/h
    ('Data engineer', 'Conexión Business Central–Fabric, transformaciones, reglas de calidad, Purview, publicación de la app', 240, 70),
    ('Data scientist', 'Pipeline en Fabric con MLflow, ejecución mensual y alertas, stock objetivo, piloto', 120, 85),
    ('Project manager', 'Unas 8 h al mes durante 6 meses', 48, 60),
    ('Arquitecto', 'Revisión de la arquitectura y la seguridad en Azure', 16, 90),
]
CONTINGENCIA = 0.15
OTROS_INVERSION = {'Formación': 4000, 'Limpieza del maestro de artículos': 3000, 'Analista interno (25 % del año 0)': 7500}
FUNDAE = 4000                  # bonificación de la formación (caso base)
AYUDA_DIGITALIZACION = 8000    # solo como sensibilidad: no está concedida
FASE0 = 44200                  # prueba de concepto (este TFM) valorada a precio de mercado
RECURRENTES = {'Microsoft Fabric (capacidad F2)': 2520, 'Power BI Pro': 840, 'Azure App Service': 720,
               'Microsoft Purview': 700, 'Contrato de soporte y mantenimiento (40 h × 75 €/h)': 3000,
               'Comité de Datos': 1000, 'Analista interno (10 %)': 3000}   # 11.780 € el año 1 (capítulo 6, Tabla 59)
REVISION_MODELO = (3, 3400)    # revisión a fondo del modelo en el año 3 (40 h × 85 €/h)
SUBIDA_RECURRENTES = 0.05
TASA_DESCUENTO = 0.08
CAPTURA = {'Conservador': [0.60, 0.65, 0.70, 0.70, 0.70], 'Base': [1.0] * 5, 'Optimista': [1.0] * 5}
H_ESCENARIO = {'Conservador': 0.10, 'Base': 0.10, 'Optimista': 0.15}


# ---------------------------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------------------------
def cargar_ficha():
    with open(os.path.join(DATOS, 'modelo_final.json'), encoding='utf-8') as f:
        return json.load(f)


def cargar_recepciones():
    t = pd.read_csv(os.path.join(DATOS, 'recepciones_mensuales.csv'), index_col=0)
    t.index = pd.to_datetime(t.index + '-01')
    return t


def cargar_ipri_csv():
    s = pd.read_csv(os.path.join(DATOS, 'ipri_241.csv'), index_col=0)['ipri_241']
    s.index = pd.to_datetime(s.index + '-01')
    return s


def descargar_ipri_ine(timeout=15):
    """Descarga el IPRI del acero desde la API del INE (mismo código que el pipeline)."""
    import requests
    r = requests.get(INE_URL, timeout=timeout)
    r.raise_for_status()
    serie = next(s for s in r.json() if s.get('COD') == INE_COD)
    idx = pd.to_datetime([f"{d['Anyo']}-{int(d['FK_Periodo']):02d}-01" for d in serie['Data']])
    return pd.Series([d['Valor'] for d in serie['Data']], index=idx, name='ipri_241').sort_index().astype(float)


def cargar_stock():
    """Stock físico de bobina de acero a fin de mes por familia (Business Central)."""
    t = pd.read_csv(os.path.join(DATOS, 'stock_mensual_familia.csv'), sep=';', index_col=0)
    meses = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
    t.index = [pd.Timestamp(2000 + int(m.split('-')[1]), meses[m.split('-')[0]], 1) for m in t.index]
    return t


def cargar_resumen_modelos():
    t = pd.read_csv(os.path.join(DATOS, 'resumen_modelos_total.csv'), sep=';', decimal=',', index_col=0)
    return t


# ---------------------------------------------------------------------------------------------
# Modelo (igual que el pipeline de la fase 2)
# ---------------------------------------------------------------------------------------------
def variables(meses, ipri, conocido):
    """precio_l2 y ago_dic tal como se conocerían en la fecha de corte (sin información futura)."""
    var3 = (ipri.loc[:conocido].pct_change(3) * 100).dropna()
    precio = [var3.get(d - pd.DateOffset(months=2), np.nan) if d - pd.DateOffset(months=2) <= conocido else var3.iloc[-1]
              for d in meses]
    return pd.DataFrame({'precio_l2': precio, 'ago_dic': meses.month.isin([8, 12]).astype(float)}, index=meses)


def ajustar(Y, ipri, corte):
    """Reentrena el ARIMAX(0,0,0) con todos los meses hasta el corte."""
    Yc = Y.loc[:corte]
    conocido = corte - pd.DateOffset(months=1)   # el INE se publica con un mes de retraso
    X = variables(Yc.index, ipri, conocido)
    aj = SARIMAX(Yc, exog=X, order=(0, 0, 0), trend='c').fit(disp=False, cov_type='oim')
    return aj, X, conocido


def controles(aj, ficha):
    pv = aj.pvalues.drop(['intercept', 'sigma2'], errors='ignore')
    lb = float(acorr_ljungbox(aj.resid, lags=[12])['lb_pvalue'].iloc[0])
    ref = ficha['coeficientes_entrenamiento']
    signos = all(np.sign(aj.params[k]) == np.sign(ref[k]) for k in ['precio_l2', 'ago_dic'])
    return {'Variables significativas (p < 0,05)': (bool(pv.max() < 0.05), f'p máx. {pv.max():.3f}'),
            'Residuos aleatorios (Ljung-Box p > 0,05)': (lb > 0.05, f'p = {lb:.2f}'),
            'Mismo signo que en la fase 1': (bool(signos), 'precio +, agosto/diciembre −' if signos else 'cambia algún signo')}


def prever(Y, ipri, corte, horizonte=3, confianza=0.95):
    aj, X, conocido = ajustar(Y, ipri, corte)
    futuro = pd.date_range(corte + pd.offsets.MonthBegin(1), periods=horizonte, freq='MS')
    Xf = variables(futuro, ipri, conocido)
    pr = aj.get_forecast(horizonte, exog=Xf)
    z = stats.norm.ppf(0.5 + confianza / 2)
    media, se = pr.predicted_mean.values, pr.se_mean.values
    mensual = pd.DataFrame({'prevision': media, 'inferior': np.clip(media - z * se, 0, None),
                            'superior': media + z * se}, index=futuro)
    totales = {}
    for k in (2, 3):   # ARIMAX(0,0,0): errores independientes, la varianza del total es la suma
        m, s = media[:k].sum(), np.sqrt((se[:k] ** 2).sum())
        totales[k] = {'prevision': m, 'inferior': max(m - z * s, 0), 'superior': m + z * s, 'media': Y.loc[:corte].mean() * k}
    return {'ajuste': aj, 'X': X, 'Xf': Xf, 'mensual': mensual, 'totales': totales, 'conocido': conocido, 'corte': corte}


def pesos_familia(F, corte):
    s = F.loc[:corte, FAMILIAS].sum()
    return s / s.sum()


# ---------------------------------------------------------------------------------------------
# Regla de compra (capítulo 5, módulo 1)
# ---------------------------------------------------------------------------------------------
def seguridad(familia, plazo, nivel_servicio):
    z = stats.norm.ppf(nivel_servicio)
    return SEGURIDAD_95[plazo][familia] * z / Z_95


def stock_objetivo(plazo, nivel_servicio):
    """Stock objetivo medio = stock de ciclo (medio mes de recepciones) + stock de seguridad.

    Parte de la tabla del capítulo 5 (95 %) y reescala el stock de seguridad con el nivel de servicio. En producción
    se recalcularía cada mes con la previsión y el error del último reentrenamiento.
    """
    filas = []
    for f in FAMILIAS:
        ciclo = OBJETIVO_95[plazo][f] - SEGURIDAD_95[plazo][f]
        ss = seguridad(f, plazo, nivel_servicio)
        filas.append({'familia': f, 'ciclo': ciclo, 'seguridad': ss, 'objetivo': ciclo + ss})
    return pd.DataFrame(filas).set_index('familia')


def recomendar(prev_plazo_familia, ss, stock, pendiente):
    cantidad = prev_plazo_familia + ss - stock - pendiente
    if stock < ss:
        estado = 'urgente'
    elif cantidad > 0:
        estado = 'sugerida'
    else:
        estado = 'no comprar'
    return max(cantidad, 0.0), cantidad, estado


# ---------------------------------------------------------------------------------------------
# Monitorización (capítulo 5, módulo 4; reglas del pipeline)
# ---------------------------------------------------------------------------------------------
def simular_monitorizacion(Y, F, ipri, corte_actual, ficha, primer_corte='2025-09-01', H=3, minimo=6, factor=1.5):
    filas = []
    for c in pd.date_range(primer_corte, corte_actual, freq='MS'):
        p = prever(Y, ipri, c, horizonte=H)
        meses = p['mensual'].index
        vencida = meses[-1] <= corte_actual
        real = Y.reindex(meses).sum() if vencida else np.nan
        filas.append({'corte': c, 'meses': f"{meses[0]:%m/%Y} – {meses[-1]:%m/%Y}", 'prevision': p['totales'][H]['prevision'],
                      'media': p['totales'][H]['media'], 'real': real, 'vencida': vencida})
    t = pd.DataFrame(filas)
    v = t[t['vencida']]
    res = {'tabla': t, 'vencidas': len(v)}
    if len(v):
        res['error_modelo'] = (v['real'] - v['prevision']).abs().sum() / v['real'].sum() * 100
        res['error_media'] = (v['real'] - v['media']).abs().sum() / v['real'].sum() * 100
    return res


def estado_monitorizacion(mon, ctrl, alertas_datos, ficha, minimo=6, factor=1.5):
    ref = ficha['metricas']['cv_total3']
    alertas = list(alertas_datos)
    if not all(ok for ok, _ in ctrl.values()):
        alertas.append('El reentrenamiento no supera los controles')
        return 'Revisar', alertas
    if mon['vencidas'] >= minimo and mon.get('error_modelo', 0) > mon.get('error_media', np.inf):
        return 'Revisar', alertas + ['El modelo predice peor que la media']
    if mon.get('error_modelo', 0) > factor * ref:
        alertas.append(f'Error por encima de 1,5 veces el de la validación ({ref:.1f} %)')
    if alertas:
        return 'Vigilar', alertas
    if mon['vencidas'] < minimo:
        return 'En seguimiento', alertas
    return 'Correcto', alertas


def alertas_datos(Y, X, Xf, corte):
    out = []
    lo, hi = X['precio_l2'].min(), X['precio_l2'].max()
    if not Xf['precio_l2'].between(lo, hi).all():
        out.append(f'Precio previsto fuera del rango histórico ({lo:.1f} % a {hi:.1f} %)')
    Yc = Y.loc[:corte]
    ult, prev = Yc.iloc[-12:], Yc.iloc[:-12]
    z = (ult.mean() - prev.mean()) / (prev.std() / np.sqrt(12))
    if abs(z) > 2:
        out.append(f'Cambio de nivel en los últimos 12 meses ({ult.mean():.0f} t frente a {prev.mean():.0f} t)')
    return out


# ---------------------------------------------------------------------------------------------
# Retorno económico (capítulo 6)
# ---------------------------------------------------------------------------------------------
def coste_consultora():
    base = sum(h * e for _, _, h, e in CONSULTORA)
    return base, base * CONTINGENCIA, base * (1 + CONTINGENCIA)


def flujos(ahorro_anual, escenario, horizonte, ayuda_digital=False, incluir_fase0=False):
    _, _, consultora = coste_consultora()
    inversion = consultora + sum(OTROS_INVERSION.values()) - FUNDAE
    if ayuda_digital:
        inversion -= AYUDA_DIGITALIZACION
    if incluir_fase0:
        inversion += FASE0
    rec_base = sum(RECURRENTES.values())
    filas = [{'año': 0, 'ahorro': 0.0, 'coste': inversion}]
    for t in range(1, horizonte + 1):
        coste = rec_base * (1 + SUBIDA_RECURRENTES) ** (t - 1) + (REVISION_MODELO[1] if t == REVISION_MODELO[0] else 0)
        # el capítulo 6 redondea el ahorro anual a centenas (Tabla 54)
        filas.append({'año': t, 'ahorro': round(ahorro_anual * CAPTURA[escenario][t - 1], -2), 'coste': coste})
    f = pd.DataFrame(filas).set_index('año')
    f['neto'] = f['ahorro'] - f['coste']
    f['acumulado'] = f['neto'].cumsum()
    return f, inversion


def indicadores(f, inversion, tasa=TASA_DESCUENTO):
    neto = f['neto'].values
    van = sum(v / (1 + tasa) ** t for t, v in enumerate(neto))
    try:
        from scipy.optimize import brentq
        tir = brentq(lambda r: sum(v / (1 + r) ** t for t, v in enumerate(neto)), -0.99, 10)
    except ValueError:
        tir = np.nan
    beneficio = f['ahorro'].sum() - f['coste'].sum()
    # Recuperación desde la puesta en marcha (meses), con el flujo neto mensual de cada año
    pendiente, meses = inversion, 0
    for t in range(1, len(f)):
        mensual = f.loc[t, 'neto'] / 12
        if mensual <= 0:
            meses += 12
            continue
        if pendiente <= mensual * 12:
            meses += int(np.ceil(pendiente / mensual))
            pendiente = 0
            break
        pendiente -= mensual * 12
        meses += 12
    return {'beneficio': beneficio, 'van': van, 'tir': tir, 'roi_coste': beneficio / f['coste'].sum(),
            'roi_inversion': beneficio / inversion, 'recuperacion': meses if pendiente == 0 else None,
            'coste_total': f['coste'].sum(), 'ahorro_total': f['ahorro'].sum()}


def exceso_critico(escenario, horizonte, h, eur_t_exceso, ayuda_digital=False, incluir_fase0=False):
    """Exceso de stock (t) con el que el VAN es cero; el ahorro es lineal en el exceso."""
    f, _ = flujos(0, escenario, horizonte, ayuda_digital, incluir_fase0)
    desc = np.array([(1 + TASA_DESCUENTO) ** -t for t in f.index])
    captura = np.array([0] + CAPTURA[escenario][:horizonte])
    ahorro_t = h * eur_t_exceso * captura          # ahorro de cada año por tonelada de exceso
    return float((f['coste'].values * desc).sum() / (ahorro_t * desc).sum())


def nivel_servicio_implicito(stock_medio_total, ciclo_total, plazo=3):
    """Nivel de servicio al que equivale el stock real con el error del modelo."""
    ss_95 = sum(SEGURIDAD_95[plazo].values())
    z = (stock_medio_total - ciclo_total) / ss_95 * Z_95
    return float(stats.norm.cdf(z)), z


def cargar_pendiente():
    """Bobina de acero pedida y sin llegar por familia en la fecha de la extracción del ERP."""
    with open(os.path.join(DATOS, 'pedidos_pendientes.json'), encoding='utf-8') as f:
        d = json.load(f)
    d['fecha_foto'] = pd.Timestamp(d['fecha_foto'])
    return d
