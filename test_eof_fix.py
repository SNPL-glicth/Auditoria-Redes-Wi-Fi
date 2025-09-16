#!/usr/bin/env python3
"""
Test para verificar que el manejo de EOFError funciona correctamente
"""
import sys
import os
from unittest.mock import patch
from io import StringIO

# Importar la clase principal del auditor
from wifi_auditor_pro import WiFiAuditor, Colors

def test_eof_handling():
    """Test específico para manejo de EOFError"""
    print("🔧 TEST: Verificando manejo de EOFError")
    print("=" * 60)
    
    # Crear instancia del auditor
    auditor = WiFiAuditor()
    
    # Simular targets
    auditor.targets = [
        {'essid': 'Red_Test_1', 'clients': 2, 'power': -65, 'bssid': '00:11:22:33:44:55', 'channel': '6', 'encryption': 'WPA2'},
        {'essid': 'Red_Test_2', 'clients': 0, 'power': -70, 'bssid': '00:11:22:33:44:66', 'channel': '11', 'encryption': 'WPA2'},
    ]
    
    print(f"📊 Simulando {len(auditor.targets)} targets")
    
    # Test 1: safe_input maneja EOFError correctamente
    print("\n🧪 Test 1: safe_input con EOFError")
    print("-" * 40)
    
    # Simular EOFError
    with patch('builtins.input', side_effect=EOFError):
        try:
            result = auditor.safe_input("Test prompt: ", default="default_value")
            print(f"✅ safe_input devolvió: '{result}'")
            if result == "default_value":
                print("✅ Manejo de EOFError correcto")
            else:
                print(f"❌ Esperaba 'default_value', obtuvo '{result}'")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    # Test 2: safe_input maneja entrada normal
    print("\n🧪 Test 2: safe_input con entrada normal")
    print("-" * 40)
    
    with patch('builtins.input', return_value="entrada_normal"):
        try:
            result = auditor.safe_input("Test prompt: ")
            print(f"✅ safe_input devolvió: '{result}'")
            if result == "entrada_normal":
                print("✅ Entrada normal correcta")
            else:
                print(f"❌ Esperaba 'entrada_normal', obtuvo '{result}'")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    # Test 3: process_selection_preview maneja EOFError en bucle principal
    print("\n🧪 Test 3: Simular simple_target_selection con EOF")
    print("-" * 40)
    
    # Capturar stdout para logs
    original_stdout = sys.stdout
    captured_output = StringIO()
    
    # Simular EOFError en input
    with patch('builtins.input', side_effect=EOFError):
        with patch('sys.stdout', captured_output):
            try:
                result = auditor.simple_target_selection()
                print(f"✅ simple_target_selection devolvió: {result}")
                if result == []:
                    print("✅ EOF manejado correctamente, devolvió lista vacía")
                else:
                    print(f"❌ Esperaba lista vacía, obtuvo {result}")
            except Exception as e:
                print(f"❌ Error inesperado: {e}")
    
    # Restaurar stdout
    sys.stdout = original_stdout
    
    print("\n" + "=" * 60)
    print("✅ TEST EOF COMPLETADO")
    print("=" * 60)

def test_keyboard_interrupt_handling():
    """Test para manejo de KeyboardInterrupt"""
    print("\n🔧 TEST: Verificando manejo de KeyboardInterrupt")
    print("=" * 60)
    
    auditor = WiFiAuditor()
    auditor.targets = [
        {'essid': 'Red_Test_1', 'clients': 1, 'power': -65, 'bssid': '00:11:22:33:44:55', 'channel': '6', 'encryption': 'WPA2'},
    ]
    
    # Test KeyboardInterrupt en safe_input
    print("\n🧪 Test: safe_input con KeyboardInterrupt")
    print("-" * 40)
    
    with patch('builtins.input', side_effect=KeyboardInterrupt):
        try:
            result = auditor.safe_input("Test prompt: ")
            print(f"❌ No se lanzó KeyboardInterrupt como esperado")
        except KeyboardInterrupt:
            print("✅ KeyboardInterrupt manejado correctamente")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_eof_handling()
        test_keyboard_interrupt_handling()
    except Exception as e:
        print(f"Error en tests: {e}")
        import traceback
        traceback.print_exc()