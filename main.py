
import os
import requests

from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from bs4 import BeautifulSoup


URL = "https://investidor10.com.br/acoes/dividendos/"

TELEGRAM_API = "https://api.telegram.org/bot{}/sendMessage"

MAX_MESSAGE_SIZE = 3900

MESES = {
    "01": "janeiro",
    "02": "fevereiro",
    "03": "marco",
    "04": "abril",
    "05": "maio",
    "06": "junho",
    "07": "julho",
    "08": "agosto",
    "09": "setembro",
    "10": "outubro",
    "11": "novembro",
    "12": "dezembro"
}


def buscar_proventos():
    resposta = requests.get(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=30
    )

    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")

    proventos = []
    registros_processados = set()

    for linha in soup.select("tr[ticker-name]"):

        ticker = linha.get("ticker-name", "").strip()

        campos = linha.select("span.table-field")

        valor_elemento = linha.select_one("span.payment-price")

        if not ticker or len(campos) < 3 or not valor_elemento:
            continue

        data_com = campos[0].get_text(strip=True)
        pagamento = campos[1].get_text(strip=True)
        tipo = campos[2].get_text(strip=True)

        valor = valor_elemento.get_text(" ", strip=True)

        try:
            data_com_obj = datetime.strptime(data_com, "%d/%m/%y")
            pagamento_obj = datetime.strptime(pagamento, "%d/%m/%y")
        except ValueError:
            continue

        registro = (
            ticker,
            data_com,
            pagamento,
            tipo,
            valor
        )

        if registro in registros_processados:
            continue

        registros_processados.add(registro)

        proventos.append({
            "ticker": ticker,
            "data_com": data_com,
            "pagamento": pagamento,
            "tipo": tipo,
            "valor": valor,
            "data_com_obj": data_com_obj,
            "pagamento_obj": pagamento_obj
        })

    proventos.sort(
        key=lambda item: item["pagamento_obj"]
    )

    return proventos


def gerar_url_fonte(referencia):
    mes, ano = referencia.split("/")

    nome_mes = MESES[mes]

    return (
        f"https://investidor10.com.br/acoes/"
        f"dividendos/{ano}/{nome_mes}/"
    )


def gerar_cabecalho(proventos, referencia):

    url_fonte = gerar_url_fonte(referencia)

    return (
        "<b>AGENDA DE DIVIDENDOS</b>\n"
        f"📅 Referência: {referencia}\n"
        f"📌 Total de registros: {len(proventos)}\n"
        f'🔎 Fonte: <a href="{url_fonte}">'
        "Investidor10 – Agenda de Dividendos</a>\n"
    )


def formatar_linha(provento):

    return (
        f"{provento['ticker']:<8}"
        f"{provento['tipo']:<12}"
        f"{provento['valor']:>12}"
        f"{provento['data_com'][:5]:>8}"
        f"{provento['pagamento'][:5]:>12}"
    )


def gerar_mensagens(proventos, referencia):

    cabecalho = gerar_cabecalho(
        proventos,
        referencia
    )

    titulo_tabela = (
        f"{'ATIVO':<8}"
        f"{'TIPO':<12}"
        f"{'VALOR':>12}"
        f"{'COM':>8}"
        f"{'PGTO':>12}"
    )

    linhas = [
        titulo_tabela,
        "-" * len(titulo_tabela)
    ]

    for provento in proventos:
        linhas.append(formatar_linha(provento))

    mensagens = []
    linhas_atuais = [linhas[0], linhas[1]]

    def montar_mensagem(linhas_tabela):
        tabela = "\n".join(linhas_tabela)

        return (
            cabecalho
            + "<pre>"
            + escape(tabela)
            + "</pre>"
        )

    for linha in linhas[2:]:

        teste = montar_mensagem(
            linhas_atuais + [linha]
        )

        if len(teste) > MAX_MESSAGE_SIZE:

            mensagens.append(
                montar_mensagem(linhas_atuais)
            )

            linhas_atuais = [
                titulo_tabela,
                "-" * len(titulo_tabela),
                linha
            ]

        else:
            linhas_atuais.append(linha)

    if len(linhas_atuais) > 2 or not mensagens:
        mensagens.append(
            montar_mensagem(linhas_atuais)
        )

    return mensagens


def enviar_telegram(mensagens):

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    message_thread_id = os.environ["TELEGRAM_MESSAGE_THREAD_ID"]

    url = TELEGRAM_API.format(token)

    for mensagem in mensagens:

        resposta = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "message_thread_id": message_thread_id,
                "text": mensagem,
                "parse_mode": "HTML"
            },
            timeout=30
        )

        resposta.raise_for_status()

        resultado = resposta.json()

        if not resultado.get("ok"):
            raise RuntimeError(
                f"Erro no Telegram: {resultado}"
            )


def main():

    print("Buscando agenda de dividendos...")

    proventos = buscar_proventos()

    referencia = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%m/%Y")

    print(f"Referência: {referencia}")
    print(f"Total de registros: {len(proventos)}")

    if not proventos:
        print("Nenhum provento encontrado.")
        return

    mensagens = gerar_mensagens(
        proventos,
        referencia
    )

    print(f"Total de mensagens: {len(mensagens)}")

    enviar_telegram(mensagens)

    print("Agenda enviada com sucesso!")


if __name__ == "__main__":
    main()
