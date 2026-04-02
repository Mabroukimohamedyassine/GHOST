#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GHOST-v3 — The Circuit Manager (tor_controller.py)                          ║
║                                                                            ║
║  Purpose:                                                                  ║
║    Communicates with the Tor Gateway container's Control Port to query     ║
║    status, authenticate, and force IP rotation (circuit drops).            ║
║                                                                            ║
║  Requirements:                                                             ║
║    - Uses the 'stem' library.                                              ║
║    - Reads TOR_CONTROL_PORT from the environment (default 9051).           ║
║    - rotate_ip() method to send the NEWNYM signal.                         ║
║    - Robust error handling for connection and authentication failures.     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import logging
from typing import Optional

# ────────────────────────── Third-Party Imports ───────────────────────────
from stem import Signal
from stem.control import Controller
from stem.connection import AuthenticationFailure, MissingPassword
from stem.socket import SocketError

# Configure module-level logger matching the main orchestrator's format
logger = logging.getLogger("ghost.tor_controller")
logger.setLevel(logging.INFO)

# If no handlers exist (e.g., when run standalone), add a default stderr handler
if not logger.handlers:
    import sys
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s", 
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class TorController:
    """
    Manages the connection to the Tor daemon running in the Gateway container.
    Provides methods to authenticate and request new circuits (IP rotation).
    """

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None, password: Optional[str] = None) -> None:
        """
        Initializes the TorController.

        Args:
            host: The IP address where the Tor control port is accessible.
                  Defaults to localhost 127.0.0.1.
            port: The Tor control port. If None, it will try to read from the 
                  TOR_CONTROL_PORT environment variable (defaulting to 9051).
            password: Optional control port password. Usually, we rely on 
                      basic/cookie authentication if configured securely for 
                      local access only.
        """
        self.host = host
        
        # Determine the port from arguments or environment
        if port is not None:
            self.port = port
        else:
            try:
                self.port = int(os.environ.get("TOR_CONTROL_PORT", "9051"))
            except ValueError:
                logger.warning("TOR_CONTROL_PORT is invalid; defaulting to 9051.")
                self.port = 9051
                
        self.password = password
        self._controller: Optional[Controller] = None

    def connect_and_authenticate(self) -> bool:
        """
        Establishes a connection to the Tor Control Port and authenticates.

        Returns:
            bool: True if connection and authentication were successful, False otherwise.
        """
        logger.info(f"Connecting to Tor Control Port at {self.host}:{self.port}...")
        try:
            # Instantiate the Controller from the given host and port
            self._controller = Controller.from_port(address=self.host, port=self.port)
            
            # Attempt authentication
            if self.password:
                self._controller.authenticate(password=self.password)
            else:
                # This will attempt authentication with default parameters (often cookie or null)
                self._controller.authenticate()
                
            logger.info("Successfully connected and authenticated to the Tor Gateway.")
            return True

        except SocketError as se:
            logger.error(f"Connection timeout/socket error when connecting to {self.host}:{self.port} — {se}")
            self._cleanup_failed_connection()
            return False
            
        except MissingPassword:
            logger.error("Authentication failed: Tor control port requires a password, but none was provided.")
            self._cleanup_failed_connection()
            return False
            
        except AuthenticationFailure as af:
            logger.error(f"Authentication failed: {af}")
            self._cleanup_failed_connection()
            return False
            
        except Exception as e:
            logger.error(f"An unexpected error occurred during Tor connection: {e}")
            self._cleanup_failed_connection()
            return False

    def _cleanup_failed_connection(self) -> None:
        """Safely cleans up the controller object if a connection attempt fails."""
        if self._controller:
            try:
                self._controller.close()
            except Exception:
                pass
            self._controller = None

    def rotate_ip(self) -> bool:
        """
        Sends the NEWNYM signal to instantly drop the current Tor circuit
        and request a fresh exit node IP.

        Returns:
            bool: True if the signal was successfully sent, False otherwise.
        """
        if not self._controller or not self._controller.is_authenticated():
            logger.warning("Tor Controller is not connected. Attempting to connect now...")
            if not self.connect_and_authenticate():
                logger.error("Could not rotate IP: Tor control connection unavailable.")
                return False

        logger.info("Requesting new Tor circuit (NEWNYM)...")
        try:
            # Send the NEWNYM signal to drop the current exit nodes
            self._controller.signal(Signal.NEWNYM)
            logger.info("NEWNYM signal sent. A fresh Exit Node IP has been requested and will be used for new connections.")
            return True

        except SocketError as se:
            logger.error(f"Lost connection to Tor during IP rotation: {se}")
            self.disconnect()
            return False
            
        except Exception as e:
            logger.error(f"Failed to send NEWNYM signal: {e}")
            return False

    def get_tor_version(self) -> Optional[str]:
        """
        Fetches the version of the connected Tor daemon.
        Useful for health checking the connection.
        """
        if self._controller and self._controller.is_authenticated():
            try:
                return self._controller.get_version().version_str
            except Exception as e:
                logger.error(f"Could not retrieve Tor version: {e}")
                return None
        return None

    def get_circuit_path(self) -> Optional[str]:
        """
        Queries the current active Tor circuits and returns a formatted
        string showing the geographical path (e.g., 'DE -> FR -> JP').
        """
        if not self._controller or not self._controller.is_authenticated():
            return None

        try:
            for circ in self._controller.get_circuits():
                if circ.status == "BUILT" and circ.purpose == "GENERAL":
                    path_countries = []
                    for fingerprint, nickname in circ.path:
                        try:
                            # Get the router status entry to find its IP
                            desc = self._controller.get_network_status(fingerprint, default=None)
                            if desc and desc.address:
                                country_code = self._controller.get_info(f"ip-to-country/{desc.address}", default="??")
                                country = country_code.upper() if country_code != "??" else "Unknown"
                            else:
                                country = "Unknown"
                            
                            path_countries.append(country)
                        except Exception:
                            path_countries.append("Unknown")
                    
                    if path_countries:
                        return " → ".join(path_countries)
            
            return "Building circuit..."
        except Exception as e:
            logger.debug(f"Error fetching circuit path: {e}")
            return None

    def disconnect(self) -> None:
        """
        Cleanly closes the connection to the Tor Control Port.
        """
        if self._controller:
            logger.info("Closing connection to Tor Control Port.")
            try:
                self._controller.close()
            except Exception as e:
                logger.debug(f"Error while closing Tor controller: {e}")
            finally:
                self._controller = None


if __name__ == "__main__":
    # ── Example usage for ad-hoc testing ────────────────────────────────────
    import time
    
    manager = TorController()
    if manager.connect_and_authenticate():
        version = manager.get_tor_version()
        logger.info(f"Gateway Tor version: {version}")
        
        manager.rotate_ip()
        
        # In a real environment, you might hold the connection open
        # and wait for signals or keyboard interrupts.
        time.sleep(1)
        
        manager.disconnect()
    else:
        logger.error("Failed to initialize TorController test.")
        import sys
        sys.exit(1)
