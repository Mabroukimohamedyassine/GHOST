# ==============================================================================
# GHOST v3 — Browser Container (Container C)
# ==============================================================================
# PURPOSE:  The isolated "Clean Room." A sandboxed environment running ONLY
#           the Tor Browser. If a malicious website exploits the browser, the
#           attacker is trapped in this minimal container with zero access to
#           the Workstation's pentest tools, the host filesystem, or the
#           Gateway's Tor control port.
#
# NETWORK:  Lives on the isolated ghost_net (10.0.0.4). All traffic is
#           routed exclusively through the Gateway (10.0.0.2), which
#           transparently proxies everything through Tor.
#
# ACCESS:   User connects via browser at http://localhost:8081 to interact
#           with the Tor Browser through a noVNC HTML5 web interface.
#
# SECURITY: The Tor Browser REFUSES to run as root. A dedicated non-root
#           user (ghost_browser) is created for all browser operations.
#           Supervisor manages process lifecycle with auto-restart.
# ==============================================================================

FROM debian:bullseye-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------------------------------
# LAYER 1: Core System Dependencies
# --------------------------------------------------------------------------
# iproute2      — Provides `ip` command for route manipulation (routing handcuffs)
# iptables      — Backup firewall rules for defense-in-depth
# curl          — HTTP client for downloading the Tor Browser Bundle
# xz-utils      — Decompresses the .tar.xz Tor Browser archive
# gnupg         — GPG for verifying the Tor Browser signature
# ca-certificates — Root CA certs for HTTPS downloads from torproject.org
# procps        — Provides `ps`, `top` for process debugging
# libdbus-glib-1-2 — Required runtime dependency for Tor Browser (Firefox/Gecko)
# libgtk-3-0    — GTK3 toolkit (Tor Browser GUI rendering)
# libx11-xcb1   — X11/XCB interop (required by Firefox-based browsers)
# libasound2    — ALSA sound library (Tor Browser expects it, even headless)
# libxt6        — X Toolkit Intrinsics (Firefox widget dependency)
# libpci3       — PCI bus access (hardware detection fallback)
# --------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iptables \
    curl \
    xz-utils \
    gnupg \
    ca-certificates \
    procps \
    libdbus-glib-1-2 \
    libgtk-3-0 \
    libx11-xcb1 \
    libasound2 \
    libxt6 \
    libpci3 \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# LAYER 2: Headless GUI Stack & Process Manager
# --------------------------------------------------------------------------
# xvfb          — X Virtual Framebuffer: creates a virtual display in memory
#                 (the "invisible monitor" the Tor Browser renders to)
# x11vnc        — VNC server that captures the Xvfb display and serves it
# novnc         — HTML5 VNC client (streams the desktop to a web browser)
# websockify    — WebSocket-to-TCP bridge (translates browser WebSocket
#                 connections to the raw VNC/RFB protocol on the backend)
# supervisor    — Process manager that keeps all 4 services alive and
#                 handles orderly startup, logging, and auto-restart
# --------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# LAYER 3: Security — Non-Root User Creation (CRITICAL)
# --------------------------------------------------------------------------
# The Tor Browser explicitly refuses to launch as root. This is a deliberate
# upstream security decision: running a browser as root means any exploit
# gains full container privileges immediately.
#
# We create a dedicated user 'ghost_browser' with:
#   - A real home directory (/home/ghost_browser) for Tor Browser files
#   - A login shell (/bin/bash) for debugging if needed
#   - No password and no sudo — minimal privilege
# --------------------------------------------------------------------------
RUN useradd -m -s /bin/bash -d /home/ghost_browser ghost_browser

# --------------------------------------------------------------------------
# LAYER 4: Tor Browser Bundle Installation
# --------------------------------------------------------------------------
# Strategy:
#   1. Download the latest Tor Browser for Linux (x86_64)
#   2. Download the corresponding GPG signature (.asc)
#   3. Import the Tor Browser Developers' signing key
#   4. Verify the archive signature to ensure integrity & authenticity
#   5. Extract to the ghost_browser user's home directory
#   6. Clean up downloaded artifacts to minimize image size
#
# The version is pinned via TBB_VERSION for reproducible builds.
# Update this variable to upgrade the Tor Browser.
# --------------------------------------------------------------------------
ENV TBB_VERSION="13.0.14"
ENV TBB_ARCH=linux-x86_64
ENV TBB_DIST="https://archive.torproject.org/tor-package-archive/torbrowser/${TBB_VERSION}"
ENV TBB_FILENAME=tor-browser-${TBB_ARCH}-${TBB_VERSION}.tar.xz

WORKDIR /tmp/tbb-install

# Step 4a: Download the Tor Browser archive and its GPG signature
RUN echo "Downloading Tor Browser Bundle v${TBB_VERSION}..." && \
    curl -fSL -o "${TBB_FILENAME}" \
    "${TBB_DIST}/${TBB_FILENAME}" && \
    curl -fSL -o "${TBB_FILENAME}.asc" \
    "${TBB_DIST}/${TBB_FILENAME}.asc"

