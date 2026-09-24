"""
============================================================================
PORTAL CATIVO - FATEC JAHU
Backend em Flask
============================================================================
Este servidor tem duas funções:

  1. Servir a página do portal (portal-fatec-jahu.html) para qualquer
     dispositivo que se conectar ao hotspot. É para cá que o iptables
     redireciona todo mundo que tenta acessar a internet (ver firewall.sh).

  2. Receber o clique do botão "Liberar acesso à internet" da página e,
     a partir do IP de quem clicou, adicionar uma regra no iptables
     liberando aquele dispositivo específico para navegar livremente.

Como rodar:
  sudo python3 app.py

(precisa de sudo/root porque: a porta 80 é uma porta privilegiada, e
porque o comando iptables também exige privilégios de administrador)
============================================================================
"""

from flask import Flask, request, send_from_directory, jsonify
import subprocess
import re
import os

app = Flask(__name__)

# ----------------------------------------------------------------------
# CONFIGURAÇÕES — ajuste esses valores para o seu ambiente
# ----------------------------------------------------------------------

# Pasta onde está o arquivo HTML do portal.
# Por padrão, assume que está na MESMA pasta deste app.py.
# Se você deixou o portal-fatec-jahu.html em outro lugar, mude aqui.
PASTA_PORTAL = os.path.dirname(os.path.abspath(__file__))
NOME_ARQUIVO_PORTAL = "portal-fatec-jahu.html"

# Nome da interface de rede que o hostapd está usando para o HOTSPOT
# (a rede onde os convidados se conectam — não confundir com a interface
# que dá acesso à internet). Descubra o nome real com o comando:
#   ip addr
INTERFACE_HOTSPOT = "wlo1"



# ----------------------------------------------------------------------
# ROTA 1: servir a página do portal
# ----------------------------------------------------------------------
@app.route("/")
def portal():
    """
    Serve o arquivo HTML do portal cativo.
    Qualquer dispositivo do hotspot que tentar abrir um site
    (ex: google.com) cai aqui, por causa do redirecionamento
    configurado no firewall.sh (regra DNAT na porta 80).
    """
    return send_from_directory(PASTA_PORTAL, NOME_ARQUIVO_PORTAL)


# ----------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE SEGURANÇA
# ----------------------------------------------------------------------
def ip_valido(ip):
    """
    Confere se o texto recebido realmente parece um endereço IPv4
    válido (ex: 192.168.50.10) antes de usá-lo dentro de um comando
    de sistema. Isso é importante para evitar que alguém tente
    "injetar" comandos maliciosos manipulando o IP de origem.
    """
    padrao = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(padrao, ip):
        return False
    # cada bloco do IP precisa estar entre 0 e 255
    return all(0 <= int(bloco) <= 255 for bloco in ip.split("."))


def obter_ip_cliente():
    """
    Descobre o IP de quem fez a requisição HTTP.
    Como o Flask, aqui, roda direto na máquina do hotspot (sem
    nenhum proxy no meio), request.remote_addr já é o IP real
    do celular/notebook do usuário dentro da rede 192.168.50.0/24.
    """
    return request.remote_addr


# ----------------------------------------------------------------------
# ROTA 2: liberar o acesso do dispositivo que clicou no botão
# ----------------------------------------------------------------------
@app.route("/liberar_acesso", methods=["POST"])
def liberar_acesso():
    """
    Chamada pelo botão "Liberar acesso à internet" da página
    (função liberarAcesso() no JavaScript do portal).

    Passo a passo:
      1. Descobre o IP de quem clicou
      2. Valida esse IP (ip_valido) por segurança
      3. Insere uma regra no iptables permitindo que ESSE IP
         específico tenha seu tráfego encaminhado (FORWARD) para
         a internet — o NAT geral já foi configurado no firewall.sh
      4. Responde em JSON se deu certo ou não
    """
    ip_cliente = obter_ip_cliente()

    if not ip_valido(ip_cliente):
        return jsonify({"ok": False, "erro": "IP inválido"}), 400

    try:
        # -I insere a regra no TOPO da chain FORWARD, garantindo que ela
        # seja avaliada antes de qualquer regra de bloqueio genérica.
        subprocess.run(
            [
                "sudo", "iptables",
                "-I", "FORWARD",
                "-s", ip_cliente,          # só esse IP de origem
                "-i", INTERFACE_HOTSPOT,   # só tráfego vindo do hotspot
                "-j", "ACCEPT"
            ],
            check=True,          # levanta erro se o comando falhar
            capture_output=True  # captura stdout/stderr para debug
        )

        print(f"[liberado] IP {ip_cliente} agora tem acesso à internet")
        return jsonify({"ok": True, "ip_liberado": ip_cliente})

    except subprocess.CalledProcessError as erro:
        print(f"[erro] Falha ao liberar {ip_cliente}: {erro.stderr}")
        return jsonify({"ok": False, "erro": "Falha ao liberar acesso"}), 500


# ----------------------------------------------------------------------
# INICIALIZAÇÃO DO SERVIDOR
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # host="0.0.0.0" -> escuta em TODAS as interfaces de rede da máquina,
    #                   incluindo a interface do hotspot (necessário para
    #                   os convidados conseguirem acessar o servidor)
    # port=80        -> porta HTTP padrão (assim o navegador do usuário
    #                   não precisa digitar nenhuma porta na URL)
    app.run(host="0.0.0.0", port=80, debug=False)
