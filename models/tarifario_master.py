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

    # Naviera (solo con etiqueta Naviera)
    naviera_id = fields.Many2one(
        'res.partner',
        string='Naviera',
        domain="[('category_id.name', '=', 'Naviera')]"
    )

    # Ubicaciones (con etiquetas POL y POD)
    pol_id = fields.Many2one(
        'res.partner',
        string='Puerto Carga (POL)',
        required=True,
        domain="[('category_id.name', '=', 'POL')]"
    )
    pod_id = fields.Many2one(
        'res.partner',
        string='Puerto Destino (POD)',
        required=True,
        domain="[('category_id.name', '=', 'POD')]"
    )

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
    costo_exw = fields.Monetary(string='Costo EXW')
    ocean_freight = fields.Monetary(string='Ocean Freight')
    ams_imo = fields.Monetary(string='AMS + IMO')
    lib_seguro = fields.Monetary(string='Lib + Seguro')
    all_in = fields.Monetary(string='Total ALL IN', compute='_compute_all_in', store=True)

    # Tiempos
    transit_time = fields.Integer(string='Transit Time (días)', help='Tiempo estimado de tránsito en días')
    demoras = fields.Integer(string='Demoras (días)', help='Free time / días libres de demurrage')

    # Equipo
    equipo = fields.Selection([
        # Dry / Standard (GP)
        ('20st',  "20' ST (Dry/GP)"),
        ('40st',  "40' ST (Dry/GP)"),
        ('40hc',  "40' HC (High Cube Dry)"),
        ('45hc',  "45' HC (High Cube Dry)"),
        ('53st',  "53' ST (North America)"),
        ('53hc',  "53' HC (North America)"),

        # Reefer
        ('20rf',  "20' RF (Reefer)"),
        ('40rf',  "40' RF (Reefer)"),
        ('40rh',  "40' RH / 40' HC RF (High Cube Reefer)"),
        ('nor',   "NOR (Non-Operating Reefer)"),

        # Open Top
        ('20ot',  "20' OT (Open Top)"),
        ('40ot',  "40' OT (Open Top)"),

        # Flat Rack / Platform
        ('20fr',  "20' FR (Flat Rack)"),
        ('40fr',  "40' FR (Flat Rack)"),
        ('20pl',  "20' PL (Platform)"),
        ('40pl',  "40' PL (Platform)"),

        # Tank
        ('20tk',  "20' TK (Tank)"),

        # Special
        ('20ht',  "20' HT (Hard Top)"),
        ('40ht',  "40' HT (Hard Top)"),
        ('20vh',  "20' VH (Ventilated)"),
        ('40pw',  "40' PW (Pallet Wide)"),
        ('45pwhc',"45' PW HC (Pallet Wide High Cube)"),

        # Services
        ('lcl',   "LCL (Less than Container Load)"),
        ('bbk',   "BBK (Breakbulk / Suelta)"),
        ('roro',  "RoRo (Roll-on/Roll-off)"),
    ], string='Equipo', required=True, default='20st')

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
                rec.pol_id.name or '',
                rec.pod_id.name or '',
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

    def _get_or_create_tag(self, tag_name):
        """Obtiene o crea una etiqueta de contacto"""
        tag = self.env['res.partner.category'].search([('name', '=', tag_name)], limit=1)
        if not tag:
            tag = self.env['res.partner.category'].create({'name': tag_name})
        return tag

    def _assign_tag_to_partner(self, partner_id, tag):
        """Asigna una etiqueta a un contacto si no la tiene"""
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if tag.id not in partner.category_id.ids:
                partner.write({'category_id': [(4, tag.id)]})

    @api.model_create_multi
    def create(self, vals_list):
        tags = {
            'forwarder_id': self._get_or_create_tag('Forwarder'),
            'naviera_id': self._get_or_create_tag('Naviera'),
            'pol_id': self._get_or_create_tag('POL'),
            'pod_id': self._get_or_create_tag('POD'),
        }

        for vals in vals_list:
            for field, tag in tags.items():
                self._assign_tag_to_partner(vals.get(field), tag)

        return super().create(vals_list)

    def write(self, vals):
        field_tag_map = {
            'forwarder_id': 'Forwarder',
            'naviera_id': 'Naviera',
            'pol_id': 'POL',
            'pod_id': 'POD',
        }

        for field, tag_name in field_tag_map.items():
            if vals.get(field):
                tag = self._get_or_create_tag(tag_name)
                self._assign_tag_to_partner(vals[field], tag)

        return super().write(vals)