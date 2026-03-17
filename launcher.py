#!/usr/bin/env python3
"""
OpenClaw Trading System Launcher
Uruchamia wszystkie komponenty systemu jednocześnie.
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

# Kolory dla terminala
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

processes = []

def print_header():
    """Wyświetl nagłówek."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
    print("🦅 OpenClaw Trading System Launcher")
    print(f"{'='*60}{Colors.RESET}\n")

def print_status(component, status, message=""):
    """Wyświetl status komponentu."""
    status_color = Colors.GREEN if status == "OK" else Colors.YELLOW if status == "STARTING" else Colors.RED
    print(f"{status_color}[{status}]{Colors.RESET} {Colors.BOLD}{component}{Colors.RESET} {message}")

def signal_handler(sig, frame):
    """Obsługa Ctrl+C - zamknij wszystkie procesy."""
    print(f"\n\n{Colors.YELLOW}⚠️  Otrzymano sygnał zamknięcia...{Colors.RESET}")
    print(f"{Colors.YELLOW}Zamykam wszystkie komponenty...{Colors.RESET}\n")
    
    for name, proc in processes:
        try:
            print(f"  Zamykam {name}...")
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print(f"  {name} nie odpowiada, wymuszam zamknięcie...")
            proc.kill()
        except Exception as e:
            print(f"  Błąd przy zamykaniu {name}: {e}")
    
    print(f"\n{Colors.GREEN}✓ Wszystkie komponenty zamknięte{Colors.RESET}\n")
    sys.exit(0)

def start_component(name, command, cwd=None, env=None):
    """Uruchom komponent w tle."""
    try:
        print_status(name, "STARTING", f"Uruchamiam: {' '.join(command)}")
        
        # Użyj CREATE_NEW_PROCESS_GROUP na Windows dla lepszej kontroli
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation_flags
        )
        
        # Czekaj chwilę i sprawdź czy proces się uruchomił
        time.sleep(1)
        if proc.poll() is None:
            print_status(name, "OK", f"PID: {proc.pid}")
            processes.append((name, proc))
            return True
        else:
            stdout, stderr = proc.communicate()
            print_status(name, "FAILED", f"Proces zakończył się z kodem {proc.returncode}")
            if stderr:
                print(f"  Błąd: {stderr.decode('utf-8', errors='ignore')[:200]}")
            return False
    except Exception as e:
        print_status(name, "FAILED", f"Błąd: {e}")
        return False

def check_dependencies():
    """Sprawdź czy wymagane zależności są zainstalowane."""
    print(f"{Colors.BLUE}Sprawdzam zależności...{Colors.RESET}")
    
    # Sprawdź czy trading_system istnieje
    trading_system_path = Path(__file__).parent
    if not (trading_system_path / "main.py").exists():
        print_status("Trading System", "FAILED", "Nie znaleziono main.py")
        return False
    
    # Sprawdź czy dashboard istnieje
    dashboard_path = trading_system_path.parent / "dashboard"
    if not dashboard_path.exists():
        print(f"{Colors.YELLOW}⚠️  Dashboard nie znaleziony w {dashboard_path}{Colors.RESET}")
        print(f"{Colors.YELLOW}   Dashboard nie zostanie uruchomiony{Colors.RESET}")
    
    print_status("Dependencies", "OK", "Wszystkie wymagane pliki znalezione")
    return True

def main():
    """Główna funkcja launchera."""
    print_header()
    
    # Zarejestruj handler dla Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)
    
    # Sprawdź zależności
    if not check_dependencies():
        print(f"\n{Colors.RED}❌ Sprawdzanie zależności nie powiodło się{Colors.RESET}\n")
        sys.exit(1)
    
    print(f"\n{Colors.BLUE}Uruchamiam komponenty...{Colors.RESET}\n")
    
    # Ścieżki
    base_dir = Path(__file__).parent.parent
    trading_system_dir = Path(__file__).parent
    dashboard_dir = base_dir / "dashboard"
    
    # 1. Uruchom Trading System (główny silnik)
    success = start_component(
        "Trading System",
        [sys.executable, "-m", "trading_system.main"],
        cwd=base_dir
    )
    
    if not success:
        print(f"\n{Colors.RED}❌ Nie udało się uruchomić Trading System{Colors.RESET}")
        print(f"{Colors.YELLOW}Sprawdź logi w: {trading_system_dir / 'logs' / 'trading_system.log'}{Colors.RESET}\n")
        return
    
    time.sleep(2)  # Daj czas na inicjalizację
    
    # 2. Uruchom Dashboard (jeśli istnieje)
    if dashboard_dir.exists():
        dashboard_server = dashboard_dir / "server.py"
        if dashboard_server.exists():
            start_component(
                "Dashboard Server",
                [sys.executable, "-m", "dashboard.server"],
                cwd=base_dir
            )
        else:
            print(f"{Colors.YELLOW}⚠️  Dashboard server.py nie znaleziony{Colors.RESET}")
    
    # Podsumowanie
    print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}")
    print("✓ System uruchomiony pomyślnie!")
    print(f"{'='*60}{Colors.RESET}\n")
    
    print(f"{Colors.CYAN}Uruchomione komponenty:{Colors.RESET}")
    for name, proc in processes:
        print(f"  • {name} (PID: {proc.pid})")
    
    print(f"\n{Colors.CYAN}Dostęp:{Colors.RESET}")
    print(f"  • Dashboard: http://localhost:8000")
    print(f"  • Logi: {trading_system_dir / 'logs' / 'trading_system.log'}")
    
    print(f"\n{Colors.YELLOW}Naciśnij Ctrl+C aby zatrzymać wszystkie komponenty{Colors.RESET}\n")
    
    # Monitoruj procesy
    try:
        while True:
            time.sleep(5)
            
            # Sprawdź czy wszystkie procesy działają
            for name, proc in processes[:]:
                if proc.poll() is not None:
                    print(f"\n{Colors.RED}⚠️  {name} zakończył się nieoczekiwanie (kod: {proc.returncode}){Colors.RESET}")
                    processes.remove((name, proc))
            
            # Jeśli wszystkie procesy się zakończyły, wyjdź
            if not processes:
                print(f"\n{Colors.RED}❌ Wszystkie komponenty zakończyły działanie{Colors.RESET}\n")
                break
    
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
