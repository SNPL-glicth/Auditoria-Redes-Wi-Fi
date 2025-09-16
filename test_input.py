#!/usr/bin/env python3
"""
Test simple para verificar que el input funcione correctamente
"""

def test_selection_input():
    """Simular la selección de objetivos"""
    print("🔧 SIMULANDO SELECCIÓN DE OBJETIVOS")
    print("=" * 50)
    
    print("Opciones de selección:")
    print("1. Red de prueba 1")  
    print("2. Red de prueba 2")
    print("clients. Solo redes con clientes")
    print("q. Salir")
    
    while True:
        try:
            choice = input("\nTu selección: ").strip()
            
            if choice.lower() == 'q':
                print("Saliendo...")
                return
            elif choice.lower() == 'clients':
                print("🎯 OBJETIVOS SIMULADOS:")
                print("─" * 40)
                print(" 1. Red con clientes     | -65dBm | 👥3 | FÁCIL")
                print("─" * 40)
                print("📊 1 red | 3 clientes | Excelente elección")
                
                # Bucle separado para confirmación
                while True:
                    try:
                        confirm = input("\n¿Proceder con estos objetivos? (s/n): ").strip().lower()
                        
                        if confirm in ['s', 'si', 'y', 'yes']:
                            print("✅ Confirmado! Continuando...")
                            return
                        elif confirm in ['n', 'no']:
                            print("🔄 Volviendo a selección...")
                            break  # Salir del bucle de confirmación
                        else:
                            print("❌ Respuesta inválida. Por favor responde 's' o 'n'")
                            continue
                    except KeyboardInterrupt:
                        print("\n🛑 Operación cancelada")
                        return
            else:
                print("❌ Selección inválida. Inténtalo de nuevo.")
                continue
                
        except KeyboardInterrupt:
            print("\n🛑 Operación cancelada")
            return

if __name__ == "__main__":
    test_selection_input()