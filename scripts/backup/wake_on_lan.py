# scripts/backup/wake_on_lan.py
import sys
from wakeonlan import send_magic_packet

if len(sys.argv) < 2:
    print("Usage: python wake_on_lan.py <MAC_ADDRESS>", file=sys.stderr)
    sys.exit(1)

mac_address = sys.argv[1]
print(f"Sending Wake-on-LAN magic packet to {mac_address}...")
try:
    send_magic_packet(mac_address)
    print("Packet sent successfully.")
except Exception as e:
    print(f"Error sending packet: {e}", file=sys.stderr)
    sys.exit(1)