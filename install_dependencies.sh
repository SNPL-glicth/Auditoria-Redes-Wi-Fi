#!/bin/bash

# WiFi Auditor Pro - Script de instalación de dependencias
# Desarrollado para auditoría de seguridad profesional
# Autor: Nicolas - Auditor de Seguridad

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Función de logging
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${CYAN}[${timestamp}] [INFO] ${message}${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[${timestamp}] [SUCCESS] ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}[${timestamp}] [WARNING] ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] [ERROR] ${message}${NC}"
            ;;
    esac
    echo "[${timestamp}] [${level}] ${message}" >> installation.log
}

# Verificar permisos de root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log "ERROR" "Este script debe ejecutarse como root"
        echo -e "${RED}Por favor ejecuta: sudo $0${NC}"
        exit 1
    fi
    
    # Verificar que sudo no expire durante la instalación
    if ! sudo -n true 2>/dev/null; then
        log "WARNING" "Refrescando credenciales de sudo..."
        sudo -v
    fi
}

# Detectar distribución
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        VERSION=$VERSION_ID
    else
        log "ERROR" "No se pudo detectar la distribución"
        exit 1
    fi
    
    log "INFO" "Distribución detectada: $PRETTY_NAME"
}

# Actualizar repositorios
update_repos() {
    log "INFO" "Actualizando repositorios del sistema..."
    
    case $DISTRO in
        "ubuntu"|"debian"|"kali")
            if ! apt update; then
                log "ERROR" "Fallo actualizando repositorios apt"
                return 1
            fi
            # Upgrade opcional para ser menos invasivo
            log "INFO" "Repositorios actualizados, saltando upgrade automático"
            ;;
        "fedora"|"centos"|"rhel")
            if command -v dnf &> /dev/null; then
                if ! dnf makecache; then
                    log "ERROR" "Fallo actualizando cache dnf"
                    return 1
                fi
            else
                if ! yum makecache; then
                    log "ERROR" "Fallo actualizando cache yum"
                    return 1
                fi
            fi
            ;;
        "arch"|"manjaro")
            if ! pacman -Sy --noconfirm; then
                log "ERROR" "Fallo actualizando repositorios pacman"
                return 1
            fi
            ;;
        *)
            log "WARNING" "Distribución no soportada completamente, intentando con apt..."
            apt update || {
                log "ERROR" "Fallo actualizando repositorios en distribución desconocida"
                return 1
            }
            ;;
    esac
    
    log "SUCCESS" "Repositorios actualizados"
}

# Instalar herramientas básicas
install_basic_tools() {
    log "INFO" "Instalando herramientas básicas del sistema..."
    
    local install_cmd
    local basic_packages
    
    case $DISTRO in
        "ubuntu"|"debian"|"kali")
            install_cmd="apt install -y"
            basic_packages="curl wget git build-essential python3 python3-pip net-tools wireless-tools iw rfkill"
            
            # Actualizar cache primero
            apt update || {
                log "ERROR" "No se pudo actualizar cache de apt"
                return 1
            }
            ;;
        "fedora"|"centos"|"rhel")
            if command -v dnf &> /dev/null; then
                install_cmd="dnf install -y"
                basic_packages="curl wget git gcc gcc-c++ make python3 python3-pip net-tools wireless-tools iw rfkill"
            else
                install_cmd="yum install -y"
                basic_packages="curl wget git gcc gcc-c++ make python3 python3-pip net-tools wireless-tools iw rfkill"
            fi
            ;;
        "arch"|"manjaro")
            install_cmd="pacman -S --noconfirm"
            basic_packages="curl wget git base-devel python python-pip net-tools wireless_tools iw rfkill"
            ;;
        *)
            log "ERROR" "Distribución no soportada"
            return 1
            ;;
    esac
    
    # Instalar paquetes uno por uno para mejor control de errores
    for package in $basic_packages; do
        log "INFO" "Instalando $package..."
        if ! $install_cmd $package; then
            log "WARNING" "Fallo instalando $package, continuando..."
        else
            log "SUCCESS" "$package instalado correctamente"
        fi
    done
    
    # Verificar instalaciones críticas
    local critical_tools="python3 curl wget git"
    local missing_critical=""
    
    for tool in $critical_tools; do
        if ! command -v $tool &> /dev/null; then
            missing_critical="$missing_critical $tool"
        fi
    done
    
    if [ -n "$missing_critical" ]; then
        log "ERROR" "Herramientas críticas faltantes:$missing_critical"
        return 1
    fi
    
    log "SUCCESS" "Herramientas básicas instaladas correctamente"
}

