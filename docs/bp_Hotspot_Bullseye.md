# Hotspot Configuration for 'Bullseye' OS

[![Up](img/goup.gif)](./bp_PiZero_Standalone.md)

This section describes how to configure a Raspberry Pi as hotspot if the OS is *Debian Bullseye*.

## 1. Install required packages

```
sudo apt install dnsmasq hostapd iptables
```

## 2. Configure WLAN

```
sudo nano /etc/dhcpcd.conf
```

Copy/Paste the following code:

```
interface wlan0
static ip_address=192.168.1.1/24
nohook wpa_supplicant
```

This will configure the Wi-Fi adapter with a static IP address 192.168.1.1

## 3. Restart DHCP

```
sudo systemctl restart dhcpcd
```

If your client is connected through Wi-Fi, it will now lose connection
and you need to reconnect, which will now use the ethernet connection.

## 4. Check interfaces

```
ip l
```

Check that both, the ethernet interface (eth0) and Wi-Fi adapter (wlan0) are available.

## 5. Setup DHCP server and DNS-Cache

```
sudo mv /etc/dnsmasq.conf /etc/dnsmasq.conf_orig

sudo nano /etc/dnsmasq.conf
```

Enter the following code:

```
interface=wlan0
no-dhcp-interface=eth0
dhcp-range=192.168.1.100,192.168.1.200,255.255.255.0,24h
dhcp-option=option:dns-server,192.168.1.1
```

## 6. Test & start DHCP server and DNS Cache

```
dnsmasq --test -C /etc/dnsmasq.conf
```

The response should be
```
dnsmasq: syntax check OK.
```

## 7. Restart DNSMASQ and enable it for automatic start

```
sudo systemctl restart dnsmasq

sudo systemctl status dnsmasq

sudo systemctl enable dnsmasq
```

## 8. Setup WLAN-AP-Host (hostapd)

```
sudo nano /etc/hostapd/hostapd.conf
```

Replace the content with the following code

```
interface=wlan0
ssid=<SSID>
channel=1
hw_mode=g
ieee80211n=1
ieee80211d=1
country_code=<Country Code>
wmm_enabled=1
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase=<wpa_passphrase>
```

where you need to replace

- <SSID> with the intended SSID for the hotspot (e.g.: RaspiCamSrv)
- <Country Code> with your [A-2 ISO 3166-1 Country Code](https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes)
- <wpa_passphrase> with the passphrase to secure hotspot access

## 9. Test & start WLAN-AP-Host

```
sudo hostapd -dd /etc/hostapd/hostapd.conf
```

At the end of the output you should find:

```
...
wlan0: interface state COUNTRY_UPDATE->ENABLED
...
wlan0: AP-ENABLED
...

```

## 10. Test Hotspot Access

With a mobile device try to access the hotspot.

This will generate log output in the SSH session.

## 11. Enable hostapd process for automatic start

In the SSH session stop the active process<br>
<Ctrl+C>

```
sudo systemctl unmask hostapd
sudo systemctl start hostapd
sudo systemctl enable hostapd
```

## 12. Check that hostapd is active

```
sudo systemctl status hostapd
```

## 13. Activate routing

```
sudo nano /etc/sysctl.conf
```

Find and uncomment the following line:

```
net.ipv4.ip_forward=1
```

## 14. Activate NAT

```
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

sudo sh -c "iptables-save > /etc/iptables.ipv4.nat"
```

## 15. Assure NAT activation at system start

```
sudo nano /etc/rc.local
```

Before the last line with ```exit 0``` enter

```
iptables-restore < /etc/iptables.ipv4.nat
```

## 16. Reboot the system

```
sudo reboot
```

## 18. Check processes

After reconnecting with SSH

```
sudo systemctl status hostapd

ps ax | grep hostapd

sudo systemctl status dnsmasq

ps ax | grep dnsmasq
```

## 19. Test Hotspot access

- Unplug the network cable
- Switch Off/On the power supply
- From a mobile device, wait for the hotspot and try to connect.