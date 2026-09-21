"""Build the reviewed Top 100 company-payments snapshot used by the public API."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from io import TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen
from zipfile import ZipFile

import httpx

EXCLUDED_NATURES = (
    "ADMINISTRAÇÃO PÚBLICA",
    "ADMINISTRACAO PUBLICA",
    "ASSOCIAÇÃO PRIVADA",
    "ASSOCIACAO PRIVADA",
    "FUNDAÇÃO PRIVADA",
    "FUNDACAO PRIVADA",
    "ORGANIZAÇÃO RELIGIOSA",
    "ORGANIZACAO RELIGIOSA",
    "PARTIDO POLÍTICO",
    "PARTIDO POLITICO",
    "SINDICATO",
    "CONDOMÍNIO",
    "CONDOMINIO",
)


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def money(value: str) -> Decimal:
    clean = re.sub(r"[^0-9,.-]", "", value or "0")
    return Decimal(clean.replace(".", "").replace(",", "."))


def pick(row: dict[str, str], *names: str) -> str:
    folded = {re.sub(r"\W", "", key).casefold(): value for key, value in row.items()}
    for name in names:
        value = folded.get(re.sub(r"\W", "", name).casefold())
        if value is not None:
            return value
    return ""


def cnpj_label(value: str) -> str:
    return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"


def download(year: int, target: Path) -> None:
    url = f"https://portaldatransparencia.gov.br/download-de-dados/despesas-favorecidos/{year}"
    request = Request(url, headers={"User-Agent": "PuxandoACapivara/1.0"})
    with urlopen(request, timeout=180) as response, target.open("wb") as output:
        while block := response.read(1024 * 1024):
            output.write(block)


def aggregate(archive_path: Path) -> tuple[dict[str, Decimal], dict[str, str]]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    names: dict[str, str] = {}
    with ZipFile(archive_path) as archive:
        csv_name = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        with TextIOWrapper(archive.open(csv_name), encoding="latin-1") as stream:
            for row in csv.DictReader(stream, delimiter=";"):
                cnpj = digits(pick(row, "Código Favorecido", "codigoPessoa"))
                name = pick(row, "Nome Favorecido", "nomePessoa").strip()
                if len(cnpj) != 14 or not name:
                    continue
                totals[cnpj] += money(pick(row, "Valor Recebido", "valor"))
                names[cnpj] = name
    return totals, names


def company_details(client: httpx.Client, cnpj: str) -> tuple[str, str] | None:
    response = client.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", timeout=30)
    if response.status_code != 200:
        return None
    data = response.json()
    nature = str(data.get("descricao_natureza_juridica") or "").upper()
    if any(term in nature for term in EXCLUDED_NATURES):
        return None
    sector = str(data.get("cnae_fiscal_descricao") or "Atividade não informada").strip()
    return sector, nature


def build(year: int, output: Path) -> None:
    with NamedTemporaryFile(suffix=".zip", delete=False) as temporary:
        archive_path = Path(temporary.name)
    try:
        download(year, archive_path)
        totals, names = aggregate(archive_path)
    finally:
        archive_path.unlink(missing_ok=True)
    candidates = sorted(totals, key=lambda cnpj: (-totals[cnpj], names[cnpj]))
    entries = []
    with httpx.Client(headers={"User-Agent": "PuxandoACapivara/1.0"}) as client:
        for cnpj in candidates[:1000]:
            details = company_details(client, cnpj)
            if details is None:
                continue
            sector, _nature = details
            entries.append(
                {
                    "name": names[cnpj],
                    "cnpj": cnpj_label(cnpj),
                    "sector": sector,
                    "value": str(totals[cnpj]),
                }
            )
            if len(entries) == 100:
                break
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "year": year,
                "source_as_of": datetime.now(UTC).date().isoformat(),
                "covered": len(totals),
                "entries": entries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    selected_year = int(sys.argv[1])
    filename = f"company_payments_{selected_year}.json"
    destination = Path(__file__).parents[1] / "app" / "data" / filename
    build(selected_year, destination)
