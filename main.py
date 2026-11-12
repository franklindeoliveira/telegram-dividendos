
import os
import re
from datetime import datetime
from html import escape

import requests
from bs4 import BeautifulSoup

URL = "https://investidor10.com.br/acoes/dividendos/"
TELEGRAM_API = "https://api.telegram.org"

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def buscar_proventos():
    response = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
        timeout=30,
    )

    print("===== DIAGNOSTICO INVESTIDOR10 =====")
    print("Status HTTP:", response.status_code)
    print("URL final:", response.url)
    print("Content-Type:", response.headers.get("Content-Type"))
    print("Tamanho HTML:", len(response.text))

    soup = BeautifulSoup(response.text, "html.parser")

    print("Titulo:", soup.title.get_text(strip=True) if soup.title else "Sem titulo")

    texto = soup.get_text(" ", strip=True)

    print("===== INICIO DO TEXTO RECEBIDO =====")
    print(texto[:5000])
    print("===== FIM DO TEXTO =====")

    raise RuntimeError("Diagnostico concluido. Verifique os logs.")


def enviar_telegram(mensagem):
    url = f"{TELEGRAM_API}/bot{TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensagem,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()

    resultado = response.json()
    if not resultado.get("ok"):
        raise RuntimeError(f"Erro do Telegram: {resultado}")


def main():
    proventos = buscar_proventos()

    mes = datetime.now().strftime("%m/%Y")

    linhas = [
        "📊 <b>AGENDA DE DIVIDENDOS</b>",
        f"📅 Referência: {mes}",
        f"📌 Total de registros: {len(proventos)}",
        "",
    ]

    for item in proventos:
        linhas.append(
            f"💰 <b>{escape(item['ticker'])}</b> — "
            f"{escape(item['tipo'])}\n"
            f"   Valor: R$ {escape(item['valor'])}\n"
            f"   Data COM: {escape(item['data_com'])}\n"
            f"   Pagamento: {escape(item['pagamento'])}\n"
        )

    linhas.append(
        '\n<a href="https://investidor10.com.br/acoes/dividendos/">'
        "Consultar agenda no Investidor10</a>"
    )

    mensagem = "\n".join(linhas)

    # O Telegram limita mensagens a 4096 caracteres.
    partes = []
    atual = ""

    for linha in mensagem.split("\n"):
        if len(atual) + len(linha) + 1 > 3800:
            partes.append(atual)
            atual = ""
        atual += linha + "\n"

    if atual.strip():
        partes.append(atual)

    for parte in partes:
        enviar_telegram(parte)

    print(f"{len(proventos)} registros enviados ao Telegram.")


if __name__ == "__main__":
    main()
