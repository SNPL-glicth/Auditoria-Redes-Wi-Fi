# WiFi Auditor Pro v2.0 - MODO ULTRA AGRESIVO 🔥

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux-orange.svg)](https://linux.org)
[![Status](https://img.shields.io/badge/status-Active-success.svg)](https://github.com/SNPL-glicth/Auditoria-Redes-Wi-Fi)

## 🚀 **AUDITOR WIFI COMPLETAMENTE AUTOMÁTICO**

**WiFi Auditor Pro v2.0** es una herramienta de auditoría de seguridad WiFi ultra agresiva y completamente automática, diseñada para profesionales en ciberseguridad. Combina técnicas avanzadas de captura de handshakes, cracking paralelo y selección inteligente de objetivos.

### ✨ **CARACTERÍSTICAS PRINCIPALES**

🧠 **Selección Automática Inteligente**
- Algoritmo de scoring que evalúa objetivos automáticamente
- Prioriza redes con clientes conectados (10x más efectivas)
- Análisis de patrones de nombres de red
- Descarte automático de redes corporativas/públicas

⚡ **Captura Ultra Agresiva**
- 3 capturas simultáneas: airodump-ng + tshark + tcpdump
- 8+ procesos de deauth con estrategias múltiples
- Bombardeo masivo continuo hasta capturar EAPOL válidos
- Técnicas avanzadas: aireplay-ng + mdk3 + velocidades variables

🧨 **Cracking Paralelo Masivo**
- Wordlists ultra inteligentes generadas automáticamente
- Patrones regionales latinoamericanos optimizados
- Ataques paralelos con aircrack-ng + hashcat simultáneamente
- Análisis del BSSID para generar patrones adicionales

🎯 **Modo Completamente Automático**
- Ejecución sin intervención del usuario
- Modo "Caza" que no se detiene hasta encontrar contraseñas
- Configuraciones automáticas optimizadas
- Interfaz adaptativa según el modo de operación

## 📦 **INSTALACIÓN RÁPIDA**

### 1. Clonar el Repositorio
```bash
git clone https://github.com/SNPL-glicth/Auditoria-Redes-Wi-Fi.git
cd Auditoria-Redes-Wi-Fi
```

### 2. Instalar Dependencias (Automático)
```bash
sudo ./install_dependencies.sh
```

### 3. ¡Listo para Usar!
```bash
# Modo manual con información visual (recomendado)
sudo python3 wifi_auditor_pro.py

# O modo completamente automático
sudo python3 wifi_auditor_pro.py --auto
```

## 🎯 **USO RÁPIDO**

### **Modo Manual Inteligente (Recomendado)**
```bash
# Tú eliges, pero con información visual de dificultad
sudo python3 wifi_auditor_pro.py
```

### **Modo Automático Completo**
```bash
# El sistema elige automáticamente los mejores objetivos
sudo python3 wifi_auditor_pro.py --auto
```

### **Modo Caza Implacable**
```bash
sudo python3 wifi_auditor_pro.py --hunt --max-targets 3 -v
```

### **Escaneo Rápido + Automático**
```bash
sudo python3 wifi_auditor_pro.py --auto --time 20 --max-targets 2
```

## 📊 **CÓMO FUNCIONA**

### 1. **Selección Inteligente**
```
🟢 Score Alto   → Redes con clientes + buena señal + WPS
🟡 Score Medio  → Buena señal pero sin clientes  
🔴 Score Bajo   → Señal débil y sin clientes
```

### 2. **Captura Ultra Agresiva**
- **Detección simultánea**: Redes Y clientes en una sola pasada
- **Capturas múltiples**: 3 herramientas capturando simultáneamente
- **Bombardeo masivo**: Hasta 8 procesos de deauth continuos
- **Verificación EAPOL**: Confirma paquetes válidos en tiempo real

### 3. **Cracking Paralelo**
- **Wordlist personalizada**: Generada específicamente para cada objetivo
- **Patrones latinos**: Apellidos, nombres y patrones regionales
- **Ataques paralelos**: aircrack-ng + hashcat trabajando simultáneamente
- **Priorización inteligente**: Las wordlists más efectivas primero

## 🛠️ **HERRAMIENTAS INCLUIDAS**

### **Archivo Principal**
- `wifi_auditor_pro.py` - Auditor principal ultra agresivo

### **Utilidades**
- `wifi_utils.py` - Herramientas adicionales de análisis
- `install_dependencies.sh` - Instalador automático de dependencias
- `EJEMPLOS_DE_USO.md` - Guía completa de uso

### **Configuración**
- `wifi_auditor_config.json` - Configuración personalizable
- `wordlists/` - Wordlists optimizadas incluidas

## ⚙️ **OPCIONES AVANZADAS**

```bash
# Todas las opciones disponibles
sudo python3 wifi_auditor_pro.py --help

# Opciones principales:
--auto              # Modo completamente automático
--hunt              # Modo caza (no se detiene)
--time SECONDS      # Tiempo de escaneo inicial
--max-targets N     # Máximo objetivos simultáneos
-i INTERFACE        # Interfaz WiFi específica
-v, --verbose       # Modo verboso detallado
--no-crack          # Solo capturar handshakes
```

## 📁 **ESTRUCTURA DEL PROYECTO**

```
Auditoria-Redes-Wi-Fi/
├── wifi_auditor_pro.py           # 🔥 Auditor principal ultra agresivo
├── wifi_utils.py                 # 🛠️ Utilidades adicionales
├── install_dependencies.sh       # 📦 Instalador automático
├── wifi_auditor_config.json      # ⚙️ Configuración
├── EJEMPLOS_DE_USO.md            # 📖 Guía de uso completa
├── README.md                     # 📝 Este archivo
├── wordlists/                    # 📚 Wordlists optimizadas
│   ├── common_passwords.txt
│   ├── latin_patterns.txt
│   ├── spanish_passwords.txt
│   └── ...
└── handshakes/                   # 🎯 Handshakes capturados (generado)
```

## 🚨 **REQUISITOS DEL SISTEMA**

- **Sistema Operativo**: Linux (Debian/Ubuntu/Kali recomendado)
- **Python**: 3.8 o superior
- **Privilegios**: Root (sudo)
- **Memoria RAM**: Mínimo 2GB
- **Interfaz WiFi**: Compatible con modo monitor

## 📈 **ESTRATEGIAS DE ÉXITO**

### **Para Máximo Éxito**
```bash
# Estrategia recomendada para la mayoría de casos
sudo python3 wifi_auditor_pro.py --hunt --time 30 --max-targets 2 -v
```

### **Para Entornos con Muchas Redes**
```bash
# Más objetivos pero limitando tiempo
sudo python3 wifi_auditor_pro.py --auto --time 45 --max-targets 5
```

### **Para Redes Muy Difíciles**
```bash
# Concentrarse en un solo objetivo con máxima agresividad
sudo python3 wifi_auditor_pro.py --hunt --time 60 --max-targets 1 -v
```

## 🎯 **CONSEJOS PROFESIONALES**

1. **Siempre usa `--auto`**: La selección automática es muy efectiva
2. **Prioriza redes con clientes**: Son 10x más fáciles de crackear
3. **Tiempo de escaneo adecuado**: 30-45 segundos es óptimo
4. **Modo `--hunt` para casos difíciles**: No se rinde hasta tener éxito
5. **Revisa los logs**: Información valiosa del progreso

## 📊 **EJEMPLO DE SALIDA**

```
🎆 CONTRASEÑA ENCONTRADA! 🎆
Red: FamiliaGarcia
Contraseña: garcia123
Método: Dictionary Attack
Herramienta: aircrack-ng (AC-0)
Wordlist: ultra_custom_FamiliaGarcia.txt
Tiempo: 2m 34s
```

## 🛡️ **USO ÉTICO Y LEGAL**

⚠️ **IMPORTANTE**: Esta herramienta está diseñada exclusivamente para:

- ✅ Auditorías de seguridad autorizadas
- ✅ Pruebas en redes propias
- ✅ Fines educativos en entornos controlados
- ✅ Evaluaciones de penetration testing con autorización

❌ **NO utilizar para**:
- Acceso no autorizado a redes
- Actividades ilegales
- Violación de la privacidad

El usuario es completamente responsable del uso de esta herramienta.

## 🤝 **CONTRIBUIR**

¡Las contribuciones son bienvenidas! Si quieres mejorar el proyecto:

1. Fork el repositorio
2. Crea una nueva rama (`git checkout -b feature/mejora-increible`)
3. Commit tus cambios (`git commit -am 'Agregar mejora increíble'`)
4. Push a la rama (`git push origin feature/mejora-increible`)
5. Abre un Pull Request

## 📝 **CHANGELOG**

### v2.0 (2024) - MODO ULTRA AGRESIVO
- ✨ Selección automática inteligente de objetivos
- ⚡ Captura ultra agresiva con técnicas múltiples
- 🧨 Cracking paralelo masivo
- 🧠 Wordlists ultra inteligentes
- 🎯 Modo completamente automático
- 🔥 Optimización para patrones latinoamericanos

### v1.0 (2024) - Versión Inicial
- 🛠️ Funcionalidades básicas de auditoría WiFi
- 📡 Captura de handshakes estándar
- 🔓 Cracking con wordlists básicas

## 📞 **SOPORTE**

Si encuentras algún problema o tienes sugerencias:

- 🐛 [Reportar un bug](https://github.com/SNPL-glicth/Auditoria-Redes-Wi-Fi/issues)
- 💡 [Sugerir una mejora](https://github.com/SNPL-glicth/Auditoria-Redes-Wi-Fi/issues)
- 📧 Email: SNPL-glicth@users.noreply.github.com

## 📄 **LICENCIA**

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 🏆 **RECONOCIMIENTOS**

- **aircrack-ng** - Suite principal de herramientas WiFi
- **hashcat** - Herramienta de cracking avanzada  
- **tshark** - Análisis de paquetes
- **Comunidad de seguridad** - Por inspiración y conocimiento compartido

---

<div align="center">

**⭐ Si este proyecto te es útil, por favor dale una estrella ⭐**

**🔥 WiFi Auditor Pro v2.0 - La herramienta definitiva para auditoría WiFi 🔥**

*Desarrollado con ❤️ por Nicolas SNPL para la comunidad de ciberseguridad*

</div>