# Instalar aircrack-ng suite
install_aircrack_suite() {
    log "INFO" "Instalando suite aircrack-ng..."
    
    case $DISTRO in
        "ubuntu"|"debian")
            # Instalar desde repositorio oficial
            apt install -y aircrack-ng
            
            # Si es una versión antigua, compilar desde source
            if ! aircrack-ng --help | grep -q "hcxpcapngtool"; then
                log "INFO" "Compilando aircrack-ng desde código fuente para obtener última versión..."
                
                # Dependencias para compilación
                apt install -y build-essential autoconf automake libtool pkg-config \
                              libnl-3-dev libnl-genl-3-dev libssl-dev ethtool shtool \
                              libpcap-dev libsqlite3-dev libpcre3-dev libhwloc-dev \
                              libcmocka-dev hostapd wpasupplicant tcpdump screen iw \
                              usbutils expect
                
                # Descargar y compilar
                cd /tmp
                wget https://download.aircrack-ng.org/aircrack-ng-1.7.tar.gz
                tar -xzf aircrack-ng-1.7.tar.gz
                cd aircrack-ng-1.7
                
                autoreconf -i
                ./configure --with-experimental --enable-maintainer-mode
                make -j$(nproc)
                make install
                ldconfig
                
                cd /root
                rm -rf /tmp/aircrack-ng-1.7*
            fi
            ;;
        "kali")
            apt install -y aircrack-ng
            ;;
        "fedora"|"centos"|"rhel")
            if command -v dnf &> /dev/null; then
                dnf install -y aircrack-ng
            else
                yum install -y aircrack-ng
            fi
            ;;
        "arch"|"manjaro")
            pacman -S --noconfirm aircrack-ng
            ;;
    esac
    
    log "SUCCESS" "Suite aircrack-ng instalada"
}

# Instalar hashcat
install_hashcat() {
    log "INFO" "Instalando hashcat..."
    
    case $DISTRO in
        "ubuntu"|"debian"|"kali")
            apt install -y hashcat hashcat-utils
            ;;
        "fedora"|"centos"|"rhel")
            if command -v dnf &> /dev/null; then
                dnf install -y hashcat
            else
                # Instalar desde binario si no está en repos
                cd /tmp
                wget https://hashcat.net/files/hashcat-6.2.6.tar.gz
                tar -xzf hashcat-6.2.6.tar.gz
                cd hashcat-6.2.6
                make install
                cd /root
                rm -rf /tmp/hashcat-6.2.6*
            fi
            ;;
        "arch"|"manjaro")
            pacman -S --noconfirm hashcat hashcat-utils
            ;;
    esac
    
    log "SUCCESS" "Hashcat instalado"
}

# Instalar herramientas adicionales
install_additional_tools() {
    log "INFO" "Instalando herramientas adicionales de seguridad WiFi..."
    
    case $DISTRO in
        "ubuntu"|"debian"|"kali")
            apt install -y reaver bully pixiewps hcxtools hcxdumptool \
                          macchanger ettercap-text-only dnsmasq hostapd \
                          mdk3 mdk4 cowpatty pyrit john crunch
            ;;
        "fedora"|"centos"|"rhel")
            if command -v dnf &> /dev/null; then
                dnf install -y reaver bully macchanger ettercap dnsmasq \
                              hostapd john crunch
            else
                yum install -y reaver bully macchanger ettercap dnsmasq \
                              hostapd john crunch
            fi
            ;;
        "arch"|"manjaro")
            pacman -S --noconfirm reaver bully macchanger ettercap \
                                  dnsmasq hostapd john crunch
            
            # Instalar desde AUR si es necesario
            if command -v yay &> /dev/null; then
                yay -S --noconfirm hcxtools hcxdumptool pixiewps mdk3
            fi
            ;;
    esac
    
    log "SUCCESS" "Herramientas adicionales instaladas"
}

# Instalar herramientas Python
install_python_tools() {
    log "INFO" "Instalando librerías Python necesarias..."
    
    pip3 install --upgrade pip
    pip3 install scapy netaddr psutil colorama requests beautifulsoup4 \
                 pycrypto pycryptodome wifi matplotlib numpy pandas \
                 netifaces python-nmap
    
    log "SUCCESS" "Librerías Python instaladas"
}

