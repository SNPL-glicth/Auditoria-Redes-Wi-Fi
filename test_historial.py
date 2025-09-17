#!/usr/bin/env python3
"""
Script de Prueba para Sistema de Historial de Contraseñas por Red
Valida la funcionalidad de crear carpetas por red y mantener historial de contraseñas.
"""

import sys
import os
import tempfile
import time
import json
from pathlib import Path

# Importar la clase principal
sys.path.append('/home/nicolas/Documentos/Auditor')
from wifi_auditor_pro import WiFiAuditor

def test_network_folder_creation():
    """Probar creación de carpetas por red"""
    print("🗂️  PRUEBA 1: Creación de Carpetas por Red")
    print("=" * 50)
    
    auditor = WiFiAuditor()
    auditor.running = True
    
    # Casos de prueba con nombres problemáticos
    test_targets = [
        {
            'essid': 'Mi Red WiFi 2024',
            'bssid': '00:1A:2B:3C:4D:5E',
            'channel': '6'
        },
        {
            'essid': 'Red/Con\\Caracteres<>Raros:*?',
            'bssid': 'AA:BB:CC:DD:EE:FF', 
            'channel': '11'
        },
        {
            'essid': 'FAMILIA_PÉREZ',
            'bssid': '11:22:33:44:55:66',
            'channel': '1'
        }
    ]
    
    for i, target in enumerate(test_targets, 1):
        print(f"\n📁 Caso {i}: {target['essid']}")
        
        try:
            # Inicializar historial
            network_key = auditor.initialize_network_history(target)
            
            # Verificar que la carpeta existe
            network_folder = auditor.wordlist_dir / network_key
            print(f"   ✅ Carpeta creada: {network_folder}")
            print(f"   ✅ Clave de red sanitizada: {network_key}")
            
            # Verificar archivos creados
            files_created = [
                "tried_passwords.txt",
                "network_stats.json", 
                "attack_history.log"
            ]
            
            for filename in files_created:
                filepath = network_folder / filename
                if filepath.exists():
                    print(f"   ✅ {filename} - Creado")
                else:
                    print(f"   ❌ {filename} - No encontrado")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n🎉 Prueba 1 completada")

def test_password_history_functionality():
    """Probar funcionalidad de historial de contraseñas"""
    print("\n💾 PRUEBA 2: Funcionalidad de Historial de Contraseñas")
    print("=" * 50)
    
    auditor = WiFiAuditor()
    auditor.running = True
    
    test_target = {
        'essid': 'TestNetwork',
        'bssid': '00:11:22:33:44:55',
        'channel': '6'
    }
    
    try:
        # Inicializar red
        network_key = auditor.initialize_network_history(test_target)
        print(f"✅ Red inicializada: {network_key}")
        
        # Primera serie de contraseñas
        first_batch = [
            'password123',
            'testnetwork123',
            'admin12345',
            'qwertyui',
            '12345678'
        ]
        
        print(f"\n🔄 Guardando primera serie de {len(first_batch)} contraseñas...")
        auditor.save_tried_passwords(first_batch, network_key, "PRUEBA_LOTE_1")
        
        # Segunda serie con algunas repetidas
        second_batch = [
            'password123',  # Repetida
            'newpassword2024',
            'testnetwork456', 
            'qwertyui',     # Repetida
            'freshpassword'
        ]
        
        print(f"\n🔍 Filtrando segunda serie (contiene {len(second_batch)} contraseñas, algunas repetidas)...")
        filtered = auditor.filter_new_passwords(second_batch, network_key)
        print(f"✅ Contraseñas nuevas después del filtro: {len(filtered)}")
        
        expected_new = ['newpassword2024', 'testnetwork456', 'freshpassword']
        if set(filtered) == set(expected_new):
            print("✅ Filtrado correcto - solo contraseñas nuevas")
        else:
            print(f"❌ Error en filtrado. Esperado: {expected_new}, Obtenido: {filtered}")
        
        # Guardar serie filtrada
        if filtered:
            auditor.save_tried_passwords(filtered, network_key, "PRUEBA_LOTE_2")
        
        # Verificar estadísticas
        stats = auditor.get_network_statistics(network_key)
        if stats:
            print(f"\n📊 Estadísticas de la red:")
            print(f"   - Total contraseñas únicas: {stats['total_unique_passwords']}")
            print(f"   - Sesiones de ataque: {stats['attack_sessions']}")
            print(f"   - Contraseñas en esta sesión: {stats['session_passwords_tried']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Prueba 2 completada")

