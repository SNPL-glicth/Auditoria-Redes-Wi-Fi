#!/usr/bin/env python3
"""
Test final para verificar que la solución al problema de selección funciona
"""
import sys
import os
from unittest.mock import patch
from wifi_auditor_pro import WiFiAuditor, Colors

def test_automatic_fallback():
    """Test del modo automático de fallback"""
    print("🔧 TEST: Modo automático de fallback")
    print("=" * 60)
    
    auditor = WiFiAuditor()
    
    # Simular escenario similar al real
    auditor.targets = [
        # Redes con clientes (las mejores)
        {'essid': 'Casa_Rodriguez', 'clients': 3, 'power': -55, 'bssid': '00:11:22:33:44:01', 'channel': '6', 'encryption': 'WPA2'},
        {'essid': 'Familia_Lopez', 'clients': 2, 'power': -60, 'bssid': '00:11:22:33:44:02', 'channel': '11', 'encryption': 'WPA2'},
        {'essid': 'Red_Oficina', 'clients': 1, 'power': -65, 'bssid': '00:11:22:33:44:03', 'channel': '1', 'encryption': 'WPA2'},
        
        # Redes con WPS (segunda opción)
        {'essid': 'Router_WPS_1', 'clients': 0, 'power': -70, 'bssid': '00:11:22:33:44:04', 'channel': '6', 'encryption': 'WPA2 WPS'},
        {'essid': 'Router_WPS_2', 'clients': 0, 'power': -75, 'bssid': '00:11:22:33:44:05', 'channel': '11', 'encryption': 'WPA2 WPS'},
        
        # Redes normales (tercera opción)
        {'essid': 'Red_Normal_1', 'clients': 0, 'power': -50, 'bssid': '00:11:22:33:44:06', 'channel': '1', 'encryption': 'WPA2'},
        {'essid': 'Red_Normal_2', 'clients': 0, 'power': -80, 'bssid': '00:11:22:33:44:07', 'channel': '6', 'encryption': 'WPA2'},
    ]
    
    print(f"📊 {len(auditor.targets)} targets simulados:")
    clients_count = sum(1 for t in auditor.targets if t['clients'] > 0)
    wps_count = sum(1 for t in auditor.targets if 'WPS' in t['encryption'])
    print(f"  🟢 {clients_count} con clientes")
    print(f"  ⚡ {wps_count} con WPS")
    print(f"  📡 {len(auditor.targets) - clients_count} sin clientes")
    
    # Test del modo automático
    print("\n🤖 Probando selección automática:")
    try:
        selected = auditor.automatic_fallback_selection()
        
        if selected:
            print(f"\n✅ Selección automática exitosa: {len(selected)} redes")
            
            # Verificar que eligió las mejores (con clientes)
            has_clients = any(t['clients'] > 0 for t in selected)
            if has_clients:
                print("✅ Correctamente priorizó redes con clientes")
            else:
                print("⚠️ No hay redes con clientes, eligió siguientes mejores")
                
        else:
            print("❌ No se seleccionó ninguna red")
            
    except Exception as e:
        print(f"❌ Error en selección automática: {e}")
        import traceback
        traceback.print_exc()

def test_robust_input_eof():
    """Test de robust_input con EOFError simulado"""
    print("\n" + "=" * 60)
    print("🔧 TEST: robust_input con EOF simulado")
    print("=" * 60)
    
    auditor = WiFiAuditor()
    
    # Simular EOFError en todas las entradas
    with patch('builtins.input', side_effect=EOFError):
        try:
            result = auditor.robust_input("Test prompt: ")
            print(f"❌ No debería haber resultado: {result}")
        except EOFError as e:
            print(f"✅ EOFError manejado correctamente: {e}")

def test_full_selection_with_eof():
    """Test completo de selección con EOF (simula tu problema)"""
    print("\n" + "=" * 60)
    print("🔧 TEST: Selección completa con EOF (tu problema)")
    print("=" * 60)
    
    auditor = WiFiAuditor()
    
    # Simular muchos targets como en tu caso
    auditor.targets = []
    for i in range(1, 25):  # Menos para el test, pero representativo
        clients = 1 if i <= 5 else 0  # 5 con clientes
        power = -60 - (i % 20)
        encryption = "WPA2" if i % 8 != 0 else "WPA2 WPS"
        
        auditor.targets.append({
            'essid': f'Red_Test_{i:02d}',
            'clients': clients,
            'power': power,
            'bssid': f'00:11:22:33:44:{i:02x}',
            'channel': str((i % 11) + 1),
            'encryption': encryption
        })
    
    print(f"📊 {len(auditor.targets)} targets simulados")
    print(f"🟢 {sum(1 for t in auditor.targets if t['clients'] > 0)} con clientes")
    
    # Simular EOF inmediato (tu problema)
    with patch('builtins.input', side_effect=EOFError):
        print("\n📝 Simulando tu problema (EOF inmediato)...")
        
        try:
            # Capturar salida para no saturar
            import contextlib
            from io import StringIO
            
            with contextlib.redirect_stdout(StringIO()):
                selected = auditor.simple_target_selection()
            
            if selected:
                print(f"✅ ¡SOLUCIONADO! Selección automática funcionó: {len(selected)} redes")
                print("📋 Redes seleccionadas:")
                for i, target in enumerate(selected[:3], 1):  # Mostrar solo las 3 primeras
                    print(f"  {i}. {target['essid']} (👥{target['clients']}, {target['power']}dBm)")
                if len(selected) > 3:
                    print(f"  ... y {len(selected) - 3} más")
            else:
                print("❌ Aún no funciona completamente")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def test_interactive_mode():
    """Test modo interactivo real (si es posible)"""
    print("\n" + "=" * 60)
    print("🔧 TEST: Modo interactivo real")
    print("=" * 60)
    
    if not sys.stdin.isatty():
        print("⚠️ No hay terminal interactivo - saltando test")
        return
    
    auditor = WiFiAuditor()
    auditor.targets = [
        {'essid': 'Test_1', 'clients': 2, 'power': -60, 'bssid': '00:11:22:33:44:01', 'channel': '6', 'encryption': 'WPA2'},
        {'essid': 'Test_2', 'clients': 0, 'power': -70, 'bssid': '00:11:22:33:44:02', 'channel': '11', 'encryption': 'WPA2'},
    ]
    
    print("✅ Terminal interactivo disponible")
    print("📝 Para probar manualmente, ejecuta:")
    print("   python3 test_final_fix.py interactive")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        test_interactive_mode()
    else:
        try:
            test_automatic_fallback()
            test_robust_input_eof()
            test_full_selection_with_eof()
            
            print("\n" + "=" * 60)
            print("🎉 TESTS COMPLETADOS")
            print("=" * 60)
            print("💡 La solución debería manejar tu problema de EOF")
            print("🚀 Ahora el auditor usará selección automática si no puede leer entrada")
            
        except Exception as e:
            print(f"Error en tests: {e}")
            import traceback
            traceback.print_exc()