# Configurar permisos y servicios
configure_system() {
    log "INFO" "Configurando sistema para auditoría WiFi..."
    
    # Detener servicios que pueden interferir
    systemctl stop NetworkManager
    systemctl stop wpa_supplicant
    systemctl stop ModemManager
    
    # Crear grupo para herramientas de red
    groupadd -f netdev 2>/dev/null
    
    # Configurar udev rules para interfaces
    cat > /etc/udev/rules.d/70-wifi-powersave.rules << 'EOF'
# Deshabilitar power management para adaptadores WiFi
ACTION=="add", SUBSYSTEM=="net", KERNEL=="wl*", RUN+="/usr/bin/iw dev %k set power_save off"
EOF
    
    # Reiniciar servicios necesarios
    systemctl enable NetworkManager
    systemctl start NetworkManager
    
    # Configurar rfkill
    rfkill unblock wifi
    rfkill unblock all
    
    log "SUCCESS" "Sistema configurado"
}

# Descargar wordlists comunes
download_wordlists() {
    log "INFO" "Descargando wordlists para auditoría..."
    
    # Crear directorio de wordlists
    mkdir -p wordlists
    cd wordlists
    
    # rockyou.txt
    if [ ! -f "rockyou.txt" ]; then
        log "INFO" "Descargando rockyou.txt..."
        if [ -f "/usr/share/wordlists/rockyou.txt.gz" ]; then
            gunzip -c /usr/share/wordlists/rockyou.txt.gz > rockyou.txt
        else
            wget -q https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
        fi
    fi
    
    # Common passwords
    if [ ! -f "common_passwords.txt" ]; then
        log "INFO" "Creando lista de passwords comunes..."
        cat > common_passwords.txt << 'EOF'
123456
password
12345678
qwerty
123456789
12345
1234
111111
1234567
dragon
123123
baseball
abc123
football
monkey
letmein
shadow
master
666666
qwertyuiop
123321
mustang
1234567890
michael
654321
superman
1qaz2wsx
7777777
121212
000000
qazwsx
123qwe
killer
trustno1
jordan
jennifer
zxcvbnm
asdfgh
hunter
buster
soccer
harley
batman
andrew
tigger
sunshine
iloveyou
2000
charlie
robert
thomas
hockey
ranger
daniel
starwars
klaster
112233
george
computer
michelle
jessica
pepper
1111
zxcvbn
555555
11111111
131313
freedom
777777
pass
maggie
159753
aaaaaa
ginger
princess
joshua
cheese
amanda
summer
love
ashley
nicole
chelsea
biteme
matthew
access
yankees
987654321
dallas
austin
thunder
taylor
matrix
mobilemail
mom
monitor
monitoring
montana
moon
moscow
EOF
    fi
    
    # DarkWeb wordlist (top 10000)
    if [ ! -f "darkweb2017-top10000.txt" ]; then
        log "INFO" "Descargando DarkWeb 2017 top 10000..."
        wget -q -O darkweb2017-top10000.txt \
            "https://raw.githubusercontent.com/insidersec/penta/master/wordlists/darkweb2017-top10000.txt" \
            2>/dev/null || log "WARNING" "No se pudo descargar darkweb2017-top10000.txt"
    fi
    
    cd ..
    log "SUCCESS" "Wordlists preparadas"
}

# Crear scripts auxiliares
create_auxiliary_scripts() {
    log "INFO" "Creando scripts auxiliares..."
    
    # Script para activar/desactivar modo monitor
    cat > monitor_mode.sh << 'EOF'
#!/bin/bash
# Script para gestión de modo monitor

case "$1" in
    "start")
        echo "Activando modo monitor..."
        sudo airmon-ng check kill
        sudo airmon-ng start $2
        ;;
    "stop")
        echo "Desactivando modo monitor..."
        sudo airmon-ng stop $2
        sudo systemctl restart NetworkManager
        ;;
    *)
        echo "Uso: $0 {start|stop} <interface>"
        exit 1
        ;;
esac
EOF
    chmod +x monitor_mode.sh
    
    # Script de limpieza del sistema
    cat > cleanup_system.sh << 'EOF'
