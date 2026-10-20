import sys
from pathlib import Path

from services.auditoria import localizar_archivos_por_patron, resolver_ruta_base
from processors.historico import cargar_historico


def test_resolver_ruta_base_usa_directorio_del_ejecutable(monkeypatch, tmp_path):
    exe = tmp_path / "dist" / "MacroControlesGlucoV2.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.touch()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "bundle", raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)

    assert resolver_ruta_base() == exe.parent


def test_localizar_archivos_por_patron_acepta_sufijo_fecha(tmp_path):
    carpeta = tmp_path / "data"
    carpeta.mkdir()
    (carpeta / "044_2024_01_01.xlsx").touch()
    (carpeta / "077_2024_01_02.xlsb").touch()
    (carpeta / "Historico_Documentos_Controlados_2024_01_01.xlsb").touch()

    assert localizar_archivos_por_patron(carpeta, "044")
    assert localizar_archivos_por_patron(carpeta, "077")
    assert localizar_archivos_por_patron(carpeta, "Historico_Documentos_Controlados")


def test_cargar_historico_usa_fallback_csv_cuando_falta_pyxlsb(tmp_path, monkeypatch):
    carpeta = tmp_path / "data"
    carpeta.mkdir()
    xlsb = carpeta / "Historico_Documentos_Controlados.xlsb"
    xlsb.touch()
    csv_fallback = carpeta / "Historico_Documentos_Controlados_fallback.csv"
    csv_fallback.write_text("id_largo,id_corto\nA1,1\n", encoding="utf-8")

    original_read_excel = __import__("pandas").read_excel

    def fake_read_excel(path, *args, **kwargs):
        if str(path) == str(xlsb):
            raise ImportError("Import pyxlsb failed. Use pip or conda to install the pyxlsb package.")
        return original_read_excel(path, *args, **kwargs)

    monkeypatch.setattr("pandas.read_excel", fake_read_excel)

    df = cargar_historico(xlsb)
    assert list(df.columns) == ["id_largo", "id_corto"]
    row = df.iloc[0].to_dict()
    assert row["id_largo"] == "A1"
    assert int(row["id_corto"]) == 1
