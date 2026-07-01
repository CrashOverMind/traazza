"""Tests de la CLI (F3.2)."""

import json

import pytest

from traazza.cli import main

FACTURAS = {
    "emisor": {"nif": "89890001K", "nombre": "Empresa Ejemplo SL"},
    "sistema": {"nombre_razon": "Mi Software SL", "nif": "B00000000",
                "nombre_sif": "MiFacturador", "id_sif": "01",
                "version": "1.0.0", "numero_instalacion": "INST-001"},
    "facturas": [
        {"tipo": "alta", "num_serie": "2024/A-1", "fecha_expedicion": "01-01-2024",
         "tipo_factura": "F1", "cuota_total": "21.00", "importe_total": "121.00",
         "fecha_hora_huso": "2024-01-01T10:00:00+01:00",
         "descripcion_operacion": "Venta",
         "desglose": [{"base_imponible": "100.00", "cuota_repercutida": "21.00",
                       "tipo_impositivo": "21.00"}]},
        {"tipo": "anulacion", "num_serie": "2024/A-0",
         "fecha_expedicion": "01-01-2024",
         "fecha_hora_huso": "2024-01-01T10:05:00+01:00"},
    ],
}


@pytest.fixture
def json_facturas(tmp_path):
    ruta = tmp_path / "facturas.json"
    ruta.write_text(json.dumps(FACTURAS), encoding="utf-8")
    return str(ruta)


def test_qr_imprime_url(capsys):
    codigo = main(["qr", "--nif", "89890001K", "--numserie", "2024/A-1",
                   "--fecha", "01-01-2024", "--importe", "121.00"])
    out = capsys.readouterr().out
    assert codigo == 0
    assert "ValidarQR?nif=89890001K" in out
    assert "numserie=2024%2FA-1" in out


def test_qr_no_verificable(capsys):
    main(["qr", "--nif", "89890001K", "--numserie", "A1",
          "--fecha", "01-01-2024", "--importe", "10.00", "--no-verificable"])
    assert "ValidarQRNoVerifactu" in capsys.readouterr().out


def test_cadena(capsys, json_facturas):
    codigo = main(["cadena", json_facturas])
    out = capsys.readouterr().out
    assert codigo == 0
    assert "Alta" in out and "Anulacion" in out
    # dos huellas SHA-256 (64 hex) distintas
    huellas = [w for w in out.split() if len(w) == 64]
    assert len(huellas) == 2 and huellas[0] != huellas[1]


def test_xml(capsys, json_facturas):
    main(["xml", json_facturas, "--indice", "0"])
    out = capsys.readouterr().out
    assert "RegistroAlta" in out and "DescripcionOperacion" in out


def test_envoltorio(capsys, json_facturas):
    main(["envoltorio", json_facturas])
    assert "RegFactuSistemaFacturacion" in capsys.readouterr().out


def test_validar_envoltorio_ok(capsys, json_facturas, tmp_path):
    ruta = tmp_path / "env.xml"
    main(["envoltorio", json_facturas])
    ruta.write_text(capsys.readouterr().out, encoding="utf-8")
    codigo = main(["validar", str(ruta), "--envoltorio"])
    assert codigo == 0
    assert "VÁLIDO" in capsys.readouterr().out


def test_validar_detecta_error(capsys, json_facturas, tmp_path):
    ruta = tmp_path / "reg.xml"
    main(["xml", json_facturas, "--indice", "0"])
    roto = capsys.readouterr().out.replace("F1", "ZZ")
    ruta.write_text(roto, encoding="utf-8")
    codigo = main(["validar", str(ruta)])
    assert codigo == 1
    assert "NO válido" in capsys.readouterr().out
