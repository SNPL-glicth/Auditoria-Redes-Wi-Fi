#!/usr/bin/env python3
"""
Test DEBUG para ver qué está pasando con el escaneo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wifi_auditor_pro import WiFiAuditor

def debug_test():
    if os.geteuid() != 0:
        print("❌ Ejecuta con sudo")
        return False
    
    print("🔍 DEBUG Test - Escaneo WiFi")
    print("=" * 40)
    
    try:
        auditor = WiFiAuditor()
        
        if not auditor.check_dependencies():
            print("❌ Faltan dependencias")
            return False
        
        if not auditor.select_interface():
            print("❌ No se pudo seleccionar interfaz")
            return False
        
        print(f"📡 Interfaz: {auditor.interface}")
        
        # Habilitar modo monitor
        print("\n🔄 Habilitando modo monitor...")
        if auditor.enable_monitor_mode():
            print(f"✅ Monitor habilitado: {auditor.monitor_interface}")
            
            # Escaneo corto para debug
            print("\n🔍 Escaneando (10 segundos)...")
            if auditor.scan_networks(scan_time=10):
                print(f"📊 Resultado: {len(auditor.targets)} redes")
                
                if auditor.targets:
                    print("\n📋 Redes encontradas:")
                    for i, target in enumerate(auditor.targets[:5], 1):
                        print(f"   {i}. {target['essid']} - {target['encryption']}")
                else:
                    print("⚠️  Ninguna red parseada correctamente")
                    
            else:
                print("❌ Error en escaneo")
        else:
            print("❌ No se pudo habilitar modo monitor")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n🧹 Limpiando...")
        if 'auditor' in locals():
            auditor.cleanup()
    
    return True

if __name__ == "__main__":
    debug_test()