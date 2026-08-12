# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FreightTariffNational(models.Model):
    """Tarifario NACIONAL: flete doméstico en MXN por ruta origen→destino.

    A diferencia del tarifario internacional (contenedor, USD, POL/POD,
    arancel), el nacional es un flete terrestre simple: país (México por
    default), origen, destino, costo en MXN por viaje y capacidad en m²
    por viaje. El motor de costos lo divide costo/capacidad para obtener
    la logística MXN/m² del ALL-IN nacional (sin arancel)."""
    _name = 'freight.tariff.national'
    _description = 'Tarifario Nacional (flete doméstico MXN)'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    active = fields.Boolean(default=True, tracking=True)

    country_id = fields.Many2one(
        'res.country', string='País', required=True,
        default=lambda self: self.env.ref('base.mx', raise_if_not_found=False),
    )
    origen = fields.Char(string='Origen', required=True, tracking=True)
    destino = fields.Char(string='Destino', required=True, tracking=True)

    currency_id = fields.Many2one(
        'res.currency', string='Moneda',
        default=lambda self: self.env.ref('base.MXN', raise_if_not_found=False),
        readonly=True,
    )
    costo = fields.Monetary(
        string='Costo (MXN)', required=True, tracking=True,
        help='Costo del flete nacional por viaje, en MXN.',
    )
    capacidad = fields.Float(
        string='Capacidad (m²)', tracking=True,
        help='m² que carga el viaje. El costo por m² = Costo ÷ Capacidad. '
             'Si se deja en 0, el motor usa la capacidad del producto.',
    )
    transit_time = fields.Integer(string='Transit Time (días)')
    notas = fields.Text(string='Notas')

    @api.depends('origen', 'destino', 'costo')
    def _compute_name(self):
        for rec in self:
            rec.name = '%s → %s' % (rec.origen or '?', rec.destino or '?')


class ProductTemplateNationalFreight(models.Model):
    _inherit = 'product.template'

    # Modo de flete del producto: el motor ALL-IN calcula la logística con
    # el tarifario que corresponda.
    x_freight_mode = fields.Selection([
        ('international', 'Internacional (contenedor USD)'),
        ('national', 'Nacional (flete MXN)'),
    ], string='Tipo de flete', default='international',
       help='Internacional: País/POL/POD + tarifa USD por contenedor + '
            'arancel. Nacional: ruta doméstica del Tarifario Nacional en '
            'MXN, sin arancel.')
    x_national_route_id = fields.Many2one(
        'freight.tariff.national',
        string='Ruta nacional',
        domain="[('active', '=', True)]",
        help='Ruta del Tarifario Nacional que paga este producto.',
    )
