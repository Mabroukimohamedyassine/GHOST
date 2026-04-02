#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GHOST-v3 — UI Manager (interface.py)                                        ║
║                                                                            ║
║  Purpose:                                                                  ║
║    Provides the rich terminal interface for GHOST-v3. Displays network     ║
║    status, Tor circuit paths, and live logs in a clean dashboard.          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import time
import logging
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich import box

# Provide a global console singleton
console = Console()

class RichLogHandler(logging.Handler):
    """
    A custom logging handler that feeds into a Rich layout panel.
    Intercepts standard python logs and renders them inside the UI block.
    """
    def __init__(self):
        super().__init__()
        self.logs = []
        self.max_lines = 10

    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        if len(self.logs) > self.max_lines:
            self.logs.pop(0)


class GhostUI:
    """Dashboard User Interface for GHOST-v3 using the `rich` library."""
    
    def __init__(self, tor_controller):
        self.tor_controller = tor_controller
        self.log_handler = RichLogHandler()
        
        # Format logs as strictly messages with their level tag
        self.log_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        
        # Attach the rich handler to the tor_controller logger explicitly
        # and the base ghost logger so we intercept all operational messages.
        logging.getLogger("ghost").addHandler(self.log_handler)

    def generate_header(self) -> Panel:
        """Generates the main ASCII banner with styling."""
        banner = """
   ____ _   _  ___  __  __ _____             _____ 
  / ___| | | |/ _ \\|  \\/  |_   _|   _       |___ / 
 | |  _| |_| | | | | |\\/| | | |   (_)        |_ \\ 
 | |_| |  _  | |_| | |  | | | |    _        ___) |
  \\____|_| |_|\\___/|_|  |_| |_|   (_)      |____/ 
        """
        return Panel(
            Align.center(Text(banner, style="bold cyan")),
            box=box.DOUBLE,
            title="[bold green]Containerized Pentesting Architecture[/bold green]",
            subtitle="[dim]Gateway -> Workstation -> Browser[/dim]"
        )

    def generate_network_status(self) -> Panel:
        """Generates the network status panel natively reading from Gateway."""
        is_connected = self.tor_controller._controller and self.tor_controller._controller.is_authenticated()
        
        status_text = Text()
        if is_connected:
            status_text.append("Gateway: ", style="bold white")
            status_text.append("ONLINE\n", style="bold green")
            version = self.tor_controller.get_tor_version() or "Unknown"
            status_text.append(f"Tor Version: {version}", style="dim")
        else:
            status_text.append("Gateway: ", style="bold white")
            status_text.append("OFFLINE\n", style="bold red")
            status_text.append("Waiting for Controller...", style="dim")

        return Panel(status_text, title="[NETWORK STATUS]", box=box.ROUNDED, border_style="cyan")

    def generate_circuit_path(self) -> Panel:
        """Generates the circuit path panel showing geography (e.g. DE -> JP)."""
        path = self.tor_controller.get_circuit_path()
        
        if not path:
            path_display = Text("N/A", style="dim")
        else:
            path_display = Text(path, style="bold magenta")

        return Panel(
            Align.center(path_display, vertical="middle"), 
            title="[CURRENT CIRCUIT PATH]", 
            box=box.ROUNDED, 
            border_style="magenta"
        )

    def generate_logs(self) -> Panel:
        """Generates the active rolling log panel."""
        # Add basic dimming to older logs, but let's keep it simple for now
        log_text = Text("\n".join(self.log_handler.logs))
        
        # Fallback if no logs are present yet
        if not self.log_handler.logs:
            log_text = Text("Awaiting events...", style="dim")
            
        return Panel(log_text, title="[LOG]", box=box.ROUNDED, border_style="yellow")

    def generate_layout(self) -> Layout:
        """Builds the main Rich layout framework for the TUI."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=9),
            Layout(name="body", size=5),
            Layout(name="logs", size=10)
        )
        layout["body"].split_row(
            Layout(name="status"),
            Layout(name="circuit")
        )

        layout["header"].update(self.generate_header())
        layout["status"].update(self.generate_network_status())
        layout["circuit"].update(self.generate_circuit_path())
        layout["logs"].update(self.generate_logs())

        return layout

    def render_transient_action(self, seconds: int = 4):
        """
        Renders the Live UI for a set amount of time. Used for CLI actions 
        like rotating the IP so the user can verify the change visually before
        control goes back to the prompt.
        """
        # Screen=False prints the UI in the terminal scrollback rather than hijacking the buffer.
        with Live(self.generate_layout(), refresh_per_second=2, screen=False) as live:
            # Loop for the designated duration to let circuit path polling reflect changes
            steps = seconds * 2
            for _ in range(steps):
                live.update(self.generate_layout())
                time.sleep(0.5)
