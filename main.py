
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
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # A página apresenta os dados em linhas de texto.
    texto = soup.get_text(" ", strip=True)

    padrao = re.compile(
        r"\b([A-Z]{4}\d{1,2})\b"
        r"\s+(.{1,100}?)"
        r"\s*\|\s*Data Com\s+(\d{2}/\d{2}/\d{2})"
        r"\s*\|\s*Pgto\s+(\d{2}/\d{2}/\d{2})"
        r"\s*\|\s*(Dividendos|JSCP)\s+R\$\s*([\d.,]+)",
        re.IGNORECASE,
    )

    proventos = []

    for ticker, empresa, data_com, pagamento, tipo, valor in padrao.findall(texto):
        proventos.append({
            "ticker": ticker,
            "data_com": data_com,
            "pagamento": pagamento,
            "tipo": tipo.upper(),
            "valor": valor,
        })

    if not proventos:
        raise RuntimeError(
            "Nenhum provento encontrado. "
            "Verifique a resposta HTML do Investidor10."
        )

    proventos.sort(
        key=lambda item: datetime.strptime(
            item["pagamento"], "%d/%m/%y"
        )
    )

    return proventos

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
