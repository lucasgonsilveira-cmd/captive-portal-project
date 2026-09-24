# Backend do Portal Cativo — Fatec Jahu

Esses arquivos, junto com o `portal-fatec-jahu.html`, formam o hotspot completo.

## O que cada arquivo faz

| Arquivo | Função |
|---|---|
| `hostapd.conf` | Cria a rede wifi do hotspot (o SSID que os convidados veem) |
| `dnsmasq.conf` | Dá IP pra cada dispositivo (DHCP) e redireciona todo domínio pro portal (DNS) |
| `firewall.sh` | Bloqueia a internet por padrão e prepara o redirecionamento HTTP |
| `app.py` | Serve a página do portal e libera o acesso quando o botão é clicado |

## Antes de começar

Instale as ferramentas necessárias (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install hostapd dnsmasq python3-flask -y
```

Descubra o nome das suas interfaces de rede:

```bash
ip addr
```

Você vai precisar de **duas interfaces**:
- Uma para o **hotspot** (broadcast do wifi) — ex: `wlan1`
- Uma para a **internet de verdade** (uplink) — ex: `wlan0` conectado ao tethering do celular

Se os nomes forem diferentes de `wlan1`/`wlan0`, ajuste em `hostapd.conf`, `dnsmasq.conf`, `app.py` (variável `INTERFACE_HOTSPOT`) e no comando do `firewall.sh`.

## Ordem de execução (todo dia de teste/apresentação)

```bash
# 1. Pare serviços que podem conflitar com o dnsmasq
sudo systemctl stop systemd-resolved

# 2. Configure o IP fixo da interface do hotspot
sudo ip addr add 192.168.50.1/24 dev wlan1

# 3. Suba o hostapd (cria o wifi)
sudo hostapd /etc/hostapd/hostapd.conf &

# 4. Suba o dnsmasq (DHCP + DNS)
sudo dnsmasq -C /etc/dnsmasq.conf

# 5. Configure o firewall (bloqueio + redirecionamento)
sudo bash firewall.sh wlan1 wlan0

# 6. Suba o servidor do portal
sudo python3 app.py
```

A partir daqui, qualquer celular que conectar na rede `TCC-Fatec-Jahu` deve cair automaticamente na página do portal ao tentar abrir qualquer site.

## Permissão do Flask para rodar o `iptables`

Como pedimos para rodar `app.py` com `sudo`, o próprio processo Flask já roda como root, então o `subprocess.run(["sudo", "iptables", ...])` dentro do `app.py` funciona sem pedir senha de novo. **Isso é aceitável para um projeto de faculdade rodando na sua própria rede controlada** — não é uma prática recomendada para um servidor em produção exposto publicamente.

## Testando sem esperar o dia da apresentação

1. Rode os passos 1–6 acima na sua máquina.
2. Conecte outro dispositivo (seu celular, por exemplo) na rede `TCC-Fatec-Jahu`.
3. Tente abrir qualquer site — deve cair na página do portal.
4. Clique em um curso, depois em "Liberar acesso à internet".
5. Tente abrir um site de novo — agora deve funcionar normalmente.

Para ver se a liberação realmente aconteceu no firewall, rode em outro terminal:

```bash
sudo iptables -L FORWARD -v -n
```

Você deve ver uma linha `ACCEPT` com o IP do dispositivo que você liberou.

## Sobre o plano B (rede móvel de backup)

Se decidir ter uma segunda fonte de internet pronta (ex: tethering de outro celular), basta que ela apareça como **outra interface de rede** (`wlan2`, por exemplo). Para trocar de uplink na hora, repita só os passos 5 e 6 trocando `wlan0` pela nova interface — não precisa mexer no hostapd nem no dnsmasq, porque eles não sabem (nem precisam saber) de onde vem a internet.
