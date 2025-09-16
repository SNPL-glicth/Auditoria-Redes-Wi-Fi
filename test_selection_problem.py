#!/usr/bin/env python3
"""
Test para simular exactamente el problema que estás experimentando
"""
import sys
import os
from wifi_auditor_pro import WiFiAuditor, Colors

def simulate_selection_issue():
    """Simular el problema de selección interactiva"""
    print("🔧 SIMULANDO PROBLEMA DE SELECCIÓN")
    print("=" * 60)
    
    auditor = WiFiAuditor()
    
    # Simular muchos targets como en tu caso real
    auditor.targets = []
    for i in range(1, 94):  # 93 redes como en tu ejemplo
        clients = 1 if i <= 21 else 0  # 21 redes con clientes
        power = -60 - (i % 30)  # Señales variadas
        encryption = "WPA2" if i % 10 != 0 else "WPA2 WPS"  # Algunas con WPS
        
        auditor.targets.append({
            'essid': f'Red_Test_{i:02d}',
            'clients': clients,
            'power': power,
            'bssid': f'00:11:22:33:44:{i:02x}',
            'channel': str((i % 11) + 1),
            'encryption': encryption
        })
    
    print(f"📊 Simulando {len(auditor.targets)} targets")
    print(f"🟢 {sum(1 for t in auditor.targets if t['clients'] > 0)} con clientes")
    print(f"🔴 {sum(1 for t in auditor.targets if t['clients'] == 0)} sin clientes")
    
    # Verificar si tenemos entrada interactiva
    print(f"\n🔍 Diagnóstico del entorno:")
    print(f"   stdin.isatty(): {sys.stdin.isatty()}")
    print(f"   stdout.isatty(): {sys.stdout.isatty()}")
    print(f"   stderr.isatty(): {sys.stderr.isatty()}")
    
    if not sys.stdin.isatty():
        print(f"   ⚠️ PROBLEMA DETECTADO: stdin no es interactivo")
        print(f"   💡 Esto explica por qué no puedes escribir entrada")
    else:
        print(f"   ✅ stdin es interactivo - debería funcionar")
    
    # Probar selección manual
    print(f"\n🧪 Test de entrada manual:")
    try:
        # Simular entrada directa sin safe_input para diagnosticar
        print("Intento 1: input() directo")
        test_input = input("Escribe algo para probar: ")
        print(f"✅ input() funcionó: '{test_input}'")
        
        print("Intento 2: safe_input de auditor")
        test_input2 = auditor.safe_input("Escribe algo con safe_input: ")
        print(f"✅ safe_input funcionó: '{test_input2}'")
        
        print("Intento 3: Simulando selección simple")
        print("Opciones de prueba:")
        print("1. clients")
        print("2. 1,5,10") 
        print("3. all")
        
        choice = auditor.safe_input("Tu elección de prueba: ")
        print(f"✅ Elección recibida: '{choice}'")
        
        # Probar process_selection_preview
        result = auditor.process_selection_preview(choice)
        if result:
            print(f"✅ Procesamiento exitoso: {len(result)} targets")
        else:
            print(f"❌ No se procesó la selección correctamente")
        
    except EOFError as e:
        print(f"❌ EOFError capturado: {e}")
        print(f"💡 Esto confirma que el problema es EOF inmediato")
    except KeyboardInterrupt:
        print(f"🛑 Cancelado por usuario")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()

def test_forced_interactive():
    """Test forzando entrada interactiva"""
    print("\n" + "=" * 60)
    print("🔧 TEST FORZANDO ENTRADA INTERACTIVA")
    print("=" * 60)
    
    # Verificar si podemos forzar interactividad
    import sys
    
    print("Probando entrada forzada...")
    try:
        # Asegurar que stdout está conectado
        if hasattr(sys.stdout, 'write'):
            sys.stdout.write("Prompt de prueba: ")
            sys.stdout.flush()
            
            # Leer directamente
            line = sys.stdin.readline()
            if line:
                print(f"✅ Línea leída: '{line.strip()}'")
            else:
                print("❌ No se pudo leer línea")
                
    except Exception as e:
        print(f"❌ Error en entrada forzada: {e}")

if __name__ == "__main__":
    try:
        simulate_selection_issue()
        test_forced_interactive()
    except Exception as e:
        print(f"Error en simulación: {e}")
        import traceback
        traceback.print_exc()