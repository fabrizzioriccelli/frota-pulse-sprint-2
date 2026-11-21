import json
import subprocess
import sys

from frota_pulse.config import GRAFICOS, PREVISOES, PROCESSADOS, RAIZ, RELATORIOS


def test_pipeline_completo_gera_as_saidas():
    r = subprocess.run([sys.executable, str(RAIZ / "src" / "executar_pipeline.py")], capture_output=True, text=True,
                       check=True)
    assert "[10] Regras x modelo" in r.stdout
    for p in (PROCESSADOS / "base_consolidada_veiculo_mes.csv", PROCESSADOS / "custos_tratados.csv",
              RELATORIOS / "relatorio_qualidade.csv", RELATORIOS / "benchmark_grupos.csv",
              RELATORIOS / "comparacao_regras_ml.csv", PREVISOES / "metricas_modelo.json"):
        assert p.exists() and p.stat().st_size > 0, p
    assert len(list(GRAFICOS.glob("*.png"))) == 7
    m = json.loads((PREVISOES / "metricas_modelo.json").read_text(encoding="utf-8"))
    assert m["tamanhos"]["teste"] > 0