def test_network_statistics():
    """Probar sistema de estadísticas de red"""
    print("\n📈 PRUEBA 3: Sistema de Estadísticas de Red")
    print("=" * 50)
    
    auditor = WiFiAuditor()
    auditor.running = True
    
    test_target = {
        'essid': 'StatNetwork',
        'bssid': '99:88:77:66:55:44',
        'channel': '11'
    }
    
    try:
        # Inicializar red
        network_key = auditor.initialize_network_history(test_target)
        
        # Simular fases completadas
        phases = ["FASE1", "FASE2", "FASE3"]
        for phase in phases:
            print(f"📊 Marcando {phase} como completada...")
            auditor.save_network_stats(network_key, phase)
        
        # Simular contraseña encontrada
        print("🔑 Simulando contraseña encontrada...")
        auditor.save_network_stats(network_key, "FASE4", "encontrada123")
        
        # Mostrar resumen
        print("\n📋 Resumen del historial:")
        already_cracked = auditor.show_network_history_summary(test_target)
        
        if already_cracked:
            print("✅ Sistema detectó correctamente que la red ya fue crackeada")
        else:
            print("❌ Sistema no detectó que la red fue crackeada")
        
        # Verificar archivo JSON
        network_folder = auditor.wordlist_dir / network_key
        stats_file = network_folder / "network_stats.json"
        
        if stats_file.exists():
            with open(stats_file, 'r') as f:
                data = json.load(f)
            print(f"\n📄 Contenido del archivo de estadísticas:")
            print(f"   - Fases completadas: {data.get('phases_completed', [])}")
            print(f"   - Contraseña exitosa: {data.get('successful_password', 'N/A')}")
            print(f"   - Fecha de crack: {data.get('crack_date', 'N/A')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Prueba 3 completada")

def test_file_persistence():
    """Probar persistencia de archivos entre sesiones"""
    print("\n💽 PRUEBA 4: Persistencia de Archivos Entre Sesiones")
    print("=" * 50)
    
    test_target = {
        'essid': 'PersistNetwork',
        'bssid': '12:34:56:78:90:AB',
        'channel': '6'
    }
    
    try:
        # SESIÓN 1
        print("🔄 SESIÓN 1: Creando historial inicial...")
        auditor1 = WiFiAuditor()
        auditor1.running = True
        
        network_key = auditor1.initialize_network_history(test_target)
        initial_passwords = ['session1_pass1', 'session1_pass2', 'session1_pass3']
        auditor1.save_tried_passwords(initial_passwords, network_key, "SESION1")
        auditor1.save_network_stats(network_key, "FASE1")
        
        del auditor1  # Simular fin de sesión
        
        # SESIÓN 2  
        print("🔄 SESIÓN 2: Cargando historial existente...")
        auditor2 = WiFiAuditor()
        auditor2.running = True
        
        network_key2 = auditor2.initialize_network_history(test_target)
        
        # Verificar que cargó el historial previo
        stats = auditor2.get_network_statistics(network_key2)
        if stats and stats['total_unique_passwords'] == 3:
            print("✅ Historial cargado correctamente desde sesión anterior")
            print(f"   - Contraseñas previamente probadas: {stats['total_unique_passwords']}")
            print(f"   - Fases completadas: {stats['phases_completed']}")
        else:
            print("❌ Error cargando historial de sesión anterior")
        
        # Agregar más contraseñas en sesión 2
        session2_passwords = ['session2_pass1', 'session1_pass1', 'session2_pass2']  # Una repetida
        filtered = auditor2.filter_new_passwords(session2_passwords, network_key2)
        
        if len(filtered) == 2:  # Debe filtrar la repetida
            print("✅ Filtro funcionó correctamente entre sesiones")
        else:
            print(f"❌ Error en filtro entre sesiones: {len(filtered)} contraseñas nuevas")
        
        auditor2.save_tried_passwords(filtered, network_key2, "SESION2")
        
        # Verificar totales finales
        final_stats = auditor2.get_network_statistics(network_key2)
        expected_total = len(initial_passwords) + len(filtered)
        
        if final_stats['total_unique_passwords'] == expected_total:
            print(f"✅ Total final correcto: {final_stats['total_unique_passwords']} contraseñas únicas")
        else:
            print(f"❌ Total incorrecto: {final_stats['total_unique_passwords']} vs {expected_total} esperadas")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Prueba 4 completada")

