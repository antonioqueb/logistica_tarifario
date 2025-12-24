from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

class FreightTariff(models.Model):
    _name = 'freight.tariff'
    _description = 'Tarifario Global de Fletes'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    active = fields.Boolean(default=True)
    
    # Relaciones Master Data
    forwarder_id = fields.Many2one('res.partner', string='Forwarder', required=True, domain=[('is_company', '=', True)])
    naviera_id = fields.Many2one('res.partner', string='Naviera', domain=[('is_company', '=', True)])
    
    # Ubicaciones
    pais_origen = fields.Many2one('res.country', string='País Origen')
    pol_id = fields.Char(string='POL (Puerto de Carga)', required=True)
    pod_id = fields.Char(string='POD (Puerto de Destino)', required=True)
    
    # Costos y Precios
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.ref('base.USD'))
    ocean_freight = fields.Monetary(string='OF (Ocean Freight)')
    costo_exw = fields.Monetary(string='Costo EXW')
    ams_imo = fields.Monetary(string='AMS + IMO')
    lib_seguro = fields.Monetary(string='Lib. + Seguro')
    all_in = fields.Monetary(string='ALL IN TOTAL', compute='_compute_all_in', store=True)
    
    # Logística
    equipo = fields.Selection([
        ('20', "20' Standard"),
        ('40', "40' Standard"),
        ('40hc', "40' High Cube"),
        ('lcl', "LCL")
    ], string='Tipo de Equipo', required=True, default='20')
    
    tt = fields.Integer(string='TT (Transit Time Días)')
    demoras = fields.Integer(string='Días de Demoras Libres')
    vigencia_fin = fields.Date(string='Vigencia Hasta', required=True)
    
    # Periodos para Reportería
    fecha_tarifa = fields.Date(string='Fecha Aplicación', default=fields.Date.context_today)
    anio = fields.Char(string='Año', compute='_compute_periodo', store=True)
    mes = fields.Selection([
        ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'),
        ('05', 'Mayo'), ('06', 'Junio'), ('07', 'Julio'), ('08', 'Agosto'),
        ('09', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string='Mes', compute='_compute_periodo', store=True)

    nota = fields.Text(string='Observaciones Internas')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Vigente'),
        ('expired', 'Expirada')
    ], string='Estado', default='active', compute='_compute_state', store=True)

    @api.depends('forwarder_id', 'pol_id', 'pod_id', 'fecha_tarifa')
    def _compute_name(self):
        for rec in self:
            date_str = rec.fecha_tarifa.strftime('%Y-%m') if rec.fecha_tarifa else ''
            rec.name = f"{rec.forwarder_id.name or 'N/A'} | {rec.pol_id}-{rec.pod_id} ({date_str})"

    @api.depends('ocean_freight', 'ams_imo', 'lib_seguro')
    def _compute_all_in(self):
        for rec in self:
            rec.all_in = rec.ocean_freight + rec.ams_imo + rec.lib_seguro

    @api.depends('fecha_tarifa')
    def _compute_periodo(self):
        for rec in self:
            if rec.fecha_tarifa:
                rec.anio = str(rec.fecha_tarifa.year)
                rec.mes = str(rec.fecha_tarifa.month).zfill(2)

    @api.depends('vigencia_fin')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.vigencia_fin and rec.vigencia_fin < today:
                rec.state = 'expired'
            else:
                rec.state = 'active'
