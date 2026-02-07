# GhostConnect - Anonymous Browsing Kill Switch v2.1.0

A robust, automated CLI tool for creating a secure anonymous browsing environment on Kali Linux using Tor, ProxyChains, and **LibreWolf** (privacy-hardened Firefox fork).

## What's New in v2.1.0

### 🚀 Universal Installation Method
- **Complete rewrite using extrepo** - LibreWolf now installs universally on all Debian-based distributions
  - Works on Kali Linux, Debian, Ubuntu, and derivatives
  - No more distribution-specific workarounds needed
  - Managed repository configuration via `extrepo` tool
  - Automatic cleanup of old/broken configuration files
  - Simpler, more reliable installation process

### Why This Improvement?
Previous versions used manual repository setup that:
- Required distribution detection and codename mapping
- Broke when LibreWolf changed repository URLs
- Needed Kali-specific workarounds

**v2.1.0 uses `extrepo`** which:
- ✅ Works universally on all Debian-based distros
- ✅ No codename detection needed
- ✅ Self-updating repository information
- ✅ Managed by Debian package maintainers

## What's New in v2.0.1

### 🐛 Critical Bug Fix
- **Fixed Kali Linux installation** - Resolved 404 error when installing LibreWolf
  - Automatically maps `kali-rolling` to Debian `unstable` repository
  - Supports all Kali variants (kali-rolling, kali-dev, etc.)
  - Improved GPG key download with `wget --quiet`
  - Enhanced error messages and logging

*(Note: v2.1.0 supersedes this fix with universal extrepo method)*

## What's New in v2.0

- **Replaced Firefox with LibreWolf** - Pre-hardened browser with privacy by default
- **No Manual Configuration** - LibreWolf comes secure out of the box (WebRTC disabled, fingerprinting resistance, etc.)
- **Automated LibreWolf Installation** - Automatically adds repository and installs LibreWolf
- **Kali Linux Support** - Properly detects and maps Kali rolling to compatible Debian repository
- **Simplified Codebase** - Removed ~200 lines of manual Firefox hardening code
- **Better User Experience** - Runs as SUDO_USER to avoid permission issues

## Features

- **Automated Setup**: Checks and installs all dependencies (Tor, ProxyChains4, LibreWolf)
- **Intelligent Configuration**: Automatically configures ProxyChains for optimal security
- **LibreWolf Browser**: Privacy-hardened Firefox fork that's secure by default
- **DNS Leak Prevention**: Enforces DNS through Tor, disables IPv6 leaks
- **Bootstrap Detection**: Waits for Tor to establish circuits before launching browser
- **Clean Kill Switch**: CTRL+C cleanly terminates everything and normalizes connection
- **Professional UI**: Rich terminal interface with progress indicators and status messages

## Why LibreWolf?

LibreWolf is a Firefox fork with **built-in privacy hardening**:
- ✓ WebRTC disabled (prevents IP leaks)
- ✓ Telemetry removed
- ✓ Fingerprinting resistance enabled
- ✓ Auto-delete cookies on close
- ✓ No Google/Mozilla telemetry
- ✓ uBlock Origin included
- ✓ Private by default

This means **no manual configuration needed** - it works securely out of the box!

## Architecture

The tool follows a modular design with three main phases:

1. **Check & Fix Phase**: Verifies root privileges, installs dependencies (including LibreWolf repository setup), configures ProxyChains
2. **Launch Phase**: Starts Tor, waits for bootstrap, launches LibreWolf in private mode
3. **Cleanup Phase**: Terminates browser, stops Tor, restores configurations

## Prerequisites

- **Kali Linux** (or any Debian-based Linux distribution)
- **Python 3.7+**
- **Root/sudo privileges**

## Installation

