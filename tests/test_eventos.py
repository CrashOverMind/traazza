"""Tests del registro de eventos (F2.2)."""

from traazza.eventos import RegistroEventos, TipoEvento


def test_eventos_se_encadenan():
    log = RegistroEventos()
    e1 = log.registrar(TipoEvento.INICIO_OPERACION, "arranque",
                       marca_tiempo="2024-01-01T10:00:00+01:00")
    e2 = log.registrar(TipoEvento.GENERACION_REGISTRO, "factura 2024/A-1",
                       marca_tiempo="2024-01-01T10:01:00+01:00")
    assert e1.huella_anterior == ""
    assert e2.huella_anterior == e1.huella
    assert log.ultima_huella == e2.huella
    assert len(e1.huella) == 64  # SHA-256 hex


def test_verificar_cadena_intacta():
    log = RegistroEventos()
    for i in range(5):
        log.registrar(TipoEvento.GENERACION_REGISTRO, f"factura {i}",
                      marca_tiempo=f"2024-01-01T10:0{i}:00+01:00")
    assert log.verificar() is True


def test_verificar_detecta_manipulacion():
    log = RegistroEventos()
    log.registrar(TipoEvento.INICIO_OPERACION, "ok",
                  marca_tiempo="2024-01-01T10:00:00+01:00")
    log.registrar(TipoEvento.INCIDENCIA, "algo",
                  marca_tiempo="2024-01-01T10:01:00+01:00")
    # Manipular el detalle de un evento ya registrado rompe la cadena.
    log.eventos[0].detalle = "manipulado"
    log._eventos[0].detalle = "manipulado"
    assert log.verificar() is False


def test_a_dicts_serializa():
    log = RegistroEventos()
    log.registrar(TipoEvento.EXPORTACION, "export csv",
                  marca_tiempo="2024-01-01T10:00:00+01:00")
    d = log.a_dicts()[0]
    assert d["tipo"] == "Exportacion"
    assert d["detalle"] == "export csv"
    assert "huella" in d
