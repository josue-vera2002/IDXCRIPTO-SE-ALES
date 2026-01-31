import cv2
import numpy as np
import os
from scipy import stats

def analyze_image(image_path):
    """
    Analiza una captura de pantalla de gráfico de trading
    Extrae: tendencia, fuerza, volatilidad, momentum, patrones
    Versión calibrada para análisis realista
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to read image: {image_path}")
    
    h, w = img.shape[:2]
    
    # 1. DETECCIÓN DE TENDENCIA MEJORADA
    trend_data = detect_trend_advanced(img)
    
    # 2. ANÁLISIS DE VOLATILIDAD
    volatility_data = analyze_volatility(img)
    
    # 3. DETECCIÓN DE MOMENTUM
    momentum_data = detect_momentum(img)
    
    # 4. ANÁLISIS DE VELAS (último 20% del gráfico)
    candle_analysis = analyze_recent_candles(img)
    
    # 5. DETECCIÓN DE CAMBIOS DE TENDENCIA
    reversal_signals = detect_reversal_patterns(img)
    
    # 6. FUERZA DEL MERCADO (edge detection)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_strength = float(np.sum(edges))
    norm_strength = edge_strength / (h * w) if (h * w) > 0 else 0.0
    norm_pct = norm_strength * 100.0
    
    # 7. CALCULAR FUERZA CALIBRADA
    strength = calculate_calibrated_strength(
        trend_data, 
        volatility_data, 
        momentum_data,
        candle_analysis,
        reversal_signals
    )
    
    # 8. CLASIFICACIÓN REALISTA DEL MERCADO
    market_state = classify_market_state_realistic(
        trend_data,
        volatility_data,
        candle_analysis,
        strength
    )
    
    return {
        # Datos principales
        "trend": trend_data["direction"],
        "strength": strength,
        "norm_pct": round(norm_pct, 4),
        
        # Datos detallados
        "trend_angle": trend_data["angle"],
        "trend_confidence": trend_data["confidence"],
        "volatility": volatility_data["level"],
        "volatility_score": volatility_data["score"],
        "momentum": momentum_data["direction"],
        "momentum_strength": momentum_data["strength"],
        
        # Patrones
        "candle_pattern": candle_analysis["pattern"],
        "recent_movement": candle_analysis["movement"],
        "reversal_detected": reversal_signals["detected"],
        
        # Estado del mercado
        "market_state": market_state,
        "is_trending": market_state != "lateral",
        
        # Metadatos
        "edge_strength": edge_strength,
        "shape": (w, h)
    }


def detect_trend_advanced(img):
    """
    Detección avanzada de tendencia con múltiples métodos
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Método 1: Análisis por columnas (más preciso)
    # Dividir imagen en 20 columnas
    col_width = w // 20
    column_means = []
    
    for i in range(20):
        start = i * col_width
        end = start + col_width if i < 19 else w
        col_section = gray[:, start:end]
        
        # Encontrar punto medio vertical (donde está el precio)
        # Buscar la zona más oscura (generalmente la línea del gráfico)
        vertical_profile = np.mean(col_section, axis=1)
        min_idx = np.argmin(vertical_profile)
        column_means.append(min_idx)
    
    # Regresión lineal sobre los puntos
    x = np.arange(len(column_means))
    y = np.array(column_means)
    
    try:
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        
        # En OpenCV, Y aumenta hacia abajo, así que invertimos
        angle = -np.degrees(np.arctan(slope * (h/w)))  # Ajustar por aspecto
        
        confidence = int(r_squared * 100)
        
    except:
        angle = 0
        confidence = 0
    
    # Determinar dirección con umbrales más estrictos
    if angle > 5 and confidence > 40:
        direction = "alcista"
    elif angle < -5 and confidence > 40:
        direction = "bajista"
    else:
        direction = "lateral"
    
    # Verificar consistencia (últimos 5 vs primeros 5 puntos)
    first_avg = np.mean(column_means[:5])
    last_avg = np.mean(column_means[-5:])
    consistency = abs(first_avg - last_avg)
    
    # Si la diferencia es pequeña, probablemente es lateral
    if consistency < (h * 0.05):  # Menos del 5% de altura
        direction = "lateral"
        confidence = max(0, confidence - 20)
    
    return {
        "direction": direction,
        "angle": round(float(angle), 2),
        "confidence": max(0, min(100, confidence)),
        "consistency": consistency
    }


