# ==============================================================================
# GHOST v3 — Workstation Container (Container B)
# ==============================================================================
# PURPOSE:  The secure "Operating Room." A full Kali Linux workspace with a
#           headless XFCE desktop streamed via noVNC to the user's browser.
#
# NETWORK:  Lives on the isolated ghost_net (10.0.0.3). Has NO direct internet
#           access. All traffic is routed through the Gateway (10.0.0.2) which
#           transparently proxies it through Tor.
#
# ACCESS:   User connects via browser at http://localhost:8080 to interact
#           with the full Kali desktop environment.
# ==============================================================================

FROM kalilinux/kali-rolling

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------------------------------
# LAYER 1: Core System Dependencies
# --------------------------------------------------------------------------
# iproute2      — Provides `ip` command for route manipulation (kill-switch)
# net-tools     — Provides `ifconfig`, `netstat` for network diagnostics
# apt-utils     — Cleaner apt output and dpkg trigger handling
# iptables      — Firewall rules (backup leak prevention)
# curl, wget    — Basic HTTP utilities for verification
# bash          — Ensure bash is the default shell
# procps        — Provides `ps`, `top` for process management
# --------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    net-tools \
    apt-utils \
    iptables \
    curl \
    wget \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# LAYER 2: Headless GUI Stack
# --------------------------------------------------------------------------
# xvfb          — X Virtual Framebuffer: creates a fake display in memory
# x11vnc        — VNC server that attaches to the Xvfb display
# novnc         — HTML5 VNC client (streams desktop to a web browser)
# websockify    — WebSocket-to-TCP bridge (noVNC's transport layer)
# xfce4         — Lightweight desktop environment
# xfce4-terminal— Terminal emulator for the XFCE desktop
# dbus-x11      — D-Bus session bus (required by XFCE to start cleanly)
# --------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    xfce4 \
    xfce4-terminal \
    dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# LAYER 3: Filesystem & Environment Setup
# --------------------------------------------------------------------------
# Create the mount point for user files (passwords.txt, wordlists, etc.)
# Docker volumes from .env (MOUNT_PATH) will be mapped here at runtime.
# --------------------------------------------------------------------------
RUN mkdir -p /root/ghost_files

# Set the working directory for interactive sessions
WORKDIR /root

# --------------------------------------------------------------------------
# LAYER 4: Entrypoint Script
# --------------------------------------------------------------------------
# Copy the boot logic script that handles:
#   1. Dynamic tool installation from $KALI_METAPACKAGES
#   2. Network route manipulation (the "routing handcuffs")
#   3. Headless GUI stack startup (Xvfb -> XFCE -> VNC -> noVNC)
# --------------------------------------------------------------------------
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# --------------------------------------------------------------------------
# LAYER 5: Network Configuration
# --------------------------------------------------------------------------
# Expose the noVNC web interface port.
# The user will access the full Kali desktop at http://localhost:8080
# --------------------------------------------------------------------------
EXPOSE 8080

# --------------------------------------------------------------------------
# BOOT
# --------------------------------------------------------------------------
ENTRYPOINT ["/entrypoint.sh"]
