"""
Sauberes Logging-System für die Simulation mit Fortschrittsanzeige.

Ziele:
- Klare, strukturierte Ausgabe der Simulationsschritte
- Start/Erfolg/Fehler für jeden Schritt
- Keine technischen Debug-Details (optional per verbose-Flag)
"""

from typing import Optional, List
import sys
from datetime import datetime


class SimulationLogger:
    """Logger für strukturierte Ausgabe der Simulationsschritte."""
    
    def __init__(self, verbose: bool = False):
        """
        Args:
            verbose: Wenn True, zeige ausführlichere Informationen
        """
        self.verbose = verbose
        self.steps: List[dict] = []
        self.current_step: Optional[dict] = None
    
    def start_step(self, step_name: str, details: Optional[str] = None):
        """Markiert den Start eines Simulationsschritts."""
        self.current_step = {
            "name": step_name,
            "details": details,
            "status": "in_progress",
            "start_time": datetime.now(),
        }
        
        output = f"▶ {step_name}"
        if details and self.verbose:
            output += f" ({details})"
        print(output)
        sys.stdout.flush()
    
    def finish_step(self, success: bool = True, message: Optional[str] = None):
        """Markiert den Abschluss des aktuellen Schritts."""
        if self.current_step is None:
            return
        
        self.current_step["status"] = "success" if success else "failed"
        self.current_step["message"] = message
        self.steps.append(self.current_step)
        
        status_icon = "✓" if success else "✗"
        output = f"  {status_icon}"
        if message:
            output += f" {message}"
        
        print(output)
        sys.stdout.flush()
        self.current_step = None
    
    def info(self, message: str):
        """Zeige eine Info-Nachricht an."""
        if self.verbose:
            print(f"  ℹ {message}")
            sys.stdout.flush()
    
    def warning(self, message: str):
        """Zeige eine Warnung an."""
        print(f"  ⚠ {message}")
        sys.stdout.flush()
    
    def error(self, message: str):
        """Zeige einen Fehler an."""
        print(f"  ✗ FEHLER: {message}", file=sys.stderr)
        sys.stdout.flush()
    
    def summary(self) -> str:
        """Gibt eine Zusammenfassung aller Schritte aus."""
        total = len(self.steps)
        successful = sum(1 for s in self.steps if s["status"] == "success")
        failed = total - successful
        
        summary = f"\n{'='*60}\n"
        summary += f"Simulation abgeschlossen: {successful}/{total} Schritte erfolgreich"
        if failed > 0:
            summary += f" ({failed} Fehler)"
        summary += f"\n{'='*60}"
        return summary
    
    def print_summary(self):
        """Drucke die Zusammenfassung."""
        print(self.summary())
