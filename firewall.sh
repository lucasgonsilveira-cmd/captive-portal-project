#!/bin/bash
# ============================================================================
# FIREWALL.SH — regras de rede do portal cativo
# ============================================================================
# Este script configura o roteamento entre o hotspot e a internet, e
# bloqueia por padrão qualquer dispositivo que ainda não tenha clicado
# em "Liberar acesso" na página do portal.
#
# QUANDO RODAR: depois de subir o hostapd e o dnsmasq, e ANTES de deixar
# qualquer convidado conectar no wifi.
#
# COMO RODAR:
#   sudo bash firewall.sh <interface_hotspot> <interface_internet>
#
# EXEMPLO (hotspot na wlan1, internet vindo do tethering do celular na wlan0):
#   sudo bash firewall.sh wlan1 wlan0
# ============================================================================

IF_HOTSPOT=$1     # interface onde os CONVIDADOS se conectam (o hotspot em si)
IF_INTERNET=$2    # interface por onde a INTERNET DE VERDADE chega (ex: tethering 4G)

if [ -z "$IF_HOTSPOT" ] || [ -z "$IF_INTERNET" ]; then
  echo "Uso: sudo bash firewall.sh <interface_hotspot> <interface_internet>"
  echo "Exemplo: sudo bash firewall.sh wlan1 wlan0"
  exit 1
fi

echo "Configurando firewall..."
echo "  Hotspot (convidados):  $IF_HOTSPOT"
echo "  Internet (uplink):     $IF_INTERNET"

# ----------------------------------------------------------------------
# 1. Habilita o encaminhamento de pacotes no kernel Linux
# ----------------------------------------------------------------------
# Por padrão, o Linux NÃO roteia tráfego entre duas interfaces de rede
# diferentes. Esse comando liga essa capacidade — sem ele, mesmo com
# hostapd e dnsmasq funcionando, ninguém conseguiria navegar de fato.
sysctl -w net.ipv4.ip_forward=1

# ----------------------------------------------------------------------
# 2. Limpa regras antigas (para começar do zero a cada execução)
# ----------------------------------------------------------------------
iptables -F            # limpa regras de filtro (bloqueio/liberação)
iptables -t nat -F      # limpa regras de NAT/redirecionamento

# ----------------------------------------------------------------------
# 3. NAT — mascara o tráfego que sai para a internet de verdade
# ----------------------------------------------------------------------
# Isso faz os dispositivos do hotspot "parecerem" ser essa própria
# máquina quando o tráfego deles sai pela internet (necessário porque
# eles usam IPs internos, tipo 192.168.50.x, que não existem na internet).
iptables -t nat -A POSTROUTING -o "$IF_INTERNET" -j MASQUERADE

# ----------------------------------------------------------------------
# 4. Bloqueia tudo por padrão
# ----------------------------------------------------------------------
# A política padrão da chain FORWARD vira DROP: ou seja, por padrão,
# NINGUÉM do hotspot consegue ter tráfego encaminhado para a internet.
# É o Flask (app.py) que vai abrir uma exceção pontual pra cada IP,
# depois que a pessoa clicar em "Liberar acesso".
iptables -P FORWARD DROP

# ----------------------------------------------------------------------
# 5. Redireciona todo tráfego HTTP (porta 80) para o portal
# ----------------------------------------------------------------------
# Essa regra "engana" qualquer tentativa de acessar um site: mesmo que
# o celular tente abrir "http://google.com", a conexão é redirecionada
# (DNAT) para o IP e porta do nosso próprio servidor Flask. É esse
# comportamento que faz o celular "detectar" o portal cativo sozinho.
iptables -t nat -A PREROUTING -i "$IF_HOTSPOT" -p tcp --dport 80 \
  -j DNAT --to-destination 192.168.50.1:80

echo ""
echo "Firewall configurado com sucesso."
echo "Dispositivos conectados ao hotspot só vão conseguir ver o portal"
echo "até que cliquem em 'Liberar acesso à internet'."
