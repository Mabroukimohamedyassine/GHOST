#!/usr/bin/env python3
"""
GhostConnect - Automated Anonymous Browsing Kill Switch
A robust CLI tool for creating a secure, anonymous browsing environment using LibreWolf + Tor
Version 2.1.1 - Enhanced network robustness (IPv4 forcing + retry logic for flaky connections)
"""

import os
import sys
import subprocess
import signal
import time
import socket
import shutil
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback to colorama
    try:
        from colorama import init, Fore, Style
        init(autoreset=True)
    except ImportError:
        # Define dummy constants if colorama not available
        class Fore:
            GREEN = RED = YELLOW = CYAN = MAGENTA = ""
        class Style:
            BRIGHT = RESET_ALL = ""


class GhostConnector:
    """Main class for managing anonymous browsing environment"""

    # ASCII Art Banner
    BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ░██████╗░██╗░░██╗░█████╗░░██████╗████████╗                ║
║   ██╔════╝░██║░░██║██╔══██╗██╔════╝╚══██╔══╝                ║
║   ██║░░██╗░███████║██║░░██║╚█████╗░░░░██║░░░                ║
║   ██║░░╚██╗██╔══██║██║░░██║░╚═══██╗░░░██║░░░                ║
║   ╚██████╔╝██║░░██║╚█████╔╝██████╔╝░░░██║░░░                ║
║   ░╚═════╝░╚═╝░░╚═╝░╚════╝░╚═════╝░░░░╚═╝░░░                ║
║                                                               ║
║              ░█████╗░░█████╗░███╗░░██╗███╗░░██╗             ║
║              ██╔══██╗██╔══██╗████╗░██║████╗░██║             ║
║              ██║░░╚═╝██║░░██║██╔██╗██║██╔██╗██║             ║
║              ██║░░██╗██║░░██║██║╚████║██║╚████║             ║
║              ╚█████╔╝╚█████╔╝██║░╚███║██║░╚███║             ║
║              ░╚════╝░░╚════╝░╚═╝░░╚══╝╚═╝░░╚══╝             ║
║                                                               ║
║          Anonymous Browsing Kill Switch v2.1.1               ║
║            Powered by LibreWolf + Tor + extrepo              ║
╚═══════════════════════════════════════════════════════════════╝
    """

    def __init__(self):
        """Initialize GhostConnector with necessary paths and state"""
        self.tor_process = None
        self.proxychains_config = Path("/etc/proxychains4.conf")
        self.proxychains_backup = Path("/etc/proxychains4.conf.ghost.bak")
        self.sudo_user = os.environ.get('SUDO_USER', 'root')
        self.sudo_uid = os.environ.get('SUDO_UID')
        self.sudo_gid = os.environ.get('SUDO_GID')

        if RICH_AVAILABLE:
            self.console = Console()
        else:
            self.console = None

        # Register signal handlers for clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle CTRL+C and termination signals"""
        self._print("\n[!] Signal received. Initiating shutdown...", "warning")
        self.cleanup()
        sys.exit(0)

    def _print(self, message: str, msg_type: str = "info"):
        """Print formatted messages"""
        if RICH_AVAILABLE and self.console:
            if msg_type == "success":
                self.console.print(f"[green][✓][/green] {message}")
            elif msg_type == "error":
                self.console.print(f"[red][✗][/red] {message}")
            elif msg_type == "warning":
                self.console.print(f"[yellow][!][/yellow] {message}")
            elif msg_type == "info":
                self.console.print(f"[cyan][*][/cyan] {message}")
            else:
                self.console.print(message)
        else:
            # Fallback to colorama or plain text
            if msg_type == "success":
                print(f"{Fore.GREEN}[✓] {message}{Style.RESET_ALL}")
            elif msg_type == "error":
                print(f"{Fore.RED}[✗] {message}{Style.RESET_ALL}")
            elif msg_type == "warning":
                print(f"{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")
            elif msg_type == "info":
                print(f"{Fore.CYAN}[*] {message}{Style.RESET_ALL}")
            else:
                print(message)

    def _run_command(self, command: list, check: bool = True, capture: bool = False) -> Optional[subprocess.CompletedProcess]:
        """Execute system command"""
        try:
            if capture:
                result = subprocess.run(
                    command,
                    check=check,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                return result
            else:
                result = subprocess.run(command, check=check)
                return result
        except subprocess.CalledProcessError as e:
            self._print(f"Command failed: {' '.join(command)}", "error")
            if capture and e.stderr:
                self._print(f"Error: {e.stderr}", "error")
            return None
        except FileNotFoundError:
            self._print(f"Command not found: {command[0]}", "error")
            return None

    def show_banner(self):
        """Display ASCII art banner"""
        if RICH_AVAILABLE and self.console:
            self.console.print(self.BANNER, style="bold green")
        else:
            print(f"{Fore.GREEN}{Style.BRIGHT}{self.BANNER}{Style.RESET_ALL}")

    def check_root(self) -> bool:
        """Ensure script is running with root privileges"""
        if os.geteuid() != 0:
            self._print("This tool requires root privileges!", "error")
            self._print("Please run with: sudo python3 ghostconnect.py", "warning")
            return False
        self._print("Root privileges confirmed", "success")
        return True

    def check_dependencies(self) -> bool:
        """Check and install required dependencies"""
        self._print("Checking dependencies...", "info")

        # Check standard dependencies
        standard_deps = {
            "tor": "tor",
            "proxychains4": "proxychains4"
        }

        missing_deps = []

        for cmd, package in standard_deps.items():
            result = self._run_command(["which", cmd], check=False, capture=True)
            if not result or result.returncode != 0:
                missing_deps.append(package)
                self._print(f"{cmd} not found", "warning")
            else:
                self._print(f"{cmd} found: {result.stdout.strip()}", "success")

        # Check for LibreWolf
        librewolf_result = self._run_command(["which", "librewolf"], check=False, capture=True)
        librewolf_missing = not librewolf_result or librewolf_result.returncode != 0

        if librewolf_missing:
            self._print("librewolf not found", "warning")
        else:
            self._print(f"librewolf found: {librewolf_result.stdout.strip()}", "success")

        # Install standard dependencies if missing
        if missing_deps:
            self._print(f"Missing dependencies: {', '.join(missing_deps)}", "warning")
            self._print("Installing missing dependencies...", "info")

            # Update package list (force IPv4)
            self._print("Updating package list...", "info")
            if not self._run_command(["apt", "-o", "Acquire::ForceIPv4=true", "update"], check=False):
                self._print("Failed to update package list", "error")
                return False

            # Install missing packages (force IPv4)
            for package in missing_deps:
                self._print(f"Installing {package}...", "info")
                if not self._run_command(["apt", "-o", "Acquire::ForceIPv4=true", "install", "-y", package], check=False):
                    self._print(f"Failed to install {package}", "error")
                    return False
                self._print(f"{package} installed successfully", "success")

        # Handle LibreWolf installation separately
        if librewolf_missing:
            if not self._install_librewolf():
                self._print("Failed to install LibreWolf", "error")
                return False

        if not missing_deps and not librewolf_missing:
            self._print("All dependencies satisfied", "success")

        return True

    def _install_librewolf(self) -> bool:
        """Install LibreWolf browser using extrepo (universal method)"""
        self._print("Installing LibreWolf using extrepo...", "info")

        try:
            # Step 1: Clean up old/broken repository files
            self._print("Cleaning up old LibreWolf configuration files...", "info")

            old_sources = Path("/etc/apt/sources.list.d/librewolf.list")
            old_keyring = Path("/usr/share/keyrings/librewolf.gpg")

            if old_sources.exists():
                try:
                    old_sources.unlink()
                    self._print("Removed old repository file", "success")
                except Exception as e:
                    self._print(f"Warning: Could not remove old repo file: {str(e)}", "warning")

            if old_keyring.exists():
                try:
                    old_keyring.unlink()
                    self._print("Removed old GPG keyring", "success")
                except Exception as e:
                    self._print(f"Warning: Could not remove old keyring: {str(e)}", "warning")

            # Step 2: Install extrepo
            self._print("Installing extrepo package manager...", "info")

            # Update package list first (force IPv4)
            if not self._run_command(["apt", "-o", "Acquire::ForceIPv4=true", "update"], check=False):
                self._print("Failed to update package list", "error")
                return False

            # Install extrepo (force IPv4)
            if not self._run_command(["apt", "-o", "Acquire::ForceIPv4=true", "install", "-y", "extrepo"], check=False):
                self._print("Failed to install extrepo", "error")
                return False

            self._print("extrepo installed successfully", "success")

            # Step 3: Enable LibreWolf repository via extrepo
            self._print("Enabling LibreWolf repository via extrepo...", "info")

            if not self._run_command(["extrepo", "enable", "librewolf"], check=False):
                self._print("Failed to enable LibreWolf via extrepo", "error")
                return False

            self._print("LibreWolf repository enabled successfully", "success")

            # Step 4: Update package list with new repository (force IPv4)
            self._print("Updating package list with LibreWolf repository...", "info")

            if not self._run_command(["apt", "-o", "Acquire::ForceIPv4=true", "update"], check=False):
                self._print("Failed to update package list", "error")
                return False

            # Step 5: Install LibreWolf with retry loop (force IPv4)
            self._print("Installing LibreWolf package...", "info")

            max_retries = 3
            retry_count = 0
            install_success = False

            while retry_count < max_retries and not install_success:
                if retry_count > 0:
                    self._print(f"Retry attempt {retry_count}/{max_retries}...", "warning")
                    time.sleep(2)  # Wait 2 seconds between retries

                result = self._run_command([
                    "apt",
                    "-o", "Acquire::ForceIPv4=true",
                    "install",
                    "-y",
                    "librewolf"
                ], check=False)

                if result and result.returncode == 0:
                    install_success = True
                    break

                retry_count += 1
                if retry_count < max_retries:
                    self._print(f"Installation failed, retrying... ({retry_count}/{max_retries})", "warning")

            if not install_success:
                self._print("Failed to install LibreWolf after multiple attempts", "error")
                self._print("Network issue or repository temporarily unavailable", "warning")
                return False

            # Step 6: Verify installation
            verify = self._run_command(["which", "librewolf"], check=False, capture=True)
            if verify and verify.returncode == 0:
                self._print(f"LibreWolf installed successfully: {verify.stdout.strip()}", "success")
                return True
            else:
                self._print("LibreWolf installation verification failed", "error")
                return False

        except Exception as e:
            self._print(f"Error during LibreWolf installation: {str(e)}", "error")
            return False

    def configure_proxychains(self) -> bool:
        """Configure ProxyChains for Tor"""
        self._print("Configuring ProxyChains...", "info")

        try:
            # Backup original config if not already backed up
            if self.proxychains_config.exists() and not self.proxychains_backup.exists():
                shutil.copy(self.proxychains_config, self.proxychains_backup)
                self._print(f"Backed up original config to {self.proxychains_backup}", "success")

            # Create optimal ProxyChains configuration
            config_content = """# GhostConnect ProxyChains Configuration
# Strict chain - All proxies must be online
strict_chain

# Proxy DNS requests - prevent DNS leak
proxy_dns

# TCP read/write timeout in milliseconds
tcp_read_time_out 15000
tcp_connect_time_out 8000

# SOCKS5 proxy list
[ProxyList]
socks5 127.0.0.1 9050
"""

            self.proxychains_config.write_text(config_content)
            self._print("ProxyChains configured successfully", "success")
            return True

        except Exception as e:
            self._print(f"Failed to configure ProxyChains: {str(e)}", "error")
            return False

    def start_tor_service(self) -> bool:
        """Start Tor service"""
        self._print("Starting Tor service...", "info")

        # First, stop any existing Tor service
        self._run_command(["service", "tor", "stop"], check=False)
        time.sleep(1)

        # Start Tor
        result = self._run_command(["service", "tor", "start"], check=False)

        if result and result.returncode == 0:
            self._print("Tor service started", "success")
            return True
        else:
            self._print("Failed to start Tor service", "error")
            return False

    def wait_for_tor_bootstrap(self, timeout: int = 60) -> bool:
        """Wait for Tor to bootstrap and be ready"""
        self._print("Waiting for Tor to establish circuits...", "info")

        start_time = time.time()

        if RICH_AVAILABLE and self.console:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Connecting to Tor network...", total=None)

                while time.time() - start_time < timeout:
                    if self._check_tor_port():
                        progress.stop()
                        self._print("Tor is ready!", "success")
                        return True
                    time.sleep(1)
        else:
            # Fallback without rich
            dots = 0
            while time.time() - start_time < timeout:
                if self._check_tor_port():
                    print()  # New line after dots
                    self._print("Tor is ready!", "success")
                    return True

                print(f"\rConnecting to Tor network{'.' * (dots % 4)}{' ' * (3 - (dots % 4))}", end='', flush=True)
                dots += 1
                time.sleep(1)
            print()  # New line after timeout

        self._print(f"Tor failed to bootstrap within {timeout} seconds", "error")
        return False

    def _check_tor_port(self) -> bool:
        """Check if Tor SOCKS port (9050) is listening"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', 9050))
                return result == 0
        except Exception:
            return False

    def launch_librewolf(self) -> bool:
        """Launch LibreWolf through ProxyChains in private mode"""
        self._print("Launching LibreWolf in Ghost Mode...", "info")

        try:
            # Prepare environment for running as SUDO_USER
            env = os.environ.copy()

            # Get user's home directory
            if self.sudo_user and self.sudo_user != 'root':
                home_dir = Path(f"/home/{self.sudo_user}")
                env['HOME'] = str(home_dir)
                env['USER'] = self.sudo_user

                # Set XDG runtime directory
                if self.sudo_uid:
                    env['XDG_RUNTIME_DIR'] = f"/run/user/{self.sudo_uid}"

                self._print(f"Running LibreWolf as user: {self.sudo_user}", "info")

            # Launch LibreWolf with ProxyChains
            # Use preexec_fn to drop privileges if we have SUDO_UID/GID
            preexec = None
            if self.sudo_uid and self.sudo_gid:
                uid = int(self.sudo_uid)
                gid = int(self.sudo_gid)

                def demote():
                    """Demote process to run as SUDO_USER"""
                    os.setgid(gid)
                    os.setuid(uid)

                preexec = demote

            # Launch command (don't save the process handle since we won't wait for it)
            subprocess.Popen([
                "proxychains4",
                "librewolf",
                "--private-window",
                "https://check.torproject.org"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            preexec_fn=preexec)

            self._print("LibreWolf launched successfully", "success")
            self._print("Ghost Mode Active - Anonymous browsing enabled", "success")
            self._print("LibreWolf will open to Tor Check page", "info")

            return True

        except Exception as e:
            self._print(f"Failed to launch LibreWolf: {str(e)}", "error")
            return False

    def cleanup(self):
        """Clean up resources and stop services"""
        self._print("Initiating Ghost Mode shutdown...", "warning")

        # Kill all LibreWolf processes
        try:
            self._print("Terminating all LibreWolf instances...", "info")
            self._run_command(["pkill", "-9", "librewolf"], check=False)
            self._print("LibreWolf terminated", "success")
        except Exception as e:
            self._print(f"Error terminating LibreWolf: {str(e)}", "warning")

        # Stop Tor service
        self._print("Stopping Tor service...", "info")
        result = self._run_command(["service", "tor", "stop"], check=False)
        if result and result.returncode == 0:
            self._print("Tor service stopped", "success")

        # Restore original ProxyChains config if backup exists
        if self.proxychains_backup.exists() and self.proxychains_config.exists():
            try:
                shutil.copy(self.proxychains_backup, self.proxychains_config)
                self._print("ProxyChains configuration restored", "success")
            except Exception as e:
                self._print(f"Failed to restore ProxyChains config: {str(e)}", "warning")

        self._print("Ghost Mode Deactivated. Connection Normalized.", "success")

    def run(self):
        """Main execution flow"""
        try:
            # Show banner
            self.show_banner()

            # Phase 1: Check & Fix
            self._print("\n=== Phase 1: System Check & Setup ===", "info")

            if not self.check_root():
                return False

            if not self.check_dependencies():
                self._print("Dependency installation failed", "error")
                return False

            if not self.configure_proxychains():
                self._print("ProxyChains configuration failed", "error")
                return False

            # Phase 2: Launch
            self._print("\n=== Phase 2: Activating Ghost Mode ===", "info")
            self._print("LibreWolf is pre-hardened - No manual configuration needed!", "success")

            if not self.start_tor_service():
                self._print("Tor service failed to start", "error")
                return False

            if not self.wait_for_tor_bootstrap():
                self._print("Tor bootstrap failed", "error")
                self.cleanup()
                return False

            # Launch LibreWolf
            self.launch_librewolf()

            # Keep running until CTRL+C
            self._print("\n=== Ghost Mode Running ===", "success")
            self._print("Press CTRL+C to stop Ghost Mode and cleanup", "info")
            self._print("Note: Closing LibreWolf will NOT stop Ghost Mode", "warning")

            # Wait indefinitely until signal handler is triggered
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                # This should be caught by signal handler, but just in case
                pass

            return True

        except Exception as e:
            self._print(f"Unexpected error: {str(e)}", "error")
            self.cleanup()
            return False


def main():
    """Entry point"""
    ghost = GhostConnector()
    success = ghost.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