1. Clone or download this tool:
```bash
cd /opt
git clone <your-repo> GhostConnect
cd GhostConnect
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

3. Make the script executable:
```bash
chmod +x ghostconnect.py
```

## Usage

Run the tool with sudo:

```bash
sudo python3 ghostconnect.py
```

### What Happens

1. **Root Check**: Ensures you have proper privileges
2. **Dependency Installation**: Auto-installs Tor, ProxyChains4, and LibreWolf if missing
   - Adds LibreWolf repository to APT sources
   - Imports LibreWolf GPG key
   - Installs LibreWolf package
3. **Configuration**:
   - Backs up original ProxyChains config
   - Configures strict chain mode with DNS proxying
   - **No browser hardening needed** - LibreWolf is pre-hardened!
4. **Tor Launch**: Starts Tor service and waits for circuit establishment
5. **Browser Launch**: Opens LibreWolf through ProxyChains with `--private-window` flag
   - Opens directly to https://check.torproject.org to verify Tor connection
6. **Active Monitoring**: Displays status and waits for user action
7. **Clean Exit**: Press CTRL+C to cleanly shut down everything

### Privacy Features (Built into LibreWolf)

LibreWolf comes with these privacy features **pre-configured**:

- **WebRTC disabled** - Prevents IP leaks through WebRTC
- **IPv6 disabled** - Forces IPv4 to prevent IPv6 leaks
- **Fingerprinting resistance** - Reduces browser fingerprinting
- **First-party isolation** - Isolates cookies per domain
- **No telemetry** - Zero Mozilla or third-party telemetry
- **DNS prefetching disabled** - Prevents DNS leaks
- **Tracking protection** - Enhanced tracking protection enabled
- **Auto-delete data** - Clears cookies and cache on close
- **uBlock Origin** - Ad/tracker blocking built-in
- **HTTPS-Only mode** - Forces HTTPS connections

No manual configuration required!

## Security Notes

### What This Tool Does

- Routes all LibreWolf traffic through Tor network
- Prevents DNS leaks
- Uses LibreWolf's built-in privacy protections
- Creates isolated browsing environment
- Cleans up after itself

### What This Tool Does NOT Do

- This is NOT a silver bullet for complete anonymity
- Does not protect against:
  - Browser fingerprinting (partially mitigated)
  - Login-based tracking (if you log into accounts)
  - Advanced persistent threats
  - Physical attacks or malware
- Does not encrypt traffic beyond Tor exit nodes
- Does not guarantee protection if you reveal identifying information

### Best Practices

1. **Never log into personal accounts** while in Ghost Mode
2. **Don't download files** that could contain identifying metadata
3. **Verify your IP** at https://check.torproject.org
4. **Keep Tor Browser updated** for latest security patches
5. **Consider Tails OS** for higher security requirements
6. **Don't mix** anonymous and non-anonymous browsing

## Troubleshooting

### Tor won't start
```bash
# Check Tor status
sudo service tor status

# View Tor logs
sudo tail -f /var/log/tor/log

# Restart manually
sudo service tor restart
```

### LibreWolf won't launch
```bash
# Check if LibreWolf is already running
ps aux | grep librewolf

# Kill existing instances
pkill -9 librewolf

# Verify LibreWolf installation
which librewolf
librewolf --version

# Verify ProxyChains config
cat /etc/proxychains4.conf
```

### Port 9050 already in use
```bash
# Find what's using the port
sudo netstat -tulpn | grep 9050

# Stop conflicting service
sudo service tor stop
```

### LibreWolf installation fails
```bash
# Check repository file
cat /etc/apt/sources.list.d/librewolf.list

# Manually add repository
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/librewolf.gpg] http://deb.librewolf.net $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/librewolf.list

# Re-add GPG key
wget -qO- https://deb.librewolf.net/keyring.gpg | sudo gpg --dearmor -o /usr/share/keyrings/librewolf.gpg

# Update and install
sudo apt update && sudo apt install -y librewolf
```

## File Structure

```
GhostConnect/
├── ghostconnect.py       # Main tool
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── LICENSE              # License file
```

## Configuration Files Modified

- **/etc/proxychains4.conf** - ProxyChains configuration (backed up to .ghost.bak)
- **/etc/apt/sources.list.d/librewolf.list** - LibreWolf repository (created during install)
- **/usr/share/keyrings/librewolf.gpg** - LibreWolf GPG key (created during install)

## Technical Details

### ProxyChains Configuration

```
strict_chain              # All proxies must be online
proxy_dns                 # DNS requests through proxy
socks5 127.0.0.1 9050    # Tor SOCKS5 proxy
```

### Tor Service

- **SOCKS Port**: 9050
- **Control Port**: 9051 (if enabled)
- **Service**: systemd service `tor`

### Signal Handling

The tool properly handles:
- SIGINT (CTRL+C)
- SIGTERM (kill)

Both trigger clean shutdown sequence.

## License

This tool is provided for educational and authorized security testing purposes only.

## Disclaimer

**IMPORTANT**: This tool is designed for:
- Legitimate privacy protection
- Authorized security research
- Educational purposes
- Penetration testing with proper authorization

**DO NOT USE** for:
- Illegal activities
- Unauthorized access
- Malicious purposes
- Evading law enforcement

The author assumes no liability for misuse of this tool. Always comply with applicable laws and regulations.

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style
- Security best practices maintained
- Documentation updated
- Testing on Kali Linux

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check troubleshooting section above
- Review Tor Project documentation

## Credits

Built with:
- [Tor Project](https://www.torproject.org/)
- [ProxyChains](https://github.com/haad/proxychains)
- [LibreWolf](https://librewolf.net/) - Privacy-hardened Firefox fork
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [Colorama](https://github.com/tartley/colorama) - Cross-platform colors

---

**Stay Anonymous. Stay Safe. Stay Legal.**

🔒 Ghost Mode Activated