def analyze_volatility(img):
    """
    Análisis mejorado de volatilidad
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    # Método 1: Desviación estándar por filas
    row_std = np.std(gray, axis=1)
    
    # Método 2: Diferencias entre columnas consecutivas
    col_diffs = np.diff(np.mean(gray, axis=0))
    col_volatility = np.std(col_diffs)
    
    # Combinar ambos métodos
    combined = (np.mean(row_std) + col_volatility) / 2
    
    # Normalizar de forma más conservadora
    normalized = min(100, (combined / 30) * 100)  # Ajustado para ser más realista
    
    if normalized > 65:
        level = "alta"
    elif normalized > 35:
        level = "media"
    else:
        level = "baja"
    
    return {
        "level": level,
        "score": round(float(normalized), 2)
    }


def detect_momentum(img):
    """
    Detección mejorada de momentum
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Dividir en 4 secciones
    quarter = w // 4
    sections = [
        gray[:, :quarter],
        gray[:, quarter:2*quarter],
        gray[:, 2*quarter:3*quarter],
        gray[:, 3*quarter:]
    ]
    
    # Calcular posición promedio vertical de cada sección
    positions = []
    for section in sections:
        vertical_profile = np.mean(section, axis=1)
        min_idx = np.argmin(vertical_profile)
        positions.append(min_idx)
    
    # Calcular cambio entre secciones
    changes = [positions[i+1] - positions[i] for i in range(3)]
    avg_change = np.mean(changes)
    recent_change = changes[-1]  # Último cambio (más importante)
    
    # Momentum basado en cambio reciente
    momentum_value = recent_change * 2  # Dar más peso al cambio reciente
    
    # Normalizar a 0-100
    max_change = h * 0.3  # 30% de la altura como máximo
    normalized = min(100, abs(momentum_value / max_change) * 100)
    
    # Determinar dirección (invertido porque Y crece hacia abajo)
    if abs(momentum_value) < (h * 0.03):  # Menos del 3% = neutral
        direction = "neutral"
        strength = 50
    elif momentum_value < 0:  # Subiendo
        direction = "alcista"
        strength = int(normalized)
    else:  # Bajando
        direction = "bajista"
        strength = int(normalized)
    
    return {
        "direction": direction,
        "strength": min(100, max(0, strength)),
        "recent_change": recent_change
    }