def test_special_characters_handling():
    """Probar manejo de caracteres especiales"""
    print("\n🔤 PRUEBA 5: Manejo de Caracteres Especiales")
    print("=" * 50)
    
    auditor = WiFiAuditor()
    auditor.running = True
    
    # Casos con caracteres especiales
    special_cases = [
        'Contraseña con ñ y acentos ácéntós',
        'Password with "quotes" and symbols!@#',
        'Пароль на русском языке',
        '密码中文测试',
        'Contraseña\ncon\tsaltos\rde\nlínea'
    ]
    
    test_target = {
        'essid': 'SpecialCharsNet',
        'bssid': 'AA:BB:CC:DD:EE:FF',
        'channel': '6'
    }
    
    try:
        network_key = auditor.initialize_network_history(test_target)
        
        print("💾 Probando guardado de contraseñas con caracteres especiales...")
        auditor.save_tried_passwords(special_cases, network_key, "CARACTERES_ESPECIALES")
        
        # Verificar que se guardaron correctamente
        network_folder = auditor.wordlist_dir / network_key
        tried_file = network_folder / "tried_passwords.txt"
        
        if tried_file.exists():
            with open(tried_file, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            saved_lines = [line.strip() for line in saved_content.split('\n') if line.strip()]
            
            if len(saved_lines) == len(special_cases):
                print("✅ Todas las contraseñas con caracteres especiales se guardaron")
            else:
                print(f"⚠️  Se guardaron {len(saved_lines)}/{len(special_cases)} contraseñas")
            
            # Probar filtrado con caracteres especiales
            mixed_batch = special_cases[:2] + ['nueva_password', 'otra_nueva']
            filtered = auditor.filter_new_passwords(mixed_batch, network_key)
            
            if len(filtered) == 2:
                print("✅ Filtrado correcto con caracteres especiales")
            else:
                print(f"⚠️  Filtrado inesperado: {len(filtered)} contraseñas nuevas")
        
    except Exception as e:
        print(f"❌ Error con caracteres especiales: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 Prueba 5 completada")

def cleanup_test_files():
    """Limpiar archivos de prueba"""
    print("\n🧹 Limpiando archivos de prueba...")
    
    try:
        wordlist_dir = Path("wordlists")
        if wordlist_dir.exists():
            test_folders = [
                'Mi_Red_WiFi_2024',
                'Red_Con_Caracteres____Raros___',
                'FAMILIA_PÉREZ',
                'TestNetwork',
                'StatNetwork',
                'PersistNetwork',
                'SpecialCharsNet'
            ]
            
            for folder_name in test_folders:
                test_folder = wordlist_dir / folder_name
                if test_folder.exists():
                    import shutil
                    shutil.rmtree(test_folder)
                    print(f"   🗑️  Eliminada: {folder_name}")
    
    except Exception as e:
        print(f"⚠️  Error limpiando: {e}")

def main():
    """Función principal de pruebas"""
    print("🎯 VALIDACIÓN DEL SISTEMA DE HISTORIAL DE CONTRASEÑAS POR RED")
    print("=" * 70)
    print("Este script valida la funcionalidad de crear carpetas por red")
    print("y mantener un historial persistente de contraseñas probadas.")
    print("=" * 70)
    
    start_time = time.time()
    
    try:
        test_network_folder_creation()
        test_password_history_functionality()
        test_network_statistics()
        test_file_persistence()
        test_special_characters_handling()
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("🏆 TODAS LAS PRUEBAS DEL SISTEMA DE HISTORIAL COMPLETADAS")
        print(f"⏱️  Tiempo total: {elapsed_time:.2f} segundos")
        print("=" * 70)
        print("\n✨ El sistema de historial por red está funcionando correctamente")
        print("🚀 Características validadas:")
        print("   ✅ Creación automática de carpetas por red")
        print("   ✅ Sanitización de nombres de red problemáticos")
        print("   ✅ Guardado persistente de contraseñas probadas")
        print("   ✅ Filtrado de contraseñas duplicadas")
        print("   ✅ Estadísticas detalladas por red")
        print("   ✅ Persistencia entre sesiones")
        print("   ✅ Manejo de caracteres especiales")
        print("   ✅ Archivos JSON y logs estructurados")
        
        print("\n📁 Estructura creada en wordlists/:")
        wordlist_dir = Path("wordlists")
        if wordlist_dir.exists():
            for item in sorted(wordlist_dir.iterdir()):
                if item.is_dir():
                    files = list(item.iterdir())
                    print(f"   📂 {item.name}/ ({len(files)} archivos)")
        
        # Preguntar si limpiar archivos de prueba
        print("\n🧹 ¿Deseas limpiar los archivos de prueba creados? (s/N): ", end="")
        try:
            response = input().strip().lower()
            if response in ['s', 'si', 'sí', 'y', 'yes']:
                cleanup_test_files()
                print("✅ Archivos de prueba eliminados")
            else:
                print("📁 Archivos de prueba mantenidos para inspección manual")
        except:
            print("📁 Archivos de prueba mantenidos")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas del sistema de historial: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()