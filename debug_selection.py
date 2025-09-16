#!/usr/bin/env python3
"""
Debug específico para el problema de selección de objetivos
"""

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

def debug_process_selection_preview(choice, targets):
    """Debug de la función de selección - versión simplificada"""
    print(f"🔧 DEBUG: Procesando elección '{choice}' con {len(targets)} targets")
    
    choice = choice.lower().strip()
    selected = []
    
    try:
        if choice == 'all':
            selected = targets.copy()
            print(f"✅ Opción 'all' seleccionada: {len(selected)} targets")
            
        elif choice == 'clients':
            selected = [t for t in targets if t['clients'] > 0]
            selected = sorted(selected, key=lambda x: x['clients'], reverse=True)
            print(f"✅ Opción 'clients' seleccionada: {len(selected)} targets con clientes")
            
        else:
            print(f"🔍 Verificando si '{choice}' es número...")
            # Números específicos
            if ',' in choice or choice.isdigit():
                print(f"✅ Detectado como entrada numérica")
                indices = []
                
                print(f"🔍 Dividiendo entrada: {choice.replace(' ', '').split(',')}")
                for num_str in choice.replace(' ', '').split(','):
                    print(f"  - Procesando: '{num_str}'")
                    if num_str.isdigit():
                        num = int(num_str)
                        print(f"    → Número válido: {num}")
                        if 1 <= num <= len(targets):
                            indices.append(num - 1)  # Convertir a índice base 0
                            print(f"    ✅ Número {num} dentro del rango (1-{len(targets)})")
                        else:
                            print(f"    ❌ Número {num} fuera de rango (1-{len(targets)})")
                            return None
                    else:
                        print(f"    ❌ '{num_str}' no es un dígito")
                
                print(f"🔍 Índices encontrados: {indices}")
                if indices:
                    selected = [targets[i] for i in indices]
                    print(f"✅ Seleccionados {len(selected)} targets por índices")
                    for i, target in enumerate(selected):
                        print(f"  - {i+1}. {target['essid']}")
                else:
                    print(f"❌ No se encontraron índices válidos")
                    return None
            else:
                print(f"❌ '{choice}' no es una opción reconocida")
                return None  # Selección inválida
        
        return selected
        
    except Exception as e:
        print(f"❌ ERROR en proceso: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_debug_selection():
    """Test completo de debugging"""
    print("🔧 INICIO DE DEBUG - SELECCIÓN DE OBJETIVOS")
    print("=" * 60)
    
    # Simular targets de prueba
    targets = [
        {'essid': 'Red_Test_1', 'clients': 2, 'power': -65},
        {'essid': 'Red_Test_2', 'clients': 0, 'power': -70},
        {'essid': 'Red_Test_3', 'clients': 1, 'power': -55},
    ]
    
    print(f"📊 Targets simulados: {len(targets)}")
    for i, target in enumerate(targets, 1):
        print(f"  {i}. {target['essid']} (Clientes: {target['clients']}, Señal: {target['power']}dBm)")
    
    print("\n" + "=" * 60)
    print("🧪 PROBANDO DIFERENTES SELECCIONES")
    print("=" * 60)
    
    # Pruebas
    test_cases = [
        "1",       # Un número
        "2",       # Otro número  
        "1,3",     # Múltiples números
        "clients", # Solo clientes
        "all",     # Todos
        "4",       # Fuera de rango
        "abc",     # Inválido
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Probando: '{test_case}'")
        print("-" * 30)
        result = debug_process_selection_preview(test_case, targets)
        if result:
            print(f"✅ Resultado: {len(result)} targets seleccionados")
        else:
            print(f"❌ Resultado: None (selección inválida)")
        print("-" * 30)

def interactive_debug():
    """Debug interactivo"""
    print("🔧 DEBUG INTERACTIVO - SELECCIÓN DE OBJETIVOS")
    print("=" * 60)
    
    # Simular targets
    targets = [
        {'essid': 'Movistar_Casa', 'clients': 3, 'power': -60},
        {'essid': 'Claro_Hogar', 'clients': 0, 'power': -75},
        {'essid': 'ETB_Familia', 'clients': 1, 'power': -50},
        {'essid': 'TP-Link_123', 'clients': 0, 'power': -80},
    ]
    
    print("📊 Redes simuladas:")
    for i, target in enumerate(targets, 1):
        client_emoji = "🟢" if target['clients'] > 0 else "🔴"
        print(f"  {i}. {target['essid']:15} | {target['power']}dBm | {client_emoji} {target['clients']} clientes")
    
    print("\nOpciones de selección:")
    print("1-4. Seleccionar por números (ej: 1,3)")
    print("all. Todos los objetivos")
    print("clients. Solo redes con clientes (RECOMENDADO)")
    print("q. Salir")
    
    while True:
        try:
            choice = input(f"\n{Colors.CYAN}Tu selección: {Colors.END}").strip()
            
            if choice.lower() == 'q':
                print("👋 Saliendo del debug...")
                break
            
            print(f"\n🔍 DEBUGGING SELECCIÓN: '{choice}'")
            print("=" * 40)
            
            result = debug_process_selection_preview(choice, targets)
            
            if result:
                print(f"\n🎯 RESULTADO FINAL:")
                print("─" * 30)
                for i, target in enumerate(result, 1):
                    difficulty = "FÁCIL" if target['clients'] > 0 else "MEDIO" if target['power'] > -70 else "DIFÍCIL"
                    color = Colors.GREEN if difficulty == "FÁCIL" else Colors.YELLOW if difficulty == "MEDIO" else Colors.RED
                    print(f"{i}. {color}{target['essid']}{Colors.END} | {target['power']}dBm | 👥{target['clients']} | {difficulty}")
                print("─" * 30)
                print(f"📊 Total: {len(result)} redes seleccionadas")
            else:
                print(f"\n❌ RESULTADO: Selección inválida")
            
            print("=" * 40)
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}🛑 Debug interrumpido{Colors.END}")
            break
        except Exception as e:
            print(f"{Colors.RED}❌ Error inesperado: {e}{Colors.END}")

if __name__ == "__main__":
    print("Selecciona modo de debug:")
    print("1. Test automático")
    print("2. Debug interactivo")
    
    try:
        mode = input("Modo (1/2): ").strip()
        if mode == "1":
            test_debug_selection()
        elif mode == "2":
            interactive_debug()
        else:
            print("Modo inválido")
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")