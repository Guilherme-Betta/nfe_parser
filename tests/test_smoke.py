"""Teste de fumaca — mantem o CI verde antes do primeiro componente."""

import nfe_parser


def test_pacote_importa():
    assert nfe_parser.__version__
