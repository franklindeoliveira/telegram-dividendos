
import os
import requests

from datetime import datetime
from html import escape
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL = "https://investidor10.com.br/acoes/dividendos/"

TELEGRAM_API = "https://api.telegram.org"

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


# ============================================================
# BUSCA DOS PROVENTOS NO INVESTIDOR10
# ============================================================

def buscar_proventos():
    print("Consultando agenda de dividendos...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
        )
    }

    resposta = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")

    linhas = soup.select("tr[ticker-name]")

    print(f"Linhas encontradas: {len(linhas)}")

    proventos = []
    registros_processados = set()

    for linha in linhas:
        ticker = linha.get("ticker-name", "").strip().upper()

        campos = [
            campo.get_text(" ", strip=True)
            for campo in linha.select("span.table-field")
        ]

        elemento_valor = linha.select_one("span.payment-price")

        if not ticker or not elemento_valor or len(campos) < 3:
            continue

        data_com = campos[0]
        pagamento = campos[1]
        tipo = campos[2].upper()

        valor = (
            elemento_valor
            .get_text(" ", strip=True)
            .replace("R$", "")
            .strip()
        )

        # Valida as datas
        try:
            data_com_obj = datetime.strptime(data_com, "%d/%m/%y")
            pagamento_obj = datetime.strptime(pagamento, "%d/%m/%y")
        except ValueError:
            continue

        registro = {
            "ticker": ticker,
            "tipo": tipo,
            "valor": valor,
            "data_com": data_com,
            "pagamento": pagamento,
            "pagamento_obj": pagamento_obj
        }

        # Evita registros duplicados
        chave = (
            ticker,
            data_com,
            pagamento,
            tipo,
            valor
        )

        if chave in registros_processados:
            continue

        registros_processados.add(chave)
        proventos.append(registro)

    # Ordena pela data de pagamento
    proventos.sort(
        key=lambda p: (
            p["pagamento_obj"],
            p["ticker"],
            p["tipo"]
        )
    )

    print(f"Total de proventos encontrados: {len(proventos)}")

    if not proventos:
        raise RuntimeError(
            "Nenhum provento encontrado. "
            "Verifique a estrutura da página do Investidor10."
        )

    return proventos


# ============================================================
# GERAÇÃO DA TABELA
# ============================================================

def gerar_mensagens(proventos, referencia):

    cabecalho = (
        f"<b>AGENDA DE DIVIDENDOS</b>\n"
        f"📅 Referência: {referencia}\n"
        f"📌 Total de registros: {len(proventos)}"
    )

    titulo_tabela = (
        f"{'ATIVO':<7} "
        f"{'TIPO':<10} "
        f"{'VALOR':>10} "
        f"{'COM':>5} "
        f"{'PAGAMENTO':>9}"
    )

    separador = "-" * len(titulo_tabela)

    linhas = []

    for p in proventos:

        ticker = p["ticker"]
        tipo = p["tipo"].upper()
        valor = f"R$ {p['valor']}"

        data_com = p["data_com"][:5]
        pagamento = p["pagamento"][:5]

        linha = (
            f"{ticker:<7} "
            f"{tipo:<10} "
            f"{valor:>10} "
            f"{data_com:>5} "
            f"{pagamento:>9}"
        )

        linhas.append(linha)

    mensagens = []

    bloco = [
        titulo_tabela,
        separador
    ]

    for linha in linhas:

        teste = bloco + [linha]

        mensagem_teste = (
            cabecalho
            + "\n<pre>"
            + escape("\n".join(teste))
            + "</pre>"
        )

        # Mantém uma margem de segurança para o limite do Telegram
        if len(mensagem_teste) > 3900 and len(bloco) > 2:

            mensagem = (
                cabecalho
                + "\n<pre>"
                + escape("\n".join(bloco))
                + "</pre>"
            )

            mensagens.append(mensagem)

            bloco = [
                titulo_tabela,
                separador
            ]

        bloco.append(linha)

    # Adiciona o último bloco
    if len(bloco) > 2:

        mensagem = (
            cabecalho
            + "\n<pre>"
            + escape("\n".join(bloco))
            + "</pre>"
        )

        mensagens.append(mensagem)

    return mensagens


# ============================================================
# ENVIO DAS MENSAGENS AO TELEGRAM
# ============================================================

def enviar_telegram(mensagem):

    url = f"{TELEGRAM_API}/bot{TOKEN}/sendMessage"

    dados = {
        "chat_id": CHAT_ID,
        "text": mensagem,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    resposta = requests.post(
        url,
        data=dados,
        timeout=30
    )

    resposta.raise_for_status()

    resultado = resposta.json()

    if not resultado.get("ok"):
        raise RuntimeError(
            f"Erro ao enviar mensagem: {resultado}"
        )

    print("Mensagem enviada com sucesso!")


# ============================================================
# EXECUÇÃO PRINCIPAL
# ============================================================

def main():

    print("=" * 50)
    print("AGENDA DE DIVIDENDOS")
    print("=" * 50)

    # Referência da execução
    referencia = datetime.now().strftime("%m/%Y")

    # Busca os proventos
    proventos = buscar_proventos()

    # Gera as mensagens em formato de tabela
    mensagens = gerar_mensagens(
        proventos,
        referencia
    )

    print(f"Quantidade de mensagens: {len(mensagens)}")

    # Envia todas as partes ao Telegram
    for indice, mensagem in enumerate(mensagens, start=1):

        print(
            f"Enviando mensagem "
            f"{indice}/{len(mensagens)}..."
        )

        enviar_telegram(mensagem)

    print("=" * 50)
    print("PROCESSAMENTO CONCLUÍDO!")
    print("=" * 50)


if __name__ == "__main__":
    main()
