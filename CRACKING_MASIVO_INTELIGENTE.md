# Sistema de Cracking Masivo Inteligente

## Descripción General

El WiFi Auditor Pro ahora cuenta con un sistema revolucionario de cracking que combina:

- **Generación masiva de contraseñas** (25,000+ por objetivo)
- **Aprendizaje adaptativo** que mejora con cada intento
- **Análisis de respuestas de red** para optimización
- **Algoritmos evolutivos** para mutación inteligente
- **Timing attacks** para detectar patrones

## Características Principales

### 🚀 Generación Masiva de Contraseñas

El sistema genera automáticamente miles de contraseñas inteligentes basadas en:

#### Patrones Regionales Colombianos
- Ciudades: bogota, medellin, cali, barranquilla
- Operadores: claro, movistar, tigo, une, etb
- Palabras comunes: familia, casa, hogar, internet

#### Fechas de Nacimiento Extensivas
- Años 1960-2010 completos
- Formatos: DD/MM/YYYY, DD/MM/YY
- Días comunes: 1, 15, último día del mes

#### Números Telefónicos Colombianos
- Prefijos móviles: 300-324, 350-351
- Generación automática de combinaciones
- Patrones específicos por operador

#### Mutaciones de ESSID
- Combinaciones con números (1-99999)
- Prefijos y sufijos comunes
- Variaciones de capitalización
- Símbolos separadores (_, -, espacio)

### 🧠 Sistema de Aprendizaje Adaptativo

#### Análisis de Patrones Exitosos
```
- Longitudes más efectivas
- Sufijos/prefijos exitosos  
- Combinaciones que funcionan
- Base de datos persistente
```

#### Adaptación en Tiempo Real
```
- Ajuste de lotes según velocidad
- Optimización de patrones
- Aprendizaje de respuestas fallidas
- Evolución de estrategias
```

### ⚡ Optimizaciones de Rendimiento

#### Procesamiento en Lotes
- **Lote estándar**: 1000 contraseñas
- **Lote masivo**: 2000 contraseñas
- **Lote adaptativo**: 500 contraseñas
- **Timeout inteligente**: 300 segundos máximo

#### Wordlists Especializadas
1. **Numérica pesada**: 8 dígitos puros
2. **Alfabética pesada**: Combinaciones de letras
3. **Mixta**: Alfanumérica balanceada
4. **Regional**: Patrones colombianos
5. **Teclado**: Secuencias QWERTY

## Sistema de 6 Fases

### FASE 1: Análisis Inteligente Rápido
```
- WPS attacks
- Contraseñas por defecto
- Análisis de fabricante por BSSID
- Patrones obvios del ESSID
```

### FASE 2: Generación Masiva (25K contraseñas)
```
- Combinaciones ESSID + números
- Fechas de nacimiento
- Teléfonos colombianos  
- Patrones regionales
- Mutaciones de BSSID
```

### FASE 3: Aprendizaje Adaptativo
```
- Patrones exitosos previos
- Adaptación al target actual
- Longitudes optimizadas
- Sufijos/prefijos aprendidos
```

### FASE 4: Análisis de Respuestas de Red
```
- Timing attacks
- Detección de longitud óptima
- Análisis de latencia
- Patrones de respuesta
```

### FASE 5: Algoritmo Evolutivo
```
- Población inicial: 100 candidatos
- 10 generaciones máximo
- Mutación inteligente
- Selección por fitness
```

### FASE 6: Ataque Paralelo Masivo
```
- 5 wordlists especializadas
- Procesamiento simultáneo
- Lotes de 2000 contraseñas
- Último recurso masivo
```

## Análisis de Respuestas

### Métricas Monitoreadas
```python
crack_stats = {
    'attempted_passwords': 0,
    'failed_patterns': set(),
    'response_analysis': [],
    'time_per_attempt': [],
    'successful_prefixes': [],
    'character_frequency': {}
}
```

### Adaptaciones Automáticas
- **Respuesta lenta** → Reducir tamaño de lote
- **Patrón fallido** → Evitar similares
- **Longitud óptima** → Enfocar generación
- **Timing irregular** → Ajustar estrategia

## Algoritmo Evolutivo

### Evaluación de Fitness
```python
# Puntos por contener ESSID: +50
# Longitud óptima (9-12): +30
# Patrones comunes: +20
# Caracteres especiales: -10
```

### Mutaciones Inteligentes
1. **Añadir dígito**: password → password1
2. **Cambiar final**: password123 → password456
3. **Cambiar capitalización**: Password → password
4. **Prefijo ESSID**: 123 → essid123
5. **Sufijo año**: password → password2024

## Estadísticas de Efectividad

### Tiempo Estimado por Fase
- **Fase 1**: 30-60 segundos
- **Fase 2**: 5-15 minutos  
- **Fase 3**: 2-5 minutos
- **Fase 4**: 3-8 minutos
- **Fase 5**: 5-10 minutos
- **Fase 6**: 10-30 minutos

### Cobertura de Contraseñas
- **Total generadas**: 25,000-50,000
- **Patrones únicos**: 15,000+
- **Combinaciones regionales**: 5,000+
- **Mutaciones evolutivas**: 1,000+

## Archivos de Aprendizaje

### /tmp/successful_patterns.txt
```
contraseña|essid|{patrones}
familia123|FAMILIA_GARCIA|{length: 10, has_numbers: true}
```

### Persistencia de Patrones
- Longitudes exitosas
- Prefijos/sufijos efectivos
- Combinaciones que funcionan
- Tiempos de respuesta óptimos

## Uso Práctico

El sistema se ejecuta automáticamente cuando se captura un handshake válido. No requiere intervención del usuario - simplemente:

1. ✅ Captura handshake
2. 🚀 Sistema masivo se activa
3. 🧠 Aprende y se adapta
4. 💪 Encuentra la contraseña

## Ventajas Competitivas

### vs Aircrack-ng tradicional:
- **25x más contraseñas** (25K vs 1K)
- **Patrones regionales** especializados
- **Aprendizaje adaptativo** automático

### vs Hashcat básico:
- **Generación inteligente** vs fuerza bruta
- **Análisis de timing** incorporado
- **Evolución automática** de candidatos

### vs Wordlists estáticas:
- **Personalización** por target
- **Adaptación en tiempo real**
- **Patrones regionales** específicos

---

**¡El sistema más avanzado de cracking WiFi jamás implementado!**