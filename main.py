
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

    proventos = []

    # Localiza as linhas que possuem o atributo ticker-name.
    linhas = soup.select("tr[ticker-name]")

    for linha in linhas:
        ticker = linha.get("ticker-name", "").strip().upper()

        # Datas e tipo do provento estão nos elementos table-field.
        campos = [
            campo.get_text(" ", strip=True)
            for campo in linha.select("span.table-field")
        ]

        # Valor do provento.
        elemento_valor = linha.select_one("span.payment-price")

        if not elemento_valor or len(campos) < 3:
            continue

        data_com = campos[0]
        pagamento = campos[1]
        tipo = campos[2].upper()

        valor = elemento_valor.get_text(" ", strip=True)
        valor = valor.replace("R$", "").strip()

        try:
            datetime.strptime(data_com, "%d/%m/%y")
            datetime.strptime(pagamento, "%d/%m/%y")
        except ValueError:
            continue

        if not ticker or not valor:
            continue

        proventos.append({
            "ticker": ticker,
            "data_com": data_com,
            "pagamento": pagamento,
            "tipo": tipo,
            "valor": valor,
        })

    # Evita registros duplicados.
    unicos = {}

    for item in proventos:
        chave = (
            item["ticker"],
            item["data_com"],
            item["pagamento"],
            item["tipo"],
            item["valor"],
        )
        unicos[chave] = item

    proventos = list(unicos.values())

    if not proventos:
        raise RuntimeError(
            "Nenhum provento encontrado nas linhas da tabela HTML."
        )

    proventos.sort(
        key=lambda item: datetime.strptime(
            item["pagamento"], "%d/%m/%y"
        )
    )

    print(f"Total de proventos encontrados: {len(proventos)}")

    for item in proventos[:5]:
        print(item)

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
