FROM alpine:latest

# Install Tor and iptables for transparent proxying
RUN apk add --no-cache tor iptables bash

# Copy the hardened custom Tor configuration
COPY torrc /etc/tor/torrc

# Create necessary directories and set ownership for Tor
RUN mkdir -p /var/lib/tor && chown -R tor:tor /var/lib/tor

# Provide a startup script to establish the transparent proxy rules
# and then launch the Tor service
RUN echo '#!/bin/bash' > /entrypoint.sh && \
    echo 'echo "Setting up Transparent Proxy iptables rules..."' >> /entrypoint.sh && \
    # Redirect all DNS traffic passing through to Tor's DNSPort
    echo 'iptables -t nat -A PREROUTING -i eth0 -p udp --dport 53 -j REDIRECT --to-ports 5353' >> /entrypoint.sh && \
    # Redirect all TCP traffic passing through to Tor's TransPort
    echo 'iptables -t nat -A PREROUTING -i eth0 -p tcp --syn -j REDIRECT --to-ports 9040' >> /entrypoint.sh && \
    # Reject everything that bypasses the Tor proxy to prevent leaks and provide diagnostic feedback
    echo 'iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT' >> /entrypoint.sh && \
    echo 'iptables -A FORWARD -j REJECT --reject-with icmp-admin-prohibited' >> /entrypoint.sh && \
    echo 'echo "Starting Tor..."' >> /entrypoint.sh && \
    echo 'exec su -s /bin/sh -c "tor -f /etc/tor/torrc" tor' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Start the router
ENTRYPOINT ["/entrypoint.sh"]
