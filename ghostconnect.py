#!/usr/bin/env python3
"""
GhostConnect - Automated Anonymous Browsing Kill Switch
A robust CLI tool for creating a secure, anonymous browsing environment
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
║          Anonymous Browsing Kill Switch v1.0                 ║
║                  Cyber Ghost Protocol                        ║
╚═══════════════════════════════════════════════════════════════╝
    """

    def __init__(self):
        """Initialize GhostConnector with necessary paths and state"""
        self.tor_process = None
        self.firefox_process = None
        self.proxychains_config = Path("/etc/proxychains4.conf")
        self.proxychains_backup = Path("/etc/proxychains4.conf.ghost.bak")
        self.firefox_profile_name = "GhostProfile"
        self.firefox_profile_path: Optional[Path] = None

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

        dependencies = {
            "tor": "tor",
            "proxychains4": "proxychains4",
            "firefox": "firefox-esr"
        }

        missing_deps = []

        for cmd, package in dependencies.items():
            result = self._run_command(["which", cmd], check=False, capture=True)
            if not result or result.returncode != 0:
                missing_deps.append(package)
                self._print(f"{cmd} not found", "warning")
            else:
                self._print(f"{cmd} found: {result.stdout.strip()}", "success")

        if missing_deps:
            self._print(f"Missing dependencies: {', '.join(missing_deps)}", "warning")
            self._print("Installing missing dependencies...", "info")

            # Update package list
            self._print("Updating package list...", "info")
            if not self._run_command(["apt", "update"], check=False):
                self._print("Failed to update package list", "error")
                return False

            # Install missing packages
            for package in missing_deps:
                self._print(f"Installing {package}...", "info")
                if not self._run_command(["apt", "install", "-y", package], check=False):
                    self._print(f"Failed to install {package}", "error")
                    return False
                self._print(f"{package} installed successfully", "success")
        else:
            self._print("All dependencies satisfied", "success")

        return True

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

    def _get_firefox_profile_path(self) -> Optional[Path]:
        """Locate the Firefox profile directory for GhostProfile"""
        # Common Firefox profile locations
        profile_base_paths = [
            Path.home() / ".mozilla" / "firefox",
            Path("/root/.mozilla/firefox")
        ]

        for base_path in profile_base_paths:
            if not base_path.exists():
                continue

            profiles_ini = base_path / "profiles.ini"
            if profiles_ini.exists():
                # Parse profiles.ini to find GhostProfile
                content = profiles_ini.read_text()
                in_ghost_section = False

                for line in content.split('\n'):
                    line = line.strip()
                    if f'Name={self.firefox_profile_name}' in line or f'name={self.firefox_profile_name}' in line:
                        in_ghost_section = True
                    elif in_ghost_section and (line.startswith('Path=') or line.startswith('path=')):
                        profile_dir = line.split('=', 1)[1].strip()

                        # Check if path is relative or absolute
                        if line.lower().startswith('path=') and not profile_dir.startswith('/'):
                            profile_path = base_path / profile_dir
                        else:
                            profile_path = Path(profile_dir)

                        if profile_path.exists():
                            return profile_path
                    elif line.startswith('[') and in_ghost_section:
                        # Moved to next section
                        break

        return None

    def create_firefox_profile(self) -> bool:
        """Create isolated Firefox profile with privacy settings"""
        self._print("Setting up Firefox GhostProfile...", "info")

        # Check if profile already exists
        self.firefox_profile_path = self._get_firefox_profile_path()

        if not self.firefox_profile_path:
            self._print(f"Creating new Firefox profile: {self.firefox_profile_name}", "info")

            # Create profile
            result = self._run_command([
                "firefox",
                "-CreateProfile",
                self.firefox_profile_name
            ], check=False, capture=True)

            if not result or result.returncode != 0:
                self._print("Failed to create Firefox profile", "error")
                return False

            # Wait a moment for profile creation
            time.sleep(1)

            # Get the newly created profile path
            self.firefox_profile_path = self._get_firefox_profile_path()

            if not self.firefox_profile_path:
                self._print("Profile created but could not locate directory", "error")
                return False

            self._print(f"Profile created at: {self.firefox_profile_path}", "success")
        else:
            self._print(f"Found existing GhostProfile at: {self.firefox_profile_path}", "success")

        # Inject privacy settings into user.js
        return self._inject_privacy_settings()

    def _inject_privacy_settings(self) -> bool:
        """Inject privacy settings into Firefox profile's user.js"""
        if not self.firefox_profile_path:
            self._print("Profile path not set", "error")
            return False

        user_js_path = self.firefox_profile_path / "user.js"

        self._print("Injecting privacy settings into user.js...", "info")

        # Comprehensive privacy settings
        privacy_settings = """// GhostConnect Privacy Configuration
// Disable WebRTC to prevent IP leaks
user_pref("media.peerconnection.enabled", false);
user_pref("media.peerconnection.ice.default_address_only", true);
user_pref("media.peerconnection.ice.no_host", true);
user_pref("media.peerconnection.ice.proxy_only_if_behind_proxy", true);

// Disable IPv6 to prevent leaks
user_pref("network.dns.disableIPv6", true);

// Set proxy type to Direct (ProxyChains handles routing externally)
user_pref("network.proxy.type", 0);

// Disable WebGL (fingerprinting)
user_pref("webgl.disabled", true);

// Disable geo-location
user_pref("geo.enabled", false);

// Disable telemetry
user_pref("toolkit.telemetry.enabled", false);
user_pref("toolkit.telemetry.unified", false);
user_pref("toolkit.telemetry.archive.enabled", false);

// Disable Firefox Studies
user_pref("app.shield.optoutstudies.enabled", false);

// Disable Pocket
user_pref("extensions.pocket.enabled", false);

// Disable DNS prefetching
user_pref("network.dns.disablePrefetch", true);
user_pref("network.dns.disablePrefetchFromHTTPS", true);

// Disable link prefetching
user_pref("network.prefetch-next", false);

// Disable predictor
user_pref("network.predictor.enabled", false);

// Disable search suggestions
user_pref("browser.search.suggest.enabled", false);
user_pref("browser.urlbar.suggest.searches", false);

// Clear on shutdown
user_pref("privacy.sanitize.sanitizeOnShutdown", true);
user_pref("privacy.clearOnShutdown.cache", true);
user_pref("privacy.clearOnShutdown.cookies", true);
user_pref("privacy.clearOnShutdown.offlineApps", true);

// Resist fingerprinting
user_pref("privacy.resistFingerprinting", true);

// First party isolation
user_pref("privacy.firstparty.isolate", true);

// Disable battery API
user_pref("dom.battery.enabled", false);

// Disable gamepad API
user_pref("dom.gamepad.enabled", false);

// Disable virtual reality devices
user_pref("dom.vr.enabled", false);

// GhostConnect Configuration Applied
"""

        try:
            user_js_path.write_text(privacy_settings)
            self._print(f"Privacy settings written to {user_js_path}", "success")
            return True
        except Exception as e:
            self._print(f"Failed to write user.js: {str(e)}", "error")
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

    def launch_firefox(self) -> bool:
        """Launch Firefox through ProxyChains with GhostProfile"""
        self._print("Launching Firefox in Ghost Mode...", "info")

        try:
            # Launch Firefox with ProxyChains
            self.firefox_process = subprocess.Popen([
                "proxychains4",
                "firefox",
                "-P", self.firefox_profile_name,
                "--no-remote"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            self._print("Firefox launched successfully", "success")
            self._print("Ghost Mode Active - Anonymous browsing enabled", "success")
            self._print("Press CTRL+C to deactivate Ghost Mode", "warning")

            # Wait for Firefox to exit
            self.firefox_process.wait()

            return True

        except Exception as e:
            self._print(f"Failed to launch Firefox: {str(e)}", "error")
            return False

    def cleanup(self):
        """Clean up resources and stop services"""
        self._print("Initiating Ghost Mode shutdown...", "warning")

        # Kill Firefox if running
        if self.firefox_process:
            try:
                self._print("Terminating Firefox...", "info")
                self.firefox_process.terminate()
                self.firefox_process.wait(timeout=5)
                self._print("Firefox terminated", "success")
            except subprocess.TimeoutExpired:
                self._print("Force killing Firefox...", "warning")
                self.firefox_process.kill()
            except Exception as e:
                self._print(f"Error terminating Firefox: {str(e)}", "error")

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

            if not self.create_firefox_profile():
                self._print("Firefox profile setup failed", "error")
                return False

            # Phase 2: Launch
            self._print("\n=== Phase 2: Activating Ghost Mode ===", "info")

            if not self.start_tor_service():
                self._print("Tor service failed to start", "error")
                return False

            if not self.wait_for_tor_bootstrap():
                self._print("Tor bootstrap failed", "error")
                self.cleanup()
                return False

            # Launch Firefox
            self.launch_firefox()

            # Phase 3: Cleanup (triggered by Firefox exit or CTRL+C)
            self._print("\n=== Phase 3: Cleanup ===", "info")
            self.cleanup()

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
