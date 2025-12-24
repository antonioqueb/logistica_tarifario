from odoo import models, fields, api

class FreightTariff(models.Model):
    _name = 'freight.tariff'
    _description = 'Tarifario de Fletes'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    active = fields.Boolean(default=True)
    
    # Relaciones
    forwarder_id = fields.Many2one('res.partner', string='Forwarder', required=True)
    naviera_id = fields.Many2one('res.partner', string='Naviera')
    
    # Ubicaciones
    pol_id = fields.Char(string='Puerto Carga (POL)', required=True)
    pod_id = fields.Char(string='Puerto Destino (POD)', required=True)
    
    # Costos
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.ref('base.USD'))
    ocean_freight = fields.Monetary(string='Ocean Freight')
    ams_imo = fields.Monetary(string='AMS + IMO')
    lib_seguro = fields.Monetary(string='Lib + Seguro')
    all_in = fields.Monetary(string='Total ALL IN', compute='_compute_all_in', store=True)
    
    # Logística
    equipo = fields.Selection([
        ('20', "20' ST"), ('40', "40' ST"), ('40hc', "40' HC"), ('lcl', "LCL")
    ], string='Equipo', required=True, default='20')
    
    vigencia_fin = fields.Date(string='Vigencia Hasta', required=True)
    fecha_tarifa = fields.Date(string='Fecha Tarifa', default=fields.Date.context_today)
    
    # Campos de Periodo (Importantes para la búsqueda)
    anio = fields.Char(string='Año', compute='_compute_periodo', store=True)
    mes = fields.Selection([
        ('01', 'Ene'), ('02', 'Feb'), ('03', 'Mar'), ('04', 'Abr'),
        ('05', 'May'), ('06', 'Jun'), ('07', 'Jul'), ('08', 'Ago'),
        ('09', 'Sep'), ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dic')
    ], string='Mes', compute='_compute_periodo', store=True)

    state = fields.Selection([
        ('active', 'Vigente'),
        ('expired', 'Expirada')
    ], string='Estado', default='active', compute='_compute_state', store=True)

    @api.depends('forwarder_id', 'pol_id', 'pod_id', 'fecha_tarifa')
    def _compute_name(self):
        for rec in self:
            date_str = rec.fecha_tarifa.strftime('%Y-%m') if rec.fecha_tarifa else ''
            rec.name = f"{rec.forwarder_id.name or ''} | {rec.pol_id or ''}-{rec.pod_id or ''} ({date_str})"

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
            else:
                rec.anio = False
                rec.mes = False

    @api.depends('vigencia_fin')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.vigencia_fin and rec.vigencia_fin < today:
                rec.state = 'expired'
            else:
                rec.state = 'active'