def analyze_recent_candles(img):
    """
    Analiza las últimas velas (20% derecho del gráfico)
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Enfocarse en el 20% más reciente
    recent = gray[:, int(w * 0.8):]
    
    # Analizar variación vertical
    vertical_variance = np.var(np.mean(recent, axis=1))
    
    # Analizar dirección reciente
    left_half = recent[:, :recent.shape[1]//2]
    right_half = recent[:, recent.shape[1]//2:]
    
    left_pos = np.argmin(np.mean(left_half, axis=1))
    right_pos = np.argmin(np.mean(right_half, axis=1))
    
    movement_diff = left_pos - right_pos
    
    # Clasificar movimiento
    if abs(movement_diff) < (h * 0.05):
        movement = "consolidando"
    elif movement_diff < 0:
        movement = "subiendo"
    else:
        movement = "bajando"
    
    # Clasificar patrón
    if vertical_variance > 800:
        pattern = "alta_volatilidad"
    elif vertical_variance > 300:
        pattern = "consolidación"
    else:
        pattern = "baja_actividad"
    
    return {
        "pattern": pattern,
        "movement": movement,
        "variance": vertical_variance
    }


def detect_reversal_patterns(img):
    """
    Detecta posibles reversiones de tendencia
    """
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Analizar últimos 30%
    recent = gray[:, int(w * 0.7):]
    
    # Dividir en 3 partes
    third = recent.shape[1] // 3
    part1 = recent[:, :third]
    part2 = recent[:, third:2*third]
    part3 = recent[:, 2*third:]
    
    # Posiciones
    pos1 = np.argmin(np.mean(part1, axis=1))
    pos2 = np.argmin(np.mean(part2, axis=1))
    pos3 = np.argmin(np.mean(part3, axis=1))
    
    # Detectar cambio de dirección
    trend1 = pos2 - pos1  # Primera mitad
    trend2 = pos3 - pos2  # Segunda mitad
    
    # Reversión si cambian de signo
    reversal = False
    if (trend1 > 0 and trend2 < 0) or (trend1 < 0 and trend2 > 0):
        if abs(trend1) > (h * 0.03) and abs(trend2) > (h * 0.03):
            reversal = True
    
    return {
        "detected": reversal,
        "strength": abs(trend2 - trend1) if reversal else 0
    }


def calculate_calibrated_strength(trend_data, volatility_data, momentum_data,
                                  candle_analysis, reversal_signals):
    """
    Calcula fuerza con calibración realista
    """
    # Base: confianza de la tendencia (peso 40%)
    base = trend_data["confidence"] * 0.4
    
    # Volatilidad (peso 20%)
    vol_component = volatility_data["score"] * 0.2
    
    # Momentum (peso 25%)
    momentum_component = momentum_data["strength"] * 0.25
    
    # Consistencia de velas recientes (peso 15%)
    if candle_analysis["movement"] == "consolidando":
        consistency = 40
    elif candle_analysis["pattern"] == "baja_actividad":
        consistency = 30
    else:
        consistency = 60
    
    consistency_component = consistency * 0.15
    
    # Penalización por reversión
    reversal_penalty = 0
    if reversal_signals["detected"]:
        reversal_penalty = -15
    
    # Calcular total
    total = base + vol_component + momentum_component + consistency_component + reversal_penalty
    
    # Limitar a rango realista
    return round(float(max(20, min(85, total))), 2)


def classify_market_state_realistic(trend_data, volatility_data, 
                                    candle_analysis, strength):
    """
    Clasificación realista del estado del mercado
    """
    direction = trend_data["direction"]
    volatility = volatility_data["level"]
    movement = candle_analysis["movement"]
    
    # Lateral si:
    # 1. Dirección es lateral
    # 2. Fuerza < 55
    # 3. Movimiento reciente es "consolidando"
    if direction == "lateral" or strength < 55 or movement == "consolidando":
        return "lateral"
    
    # Alcista
    if direction == "alcista":
        if volatility == "alta" and strength > 70:
            return "alcista_fuerte"
        elif volatility == "alta":
            return "alcista_volátil"
        else:
            return "alcista"
    
    # Bajista
    if direction == "bajista":
        if volatility == "alta" and strength > 70:
            return "bajista_fuerte"
        elif volatility == "alta":
            return "bajista_volátil"
        else:
            return "bajista"
    
    return "indefinido"


def diagnose_image(image_path):
    """Diagnóstico mejorado"""
    print(f"\n{'='*70}")
    print(f"📊 DIAGNÓSTICO: {os.path.basename(image_path)}")
    print(f"{'='*70}\n")
    
    result = analyze_image(image_path)
    
    print(f"🎯 TENDENCIA:")
    print(f"   • Dirección: {result['trend']} ({result['trend_angle']}°)")
    print(f"   • Confianza: {result['trend_confidence']}%")
    
    print(f"\n⚡ MOMENTUM:")
    print(f"   • Dirección: {result['momentum']}")
    print(f"   • Fuerza: {result['momentum_strength']}%")
    
    print(f"\n📊 VOLATILIDAD:")
    print(f"   • Nivel: {result['volatility']}")
    print(f"   • Score: {result['volatility_score']}")
    
    print(f"\n💪 FUERZA CALIBRADA: {result['strength']}%")
    print(f"🏷️  ESTADO: {result['market_state']}")
    print(f"🕯️  MOVIMIENTO RECIENTE: {result['recent_movement']}")
    
    if result['reversal_detected']:
        print(f"\n⚠️  REVERSIÓN DETECTADA")
    
    print(f"\n{'='*70}\n")
    
    return result


if __name__ == "__main__":
    test_images = ["m1.png", "m5.png", "m15.png"]
    
    for img_path in test_images:
        if os.path.exists(img_path):
            try:
                diagnose_image(img_path)
            except Exception as e:
                print(f"❌ Error: {e}")