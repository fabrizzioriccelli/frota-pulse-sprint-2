#!/usr/bin/env python3
"""Compila o firmware do ESP32 para o computador (modo lote) e grava a telemetria simulada em CSV.

O mesmo arquivo src/esp32/firmware/telemetria_frota/telemetria_frota.ino roda no Wokwi (modos SENSORES e ROTEIRO) e
aqui, compilado com g++ e uma camada mínima da API Arduino (src/esp32/nativo/). O gerador pseudoaleatório é próprio
do firmware, então a sequência de leituras é a mesma nos dois ambientes.

Saídas:
  data/telemetria/telemetria_esp32.csv              60 leituras por veículo-mês (perfis_lote.h)
  docs/evidencias/monitor_serial_demo.txt   saída dos 3 perfis de demonstração do Wokwi

Requer g++ (C++17). Uso:
    python src/simulacao/gerar_telemetria.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from frota_pulse.config import RAIZ, TELEMETRIA  # noqa: E402

ESP32 = RAIZ / "src" / "esp32"
FIRMWARE = ESP32 / "firmware" / "telemetria_frota"
EVIDENCIAS = RAIZ / "docs" / "evidencias"


def compilar_e_executar(flags: list[str]) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "telemetria"
        cmd = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-DNATIVO", *flags, "-I", str(ESP32 / "nativo"),
               "-I", str(FIRMWARE), "-x", "c++", str(FIRMWARE / "telemetria_frota.ino"), "-x", "none",
               str(ESP32 / "nativo" / "main.cpp"), "-o", str(exe)]
        subprocess.run(cmd, check=True)
        return subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout


def main() -> None:
    TELEMETRIA.mkdir(parents=True, exist_ok=True)
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    lote = compilar_e_executar(["-DMODO_LOTE"])
    (TELEMETRIA / "telemetria_esp32.csv").write_text(lote, encoding="utf-8")
    demo = compilar_e_executar(["-DMODO_LOTE", "-DPERFIS_DEMO"])
    (EVIDENCIAS / "monitor_serial_demo.txt").write_text(
        "# Saída do firmware para os 3 perfis de demonstração do Wokwi (compilação nativa, modo lote).\n"
        "# Mesmo formato que o Monitor Serial do Wokwi mostra no modo ROTEIRO.\n" + demo, encoding="utf-8")
    print(f"ok: {lote.count(chr(10)) - 1} leituras em data/telemetria/telemetria_esp32.csv; "
          f"{demo.count(chr(10)) - 1} leituras de demonstração")


if __name__ == "__main__":
    main()
