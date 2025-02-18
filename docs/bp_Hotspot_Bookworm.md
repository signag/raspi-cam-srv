# Hotspot Configuration for 'Bookworm' OS

[![Up](img/goup.gif)](./bp_PiZero_Standalone.md)

This section describes how to configure a Raspberry Pi as hotspot if the OS is *Debian Bookworm*.

In the following description, you will need to replace

- ```<SSID>``` with the intended hotspot SSID, e.g. "RaspCamSrv01"
- ```<passphrase>``` with the passphrase to protect hotspot access

The connection ID, used in [NetworkManager](https://networkmanager.dev/docs/api/latest/nmcli.html) commands is chosen as "RaspiCamSrv"

## 1. Install required packages

```
sudo apt install dnsmasq iptables
```

## 2. Configure Hotspot

```
sudo nmcli con add type wifi ifname wlan0 con-name RaspiCamSrv autoconnection yes ssid <SSID>

sudo nmcli con modify RaspiCamSrv 802-11-wireless.mode ap 802-11-wireless.band bg

sudo nmcli con modify RaspiCamSrv wifi-sec.key-mgmt wpa-psk

sudo nmcli con modify RaspiCamSrv wifi-sec.psk "<passphrase>"

```

## 3. Assign a Fixed IP Address

```
sudo nmcli con modify RaspiCamSrv ipv4.method manual ipv4.addresses 192.168.1.1/24

sudo nmcli con modify RaspiCamSrv ipv4.gateway 192.168.1.1

sudo nmcli con modify RaspiCamSrv ipv4.dns 192.168.1.1

```

## 4. Activate Hotspot

```
sudo nmcli con up RaspiCamSrv
```

If your SSH session uses the Wi-Fi Adapter, connection will now be lost.

If you reconnect, the ethernet adapter will be used.

At this time, a TCP/IP connection through the hotspot is not yet possible. 

## 5. Configure DHCP for hotspot

```
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf.orig

sudo nano /etc/dnsmasq.conf
```

Enter the following code:

```
interface=wlan0 
no-dhcp-interface=eth0
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
dhcp-option=option:router,192.168.1.1 
dhcp-option=option:dns-server,192.168.1.1
```

## 6. Check and start DHCP Server and DNS-Cache

```
dnsmasq --test -C /etc/dnsmasq.conf
```

## 7. Enable dnsmasq for automatic start

```
sudo systemctl restart dnsmasq

sudo systemctl status dnsmasq

sudo systemctl enable dnsmasq
```

## 8. Enable IP Forwarding

```
sudo nano /etc/sysctl.conf
```

Find and uncomment the following line:
```
net.ipv4.ip_forward=1
```

## 9. Set up NAT

```
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

sudo iptables -A FORWARD -i eth0 -o wlan0 -m state --state RELATED,ESTABLISHED -j ACCEPT

sudo iptables -A FORWARD -i wlan0 -o eth0 -j ACCEPT

```

## 10. Save Firewall Rules

```
sudo sh -c "iptables-save > /etc/iptables.rules"
```

## 11. Load firewall rules on boot

```
sudo nano /etc/network/interfaces
```

Add the following line:

```
post-up iptables-restore < /etc/iptables.rules
```

## 12. Extend hosts

```
sudo nano /etc/hosts
```

Add the following line:

```
192.168.1.1 <hostname>
```

where ```<hostname>``` must be replaced by the host name specified during OS setup.


## 13. Reboot the system

```
sudo reboot
```

## 14. Check processes

After reconnecting with SSH

```
nmcli con show --active

ip addr show wlan0
```

## 19. Test Hotspot access

- Unplug the network cable
- Switch Off/On the power supply
- From a mobile device, wait for the hotspot and try to connect.