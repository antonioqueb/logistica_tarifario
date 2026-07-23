# -*- coding: utf-8 -*-
"""Inicializa la activación de costeo: las compras YA recibidas (histórico)
cuentan para el promedio ponderado desde el arranque."""


def migrate(cr, version):
    cr.execute("""
        UPDATE purchase_order_line
           SET som_costing_activated = true
         WHERE qty_received > 0
           AND (som_costing_activated IS NULL OR som_costing_activated = false)
    """)
