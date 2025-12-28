# Hotspot Configuration for *Trixie* OS

[![Up](img/goup.gif)](./bp_PiZero_Standalone.md)

This section describes how to configure a Raspberry Pi as a **standalone Wi-Fi hotspot**
using **NetworkManager**, as provided by default in *Debian Trixie / Raspberry Pi OS (Trixie)*.

**Note**: This configuration is **not compatible with older Bookworm-style setups** that relied on
`dnsmasq`, `iptables`, or `/etc/network/interfaces`.

---

## Overview

NetworkManager provides built-in support for:

- Access Point (AP) mode
- DHCP server for hotspot clients
- NAT (masquerading)
- IP forwarding

No additional network services or firewall rules are required for a basic hotspot.

## Naming Conventions

In the following description, replace:

- `<SSID>` with the intended hotspot SSID  
  e.g. `RaspiCamSrv01`
- `<passphrase>` with the WPA2 passphrase

The NetworkManager **connection ID** used throughout this document is:   
RaspiCamSrv

## 1. Create the hotspot connection

```
sudo nmcli con add type wifi ifname wlan0 con-name RaspiCamSrv ssid <SSID> \
  connection.autoconnect yes
```

## 2. Configure hotspot parameters

Enable Access Point mode and WPA2 security:

```
sudo nmcli con modify RaspiCamSrv \
  802-11-wireless.mode ap \
  802-11-wireless.band bg \
  wifi-sec.key-mgmt wpa-psk \
  wifi-sec.psk "<passphrase>"

```

(Optional) Lock the Wi-Fi channel for improved stability:

```
sudo nmcli con modify RaspiCamSrv 802-11-wireless.channel 6
```

## 3. Enable shared IPv4 networking (recommended)

```
sudo nmcli con modify RaspiCamSrv ipv4.method shared
```

This automatically enables:

- DHCP for hotspot clients
- NAT (masquerading)
- IPv4 forwarding

## 4. Activate the hotspot

```bash
sudo nmcli con up RaspiCamSrv
```

**NOTE**: If your SSH session uses Wi-Fi, the connection will now be lost.    
Reconnection will use Ethernet.

## 5. Verify hotspot status

Check active connections:

```bash
nmcli con show --active
```

Check IP address assigned to the hotspot interface:
```bash
ip addr show wlan0
```
You should see an address in the range assigned by NetworkManager   
(e.g. 10.42.0.1/24 or similar)

## 6. Setup mDNS

To provide host name resolution to clients, [mDNS (Multicast DNS)](https://en.wikipedia.org/wiki/Multicast_DNS) can be used instead of a full-fledged DNS server.

Install and enable [Avahi](https://en.wikipedia.org/wiki/Avahi_(software)):
```
sudo apt install avahi-daemon
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

With Avahi, you will need to connect to the Raspberry Pi with    
```<hostname>.local``` instead of ```<hostname>``` or IP address,    
where ```<hostname>``` is the name given during [OS Installation](./bp_PiZero_Standalone.md#1-install-os-on-microsd-card)

## 7. Test hotspot access

1. Disconnect the Ethernet cable
2. Power-cycle the Raspberry Pi
3. From a mobile device:   
-- Search for the Wi-Fi network ```<SSID>```    
-- Connect using the configured passphrase    
-- Verify internet or local access   
-- With a Ping tool, try to ping ```<hostname>.local```