#!/bin/bash
# Script de limpieza post-auditoría

echo "Limpiando archivos temporales..."
rm -f *.csv *.cap *.hccapx *.potfile
rm -f replay_arp-* replay_dec-*

echo "Restaurando servicios de red..."
sudo airmon-ng check
sudo systemctl restart NetworkManager
sudo systemctl restart wpa_supplicant

echo "Limpieza completada"
EOF
    chmod +x cleanup_system.sh
    
    log "SUCCESS" "Scripts auxiliares creados"
}

# Verificar instalación
verify_installation() {
    log "INFO" "Verificando instalación..."
    
    local errors=0
    local tools=(
        "aircrack-ng"
        "airmon-ng" 
        "airodump-ng"
        "aireplay-ng"
        "hashcat"
        "reaver"
        "wash"
        "iwconfig"
        "ifconfig"
    )
    
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            log "SUCCESS" "$tool está disponible"
        else
            log "ERROR" "$tool NO está disponible"
            ((errors++))
        fi
    done
    
    # Verificar Python modules
    python3 -c "import scapy, netaddr, psutil" 2>/dev/null && \
        log "SUCCESS" "Módulos Python disponibles" || \
        { log "ERROR" "Faltan módulos Python"; ((errors++)); }
    
    if [ $errors -eq 0 ]; then
        log "SUCCESS" "¡Instalación completada exitosamente!"
        echo
        echo -e "${GREEN}${BOLD}=== INSTALACIÓN COMPLETADA ===${NC}"
        echo -e "${CYAN}Todas las dependencias están instaladas correctamente${NC}"
        echo -e "${YELLOW}Puedes ejecutar ahora: sudo python3 wifi_auditor_pro.py${NC}"
    else
        log "ERROR" "Se encontraron $errors errores en la instalación"
        return 1
    fi
}

# Función principal
main() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "╦┌┐┌┌─┐┌┬┐┌─┐┬  ┬  ┌─┐┬─┐  ╔╦╗┌─┐┌─┐┬"
    echo "║│││└─┐ │ ├─┤│  │  ├┤ ├┬┘   ║ │ ││ ││  "
    echo "╩┘└┘└─┘ ┴ ┴ ┴┴─┘┴─┘└─┘┴└─   ╩ └─┘└─┘┴─┘"
    echo "     WiFi Auditor Pro Dependencies"
    echo -e "${NC}"
    echo -e "${GREEN}Instalador automático de dependencias${NC}"
    echo -e "${YELLOW}Para auditoría de seguridad profesional${NC}"
    echo
    
    log "INFO" "Iniciando instalación de dependencias para WiFi Auditor Pro"
    
    check_root
    detect_distro
    
    echo -e "${YELLOW}Se instalarán las siguientes herramientas:${NC}"
    echo "• Suite aircrack-ng (aircrack, airmon, airodump, aireplay)"
    echo "• Hashcat y hashcat-utils"
    echo "• Reaver, Bully, Pixiewps"
    echo "• HCX Tools (hcxdumptool, hcxpcapngtool)"
    echo "• Herramientas auxiliares (macchanger, ettercap, etc.)"
    echo "• Librerías Python necesarias"
    echo "• Wordlists comunes para cracking"
    echo
    
    read -p "¿Continuar con la instalación? [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "INFO" "Instalación cancelada por el usuario"
        exit 0
    fi
    
    # Ejecutar instalación
    update_repos || { log "ERROR" "Fallo actualizando repositorios"; exit 1; }
    install_basic_tools || { log "ERROR" "Fallo instalando herramientas básicas"; exit 1; }
    install_aircrack_suite || { log "ERROR" "Fallo instalando aircrack-ng"; exit 1; }
    install_hashcat || { log "ERROR" "Fallo instalando hashcat"; exit 1; }
    install_additional_tools || { log "ERROR" "Fallo instalando herramientas adicionales"; exit 1; }
    install_python_tools || { log "ERROR" "Fallo instalando herramientas Python"; exit 1; }
    configure_system || { log "ERROR" "Fallo configurando sistema"; exit 1; }
    download_wordlists || { log "WARNING" "Problemas descargando wordlists"; }
    create_auxiliary_scripts || { log "WARNING" "Problemas creando scripts auxiliares"; }
    
    verify_installation
}

# Ejecutar función principal
main "$@"