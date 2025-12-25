from odoo import models, fields, api
from datetime import date


class FreightTariff(models.Model):
    _name = 'freight.tariff'
    _description = 'Tarifario de Fletes'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    active = fields.Boolean(default=True)

    # País
    country_id = fields.Many2one('res.country', string='País', required=True)

    # Forwarder (solo con etiqueta Forwarder)
    forwarder_id = fields.Many2one(
        'res.partner',
        string='Forwarder',
        required=True,
        domain="[('category_id.name', '=', 'Forwarder')]"
    )

    # Naviera
    naviera_id = fields.Many2one('res.partner', string='Naviera')

    # Ubicaciones
    pol_id = fields.Char(string='Puerto Carga (POL)', required=True)
    pod_id = fields.Char(string='Puerto Destino (POD)', required=True)

    # Periodo
    anio = fields.Char(
        string='Año',
        required=True,
        default=lambda self: str(date.today().year)
    )
    mes = fields.Selection([
        ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'),
        ('05', 'Mayo'), ('06', 'Junio'), ('07', 'Julio'), ('08', 'Agosto'),
        ('09', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string='Mes', required=True, default=lambda self: str(date.today().month).zfill(2))

    # Costos
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.ref('base.USD')
    )
    ocean_freight = fields.Monetary(string='Ocean Freight')
    ams_imo = fields.Monetary(string='AMS + IMO')
    lib_seguro = fields.Monetary(string='Lib + Seguro')
    all_in = fields.Monetary(string='Total ALL IN', compute='_compute_all_in', store=True)

    # Tiempos
    transit_time = fields.Integer(string='Transit Time (días)', help='Tiempo estimado de tránsito en días')
    demoras = fields.Integer(string='Demoras (días)', help='Free time / días libres de demurrage')

    # Equipo
    equipo = fields.Selection([
        ('20', "20' ST"), ('40', "40' ST"), ('40hc', "40' HC"), ('lcl', "LCL")
    ], string='Equipo', required=True, default='20')

    state = fields.Selection([
        ('active', 'Vigente'),
        ('expired', 'Expirada')
    ], string='Estado', default='active', compute='_compute_state', store=True)

    @api.depends('country_id', 'forwarder_id', 'pol_id', 'pod_id', 'anio')
    def _compute_name(self):
        for rec in self:
            parts = [
                rec.country_id.name or '',
                rec.forwarder_id.name or '',
                rec.pol_id or '',
                rec.pod_id or '',
                rec.anio or ''
            ]
            rec.name = ' | '.join(filter(None, parts))

    @api.depends('ocean_freight', 'ams_imo')
    def _compute_all_in(self):
        for rec in self:
            rec.all_in = (rec.ocean_freight or 0.0) + (rec.ams_imo or 0.0)

    @api.depends('anio', 'mes')
    def _compute_state(self):
        today = date.today()
        current_year = today.year
        current_month = today.month
        for rec in self:
            if rec.anio and rec.mes:
                try:
                    tariff_year = int(rec.anio)
                    tariff_month = int(rec.mes)
                    if tariff_year < current_year or (tariff_year == current_year and tariff_month < current_month):
                        rec.state = 'expired'
                    else:
                        rec.state = 'active'
                except ValueError:
                    rec.state = 'active'
            else:
                rec.state = 'active'

    @api.model_create_multi
    def create(self, vals_list):
        tag = self.env['res.partner.category'].search([('name', '=', 'Forwarder')], limit=1)
        if not tag:
            tag = self.env['res.partner.category'].create({'name': 'Forwarder'})

        for vals in vals_list:
            if vals.get('forwarder_id'):
                partner = self.env['res.partner'].browse(vals['forwarder_id'])
                if tag.id not in partner.category_id.ids:
                    partner.write({'category_id': [(4, tag.id)]})

        return super().create(vals_list)

    def write(self, vals):
        if vals.get('forwarder_id'):
            tag = self.env['res.partner.category'].search([('name', '=', 'Forwarder')], limit=1)
            if not tag:
                tag = self.env['res.partner.category'].create({'name': 'Forwarder'})
            partner = self.env['res.partner'].browse(vals['forwarder_id'])
            if tag.id not in partner.category_id.ids:
                partner.write({'category_id': [(4, tag.id)]})

        return super().write(vals)