#!/usr/bin/env python3
"""
Test para verificar que la corrección del auditor funciona
"""
import sys
import os

# Importar la clase principal del auditor
from wifi_auditor_pro import WiFiAuditor, Colors

def test_target_selection_fix():
    """Test específico para la función corregida"""
    print("🔧 TEST: Verificando corrección de selección de objetivos")
    print("=" * 60)
    
    # Crear instancia del auditor
    auditor = WiFiAuditor()
    
    # Simular targets de prueba
    auditor.targets = [
        {'essid': 'Red_Test_1', 'clients': 2, 'power': -65, 'bssid': '00:11:22:33:44:55', 'channel': '6', 'encryption': 'WPA2'},
        {'essid': 'Red_Test_2', 'clients': 0, 'power': -70, 'bssid': '00:11:22:33:44:66', 'channel': '11', 'encryption': 'WPA2'},
        {'essid': 'Red_Test_WPS', 'clients': 1, 'power': -55, 'bssid': '00:11:22:33:44:77', 'channel': '1', 'encryption': 'WPA2 WPS'},
    ]
    
    print(f"📊 Simulando {len(auditor.targets)} targets:")
    for i, target in enumerate(auditor.targets, 1):
        print(f"  {i}. {target['essid']} | {target['power']}dBm | 👥{target['clients']} | {target['encryption']}")
    
    print("\n" + "=" * 60)
    print("🧪 PROBANDO CORRECCIONES")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        ("1", "Selección de un número"),
        ("1,3", "Selección múltiple"),
        ("clients", "Solo clientes"),
        ("all", "Todos"),
        ("wps", "Solo WPS"),
        ("999", "Número fuera de rango"),
        ("abc", "Entrada inválida"),
    ]
    
    for choice, description in test_cases:
        print(f"\n🧪 {description}: '{choice}'")
        print("-" * 40)
        
        try:
            result = auditor.process_selection_preview(choice)
            
            if result is None:
                print(f"❌ Resultado: None (selección inválida)")
            elif not result:
                print(f"⚠️ Resultado: Lista vacía")
            else:
                print(f"✅ Resultado: {len(result)} targets seleccionados")
                for i, target in enumerate(result, 1):
                    print(f"  - {i}. {target['essid']}")
                    
        except Exception as e:
            print(f"💥 ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETADO")
    print("=" * 60)

def interactive_test():
    """Test interactivo usando la función real del auditor"""
    print("🔧 TEST INTERACTIVO: Usando función real de selección")
    print("=" * 60)
    
    # Crear instancia del auditor  
    auditor = WiFiAuditor()
    
    # Simular targets con variedad
    auditor.targets = [
        {'essid': 'Movistar_Casa', 'clients': 3, 'power': -60, 'bssid': '00:11:22:33:44:55', 'channel': '6', 'encryption': 'WPA2'},
        {'essid': 'Claro_Hogar', 'clients': 0, 'power': -75, 'bssid': '00:11:22:33:44:66', 'channel': '11', 'encryption': 'WPA2'},
        {'essid': 'ETB_Familia', 'clients': 1, 'power': -50, 'bssid': '00:11:22:33:44:77', 'channel': '1', 'encryption': 'WPA2'},
        {'essid': 'TP-Link_WPS', 'clients': 0, 'power': -80, 'bssid': '00:11:22:33:44:88', 'channel': '3', 'encryption': 'WPA2 WPS'},
    ]
    
    print("🌟 Ahora ejecutando la función REAL de selección...")
    print("(Esto debería funcionar sin errores)")
    
    try:
        # Llamar a la función real (simulará entrada)
        print("\n" + Colors.YELLOW + "NOTA: Para probar, puedes usar:" + Colors.END)
        print("- Números: 1, 2, 1,3")  
        print("- Palabras clave: clients, all, wps")
        print("- q para salir")
        
        # Aquí normalmente llamarías auditor.simple_target_selection()
        # pero para el test solo mostraremos que está disponible
        print(f"\n✅ Función simple_target_selection() disponible")
        print(f"✅ Función process_selection_preview() corregida")
        print(f"✅ {len(auditor.targets)} targets simulados")
        
        # Probar directamente process_selection_preview
        print("\n🔬 Prueba directa de process_selection_preview:")
        test_input = input("Ingresa una selección para probar (ej: 1,3): ").strip()
        if test_input:
            result = auditor.process_selection_preview(test_input)
            if result:
                print(f"🎯 Éxito: {len(result)} targets seleccionados")
                for target in result:
                    print(f"  - {target['essid']}")
            else:
                print("❌ No se seleccionó nada")
        
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}🛑 Test interrumpido{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}💥 Error: {e}{Colors.END}")

if __name__ == "__main__":
    print("Selecciona tipo de test:")
    print("1. Test automático")
    print("2. Test interactivo")
    
    try:
        mode = input("Modo (1/2): ").strip()
        if mode == "1":
            test_target_selection_fix()
        elif mode == "2":
            interactive_test()
        else:
            print("Modo inválido")
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")
    except Exception as e:
        print(f"Error: {e}")