# WiFi Auditor Pro v2.0 - MODO ULTRA AGRESIVO
## Ejemplos de Uso para Obtener Contraseñas WiFi

### 🚀 MODO ULTRA AGRESIVO AUTOMÁTICO (RECOMENDADO)

#### Opción 1: Modo Completamente Automático
```bash
sudo python3 wifi_auditor_pro.py --auto
```
**¿Qué hace?**
- ✅ Selecciona automáticamente los mejores objetivos
- ✅ Prioriza redes con clientes conectados
- ✅ Genera wordlists inteligentes personalizadas
- ✅ Ataque paralelo con múltiples herramientas
- ✅ NO requiere intervención del usuario

#### Opción 2: Modo Caza (Busca hasta encontrar contraseñas)
```bash
sudo python3 wifi_auditor_pro.py --hunt --max-targets 3
```
**¿Qué hace?**
- 🎯 Modo "implacable" que no se detiene
- 🎯 Busca hasta encontrar al menos una contraseña
- 🎯 Limita a 3 objetivos simultáneos
- 🎯 Ultra agresivo en captura de handshakes

### ⚡ MODOS RÁPIDOS

#### Escaneo Rápido + Auto
```bash
sudo python3 wifi_auditor_pro.py --auto --time 15 -v
```

#### Solo Redes con Clientes (Más Efectivo)
```bash
sudo python3 wifi_auditor_pro.py --auto --time 20 --max-targets 2
```

### 🎛️ OPCIONES AVANZADAS

#### Interfaz Específica + Modo Verboso
```bash
sudo python3 wifi_auditor_pro.py --auto -i wlan0 -v
```

#### Solo Captura (Sin Cracking)
```bash
sudo python3 wifi_auditor_pro.py --auto --no-crack --time 30
```

### 📊 CÓMO FUNCIONA EL MODO ULTRA AGRESIVO

1. **Selección Inteligente de Objetivos**:
   - 🟢 **Score Alto**: Redes con clientes + buena señal + WPS
   - 🟡 **Score Medio**: Buena señal pero sin clientes
   - 🔴 **Score Bajo**: Señal débil y sin clientes

2. **Captura de Handshake Ultra Agresiva**:
   - 📡 **3 capturas simultáneas**: airodump-ng + tshark + tcpdump
   - 💥 **Bombardeo masivo**: 8+ procesos de deauth continuos
   - ⚡ **Técnicas múltiples**: aireplay-ng + mdk3 + velocidades variables

3. **Cracking Paralelo Inteligente**:
   - 🧠 **Wordlist personalizada**: Basada en ESSID, BSSID y patrones latinos
   - 🔄 **Ataques paralelos**: aircrack-ng + hashcat simultáneamente
   - 🎯 **Top 5 wordlists**: En paralelo por prioridad

### 📈 ESTRATEGIAS DE ÉXITO

#### Para Máximo Éxito:
```bash
# Estrategia recomendada
sudo python3 wifi_auditor_pro.py --hunt --time 30 --max-targets 2 -v

# Si hay muchas redes
sudo python3 wifi_auditor_pro.py --auto --time 45 --max-targets 5
```

#### Para Redes Difíciles:
```bash
# Más tiempo de escaneo + modo caza
sudo python3 wifi_auditor_pro.py --hunt --time 60 --max-targets 1 -v
```

### 🔧 UTILIDADES ADICIONALES

#### Analizar Resultados:
```bash
python3 wifi_utils.py convert resultado.json html
python3 wifi_utils.py analyze wordlists/rockyou.txt
```

#### Optimizar Wordlists:
```bash
python3 wifi_utils.py optimize entrada.txt salida_optimizada.txt
python3 wifi_utils.py generate "FamiliaGarcia" "CasaPedro" -o custom.txt
```

### 🎯 CONSEJOS PARA OBTENER CONTRASEÑAS

1. **Usa siempre el modo `--auto`**: Selecciona los mejores objetivos automáticamente
2. **Prioriza redes con clientes**: Son 10x más fáciles de crackear
3. **Deja tiempo suficiente**: 30-45 segundos de escaneo inicial
4. **Modo `--hunt` para redes difíciles**: No se rinde hasta encontrar contraseñas
5. **Revisa los logs**: Información detallada del progreso

### 🚨 INFORMACIÓN IMPORTANTE

- **Permisos**: Siempre ejecutar con `sudo`
- **Dependencias**: Ejecutar `sudo ./install_dependencies.sh` primero
- **Legal**: Solo para redes propias o con autorización expresa
- **Paciencia**: El modo ultra agresivo puede tomar tiempo pero es muy efectivo

### 📂 ARCHIVOS GENERADOS

- `handshakes/`: Handshakes capturados
- `audit_results_*.json`: Resultados en JSON
- `audit_session_*.log`: Logs detallados
- `wordlists/ultra_custom_*.txt`: Wordlists personalizadas

### 🎉 EJEMPLO DE SALIDA EXITOSA

```
🎆 CONTRASEÑA ENCONTRADA! 🎆
Red: FamiliaGarcia
Contraseña: garcia123
Método: Dictionary Attack
Herramienta: aircrack-ng (AC-0)
```

¡Tu WiFi Auditor Ultra Agresivo está listo para obtener contraseñas de manera completamente automática!