# Step 4b: Import the Tor Browser Developers' GPG signing key and verify
# Key fingerprint: EF6E 286D DA85 EA2A 4BA7 DE68 4E2C 6E87 9329 8290
# This is the official key used to sign all Tor Browser releases.
# If verification fails, the build STOPS — we refuse to install untrusted binaries.
RUN echo "Importing Tor Browser Developers signing key..." && \
    gpg --auto-key-locate nodefault,wkd --locate-keys torbrowser@torproject.org || \
    gpg --keyserver keyserver.ubuntu.com \
    --recv-keys 0xEF6E286DDA85EA2A4BA7DE684E2C6E8793298290 && \
    echo "Verifying GPG signature..." && \
    gpg --verify "${TBB_FILENAME}.asc" "${TBB_FILENAME}" && \
    echo "✓ Signature verification PASSED."

# Step 4c: Extract to the ghost_browser user's home directory
# The archive extracts to a 'tor-browser/' directory containing the
# start-tor-browser launcher and the full Firefox profile.
RUN echo "Extracting Tor Browser to /home/ghost_browser/..." && \
    tar -xJf "${TBB_FILENAME}" -C /home/ghost_browser/ && \
    chown -R ghost_browser:ghost_browser /home/ghost_browser/tor-browser

# Step 4d: Cleanup downloaded artifacts to reduce final image size
RUN rm -rf /tmp/tbb-install

# --------------------------------------------------------------------------
# LAYER 5: Entrypoint Script — Routing Handcuffs + Supervisor Launch
# --------------------------------------------------------------------------
# This script runs as ROOT at container boot to:
#   1. Apply the routing handcuffs (force all traffic through Gateway)
#   2. Hand off to supervisord (which manages all services as appropriate users)
#
# The routing MUST happen before any network-aware process starts.
# If routing fails, the container halts — fail-closed by design.
# --------------------------------------------------------------------------
RUN cat <<'ENTRYPOINT_SCRIPT' > /entrypoint.sh
#!/bin/bash
# ==============================================================================
# GHOST v3 — Browser Container Entrypoint
# ==============================================================================
set -e

GATEWAY_IP="${GATEWAY_IP:-10.0.0.2}"

# --- Logging Helpers ---
log_info()    { echo -e "\033[0;36m[*] GHOST-BR:\033[0m $1"; }
log_success() { echo -e "\033[0;32m[✓] GHOST-BR:\033[0m $1"; }
log_warn()    { echo -e "\033[1;33m[!] GHOST-BR:\033[0m $1"; }
log_error()   { echo -e "\033[0;31m[✗] GHOST-BR:\033[0m $1"; }

# ==============================================================================
# PHASE 1: ROUTING HANDCUFFS (CRITICAL — FAIL-CLOSED)
# ==============================================================================
# Delete Docker's default gateway (potential leak path) and replace it with
# the Gateway container. If this fails, container MUST NOT continue.
# ==============================================================================
log_info "Applying routing handcuffs..."

if ip route del default 2>/dev/null; then
    log_success "Default gateway route removed."
else
    log_warn "No default route found (may already be clean)."
fi

if ip route add default via "$GATEWAY_IP" 2>/dev/null; then
    log_success "Default route set to Gateway ($GATEWAY_IP)."
else
    log_error "FATAL: Failed to set route to Gateway. Aborting for safety."
    log_error "Without this route, traffic could leak outside Tor."
    exit 1
fi

log_info "Current routing table:"
ip route show
log_success "Routing handcuffs applied. All traffic forced through $GATEWAY_IP."

# ==============================================================================
# PHASE 2: LAUNCH SUPERVISOR
# ==============================================================================
# Supervisor takes over PID 1 duties and manages: Xvfb, x11vnc, noVNC,
# and the Tor Browser. All process lifecycle is handled from here.
# ==============================================================================
log_info "Handing off to supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
ENTRYPOINT_SCRIPT

RUN chmod +x /entrypoint.sh

# --------------------------------------------------------------------------
# LAYER 6: Supervisor Configuration
# --------------------------------------------------------------------------
# Copy the supervisord.conf that defines all four managed processes.
# --------------------------------------------------------------------------
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# --------------------------------------------------------------------------
# LAYER 7: Network Configuration
# --------------------------------------------------------------------------
# Expose the noVNC web interface on port 8081.
# This is deliberately different from the Workstation's port 8080 to allow
# both containers to be accessed simultaneously without port conflicts.
# --------------------------------------------------------------------------
EXPOSE 8081

# --------------------------------------------------------------------------
# LAYER 8: Environment Variables for Runtime
# --------------------------------------------------------------------------
ENV DISPLAY=:1
ENV GATEWAY_IP=10.0.0.2

# --------------------------------------------------------------------------
# BOOT
# --------------------------------------------------------------------------
# The entrypoint script applies routing handcuffs, then exec's into
# supervisord which manages all child processes.
# --------------------------------------------------------------------------
ENTRYPOINT ["/entrypoint.sh"]
