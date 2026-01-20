from odoo import models, fields, api
from datetime import date, timedelta
from collections import defaultdict


class FreightTariffMonth(models.Model):
    """Modelo auxiliar para seleccionar múltiples meses"""
    _name = 'freight.tariff.month'
    _description = 'Meses del Tarifario'
    _order = 'sequence, id'

    name = fields.Char(string='Mes', required=True)
    code = fields.Char(string='Código', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)


class FreightTariff(models.Model):
    _name = 'freight.tariff'
    _description = 'Tarifario de Fletes'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    active = fields.Boolean(default=True)

    # ==========================
    # UBICACIÓN Y ENTIDADES
    # ==========================
    country_id = fields.Many2one('res.country', string='País', required=True)

    forwarder_id = fields.Many2one(
        'res.partner',
        string='Forwarder',
        required=True,
        domain="[('category_id.name', '=', 'Forwarder')]"
    )

    naviera_id = fields.Many2one(
        'res.partner',
        string='Naviera',
        domain="[('category_id.name', '=', 'Naviera')]"
    )

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

    # ==========================
    # VIGENCIA (NUEVA LÓGICA)
    # ==========================
    anio = fields.Char(
        string='Año',
        required=True,
        default=lambda self: str(date.today().year)
    )
    
    # Selección múltiple de meses
    mes_ids = fields.Many2many(
        'freight.tariff.month',
        string='Meses de Vigencia',
        required=True
    )

    # Campo técnico calculado para mantener compatibilidad con Dashboard SQL
    # Guarda el código del primer mes seleccionado (ej: '01')
    mes = fields.Selection([
        ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'),
        ('05', 'Mayo'), ('06', 'Junio'), ('07', 'Julio'), ('08', 'Agosto'),
        ('09', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string='Mes Principal', compute='_compute_mes_legacy', store=True)

    # ==========================
    # COSTOS (ACTUALIZADO)
    # ==========================
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.ref('base.USD')
    )
    
    # Grupo 1: Origen / Flete
    costo_exw = fields.Monetary(string='Costo EXW')
    ocean_freight = fields.Monetary(string='Ocean Freight')
    
    # Grupo 2: Recargos
    ams_imo = fields.Monetary(string='AMS + IMO')
    lib_seguro = fields.Monetary(string='Lib + Seguro')
    
    # Grupo 3: Nuevos Campos Solicitados
    maniobras = fields.Monetary(string='Maniobras')
    vacio_lavado = fields.Monetary(string='Vacío + Lavado')
    aa = fields.Monetary(string='AA (Agencia/Otros)')
    flete_terrestre = fields.Monetary(string='Flete Terrestre')

    # Sumatoria Total
    all_in = fields.Monetary(string='Total ALL IN', compute='_compute_all_in', store=True)

    # ==========================
    # DATOS OPERATIVOS
    # ==========================
    transit_time = fields.Integer(string='Transit Time (días)', help='Tiempo estimado de tránsito en días')
    demoras = fields.Integer(string='Demoras (días)', help='Free time / días libres de demurrage')

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
        # Others
        ('20tk',  "20' TK (Tank)"),
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

    notes = fields.Text(string="Comentarios / Notas")

    state = fields.Selection([
        ('active', 'Vigente'),
        ('expired', 'Expirada')
    ], string='Estado', default='active', compute='_compute_state', store=True)

    # ==========================
    # CAMPOS COMPUTADOS KPI
    # ==========================
    ruta_completa = fields.Char(
        string='Ruta', 
        compute='_compute_ruta_completa', 
        store=True,
        help='POL → POD'
    )
    costo_total_logistico = fields.Monetary(
        string='Costo Total Logístico',
        related='all_in',
        store=True,
        help='Es igual al All In en esta configuración'
    )
    margen_estimado = fields.Float(
        string='% Extras sobre Ocean',
        compute='_compute_margen',
        store=True,
        help='Porcentaje de costos adicionales sobre Ocean Freight'
    )

    # ==========================
    # MÉTODOS COMPUTE
    # ==========================

    @api.depends('mes_ids')
    def _compute_mes_legacy(self):
        """Calcula el mes principal para compatibilidad con búsquedas SQL del dashboard"""
        for rec in self:
            if rec.mes_ids:
                # Ordenar por código (01, 02...) y tomar el primero
                sorted_months = rec.mes_ids.sorted(key=lambda m: m.code)
                rec.mes = sorted_months[0].code
            else:
                rec.mes = False

    @api.depends('pol_id', 'pod_id')
    def _compute_ruta_completa(self):
        for rec in self:
            pol = rec.pol_id.name or '?'
            pod = rec.pod_id.name or '?'
            rec.ruta_completa = f"{pol} → {pod}"

    @api.depends(
        'costo_exw', 'ocean_freight', 'ams_imo', 'lib_seguro',
        'maniobras', 'vacio_lavado', 'aa', 'flete_terrestre'
    )
    def _compute_all_in(self):
        for rec in self:
            rec.all_in = (
                (rec.costo_exw or 0.0) +
                (rec.ocean_freight or 0.0) +
                (rec.ams_imo or 0.0) +
                (rec.lib_seguro or 0.0) +
                (rec.maniobras or 0.0) +
                (rec.vacio_lavado or 0.0) +
                (rec.aa or 0.0) +
                (rec.flete_terrestre or 0.0)
            )

    @api.depends('ocean_freight', 'all_in')
    def _compute_margen(self):
        for rec in self:
            if rec.ocean_freight:
                # Extras son todo lo que no es Ocean
                extras = rec.all_in - rec.ocean_freight
                rec.margen_estimado = (extras / rec.ocean_freight) * 100
            else:
                rec.margen_estimado = 0.0

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

    @api.depends('anio', 'mes_ids')
    def _compute_state(self):
        today = date.today()
        current_year = today.year
        current_month_code = str(today.month).zfill(2)
        
        for rec in self:
            if not rec.anio or not rec.mes_ids:
                rec.state = 'active'
                continue
            
            try:
                tariff_year = int(rec.anio)
                if tariff_year < current_year:
                    # Año pasado -> Expirado
                    rec.state = 'expired'
                elif tariff_year > current_year:
                    # Año futuro -> Vigente
                    rec.state = 'active'
                else:
                    # Año actual: Verificar si ALGUNO de los meses seleccionados
                    # es igual o posterior al mes actual.
                    codes = rec.mes_ids.mapped('code') # ej: ['01', '03']
                    is_active = False
                    for code in codes:
                        if code >= current_month_code:
                            is_active = True
                            break
                    
                    rec.state = 'active' if is_active else 'expired'
            except ValueError:
                rec.state = 'active'

    # =====================================================
    # MÉTODOS PARA DASHBOARD KPIs
    # =====================================================

    @api.model
    def get_dashboard_data(self):
        """Endpoint principal para obtener todos los KPIs del dashboard"""
        return {
            'resumen': self._get_resumen_general(),
            'promedios': self._get_promedios_activos(),
            'top_forwarders': self._get_top_forwarders(limit=5),
            'top_navieras': self._get_top_navieras(limit=5),
            'top_rutas': self._get_top_rutas(limit=5),
            'por_equipo': self._get_stats_por_equipo(),
            'por_pais': self._get_stats_por_pais(limit=5),
            'tendencia': self._get_tendencia_mensual(meses=12),
            'variaciones': self._get_variaciones_mensuales(),
            'alertas': self._get_alertas(),
            'comparativo_equipos': self._get_comparativo_equipos(),
        }

    @api.model
    def _get_resumen_general(self):
        return {
            'total': self.search_count([]),
            'activas': self.search_count([('state', '=', 'active')]),
            'expiradas': self.search_count([('state', '=', 'expired')]),
            'con_naviera': self.search_count([('naviera_id', '!=', False), ('state', '=', 'active')]),
            'sin_naviera': self.search_count([('naviera_id', '=', False), ('state', '=', 'active')]),
        }

    @api.model
    def _get_promedios_activos(self):
        tarifas = self.search([('state', '=', 'active')])
        if not tarifas:
            return {
                'all_in': 0, 'ocean_freight': 0, 'ams_imo': 0,
                'lib_seguro': 0, 'costo_exw': 0, 'transit_time': 0,
                'demoras': 0, 'costo_total': 0, 'margen_pct': 0
            }
        
        count = len(tarifas)
        return {
            'all_in': round(sum(t.all_in for t in tarifas) / count, 2),
            'ocean_freight': round(sum(t.ocean_freight or 0 for t in tarifas) / count, 2),
            'ams_imo': round(sum(t.ams_imo or 0 for t in tarifas) / count, 2),
            'lib_seguro': round(sum(t.lib_seguro or 0 for t in tarifas) / count, 2),
            'costo_exw': round(sum(t.costo_exw or 0 for t in tarifas) / count, 2),
            'transit_time': round(sum(t.transit_time or 0 for t in tarifas) / count, 1),
            'demoras': round(sum(t.demoras or 0 for t in tarifas) / count, 1),
            'costo_total': round(sum(t.all_in for t in tarifas) / count, 2),
            'margen_pct': round(sum(t.margen_estimado for t in tarifas) / count, 2),
        }

    @api.model
    def _get_top_forwarders(self, limit=5):
        data = self.read_group(
            [('state', '=', 'active')],
            ['forwarder_id', 'all_in:avg', 'ocean_freight:avg', 'transit_time:avg'],
            ['forwarder_id'],
            orderby='forwarder_id_count desc',
            limit=limit
        )
        return [{
            'id': d['forwarder_id'][0] if d['forwarder_id'] else False,
            'name': d['forwarder_id'][1] if d['forwarder_id'] else 'Sin asignar',
            'count': d.get('forwarder_id_count', 0),
            'avg_all_in': round(d.get('all_in', 0) or 0, 2),
            'avg_ocean': round(d.get('ocean_freight', 0) or 0, 2),
            'avg_transit': round(d.get('transit_time', 0) or 0, 1),
        } for d in data]

    @api.model
    def _get_top_navieras(self, limit=5):
        data = self.read_group(
            [('state', '=', 'active'), ('naviera_id', '!=', False)],
            ['naviera_id', 'all_in:avg', 'ocean_freight:avg'],
            ['naviera_id'],
            orderby='naviera_id_count desc',
            limit=limit
        )
        return [{
            'id': d['naviera_id'][0] if d['naviera_id'] else False,
            'name': d['naviera_id'][1] if d['naviera_id'] else 'Sin asignar',
            'count': d.get('naviera_id_count', 0),
            'avg_all_in': round(d.get('all_in', 0) or 0, 2),
            'avg_ocean': round(d.get('ocean_freight', 0) or 0, 2),
        } for d in data]

    @api.model
    def _get_top_rutas(self, limit=5):
        self.env.cr.execute("""
            SELECT 
                ft.pol_id, pol.name as pol_name, ft.pod_id, pod.name as pod_name,
                COUNT(*) as count, AVG(ft.all_in) as avg_all_in, AVG(ft.transit_time) as avg_transit
            FROM freight_tariff ft
            LEFT JOIN res_partner pol ON ft.pol_id = pol.id
            LEFT JOIN res_partner pod ON ft.pod_id = pod.id
            WHERE ft.state = 'active' AND ft.active = true
            GROUP BY ft.pol_id, pol.name, ft.pod_id, pod.name
            ORDER BY count DESC
            LIMIT %s
        """, (limit,))
        results = self.env.cr.dictfetchall()
        return [{
            'pol_id': r['pol_id'],
            'pol_name': r['pol_name'] or '?',
            'pod_id': r['pod_id'],
            'pod_name': r['pod_name'] or '?',
            'ruta': f"{r['pol_name'] or '?'} → {r['pod_name'] or '?'}",
            'count': r['count'],
            'avg_all_in': round(r['avg_all_in'] or 0, 2),
            'avg_transit': round(r['avg_transit'] or 0, 1),
        } for r in results]

    @api.model
    def _get_stats_por_equipo(self):
        data = self.read_group(
            [('state', '=', 'active')],
            ['equipo', 'all_in:avg', 'ocean_freight:avg'],
            ['equipo'],
            orderby='equipo_count desc'
        )
        equipo_labels = dict(self._fields['equipo'].selection)
        return [{
            'equipo': d['equipo'],
            'equipo_label': equipo_labels.get(d['equipo'], d['equipo']),
            'count': d.get('equipo_count', 0),
            'avg_all_in': round(d.get('all_in', 0) or 0, 2),
            'avg_ocean': round(d.get('ocean_freight', 0) or 0, 2),
        } for d in data]

    @api.model
    def _get_stats_por_pais(self, limit=10):
        data = self.read_group(
            [('state', '=', 'active')],
            ['country_id', 'all_in:avg', 'ocean_freight:avg', 'transit_time:avg'],
            ['country_id'],
            orderby='country_id_count desc',
            limit=limit
        )
        return [{
            'country_id': d['country_id'][0] if d['country_id'] else False,
            'country_name': d['country_id'][1] if d['country_id'] else 'Sin país',
            'count': d.get('country_id_count', 0),
            'avg_all_in': round(d.get('all_in', 0) or 0, 2),
            'avg_ocean': round(d.get('ocean_freight', 0) or 0, 2),
            'avg_transit': round(d.get('transit_time', 0) or 0, 1),
        } for d in data]

    @api.model
    def _get_tendencia_mensual(self, meses=12):
        """Tendencia mensual corregida para Odoo 19 usando SQL directo"""
        # IMPORTANTE: Usa el campo computado 'mes' para agrupar
        self.env.cr.execute("""
            SELECT 
                anio, mes, 
                COUNT(*) as count, 
                AVG(all_in) as avg_all_in, 
                AVG(ocean_freight) as avg_ocean
            FROM freight_tariff
            WHERE active = true
            GROUP BY anio, mes
            ORDER BY anio DESC, mes DESC
            LIMIT %s
        """, (meses,))
        results = self.env.cr.dictfetchall()
        
        meses_nombres = {
            '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
            '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
        }
        
        result = [{
            'anio': r['anio'],
            'mes': r['mes'],
            'periodo': f"{meses_nombres.get(r['mes'], r['mes'])}/{r['anio']}",
            'count': r['count'],
            'avg_all_in': round(r['avg_all_in'] or 0, 2),
            'avg_ocean': round(r['avg_ocean'] or 0, 2),
        } for r in results]
        return list(reversed(result))

    @api.model
    def _get_variaciones_mensuales(self):
        tendencia = self._get_tendencia_mensual(meses=2)
        if len(tendencia) < 2:
            return {'variacion_all_in': 0, 'variacion_ocean': 0, 'tendencia': 'estable'}
        
        actual = tendencia[-1]
        anterior = tendencia[-2]
        var_all_in = 0
        if anterior['avg_all_in'] > 0:
            var_all_in = ((actual['avg_all_in'] - anterior['avg_all_in']) / anterior['avg_all_in']) * 100
        
        tendencia_str = 'estable'
        if var_all_in > 5: tendencia_str = 'alza'
        elif var_all_in < -5: tendencia_str = 'baja'
        
        return {
            'variacion_all_in': round(var_all_in, 2),
            'tendencia': tendencia_str,
            'periodo_actual': actual['periodo'],
            'periodo_anterior': anterior['periodo'],
        }

    @api.model
    def _get_alertas(self):
        alertas = []
        today = date.today()
        current_year = str(today.year)
        current_month = str(today.month).zfill(2)
        
        # Alerta de expiración este mes (aproximación basada en año)
        expiran_este_mes = self.search_count([
            ('anio', '=', current_year), ('mes', '=', current_month), ('state', '=', 'active')
        ])
        if expiran_este_mes > 0:
            alertas.append({'tipo': 'warning', 'mensaje': f'{expiran_este_mes} tarifa(s) expiran este mes', 'icono': 'fa-clock-o'})
        
        tarifas_viejas = self.search_count([('state', '=', 'expired')])
        if tarifas_viejas > 10:
            alertas.append({'tipo': 'info', 'mensaje': f'{tarifas_viejas} tarifas expiradas en el sistema', 'icono': 'fa-archive'})
        
        forwarders_activos_ids = self.search([('state', '=', 'active')]).mapped('forwarder_id')
        count_f = len(set(forwarders_activos_ids.ids))
        if count_f < 3:
            alertas.append({'tipo': 'danger', 'mensaje': f'Solo {count_f} forwarder(s) con tarifas vigentes', 'icono': 'fa-exclamation-triangle'})
        
        return alertas

    @api.model
    def _get_comparativo_equipos(self):
        equipos_comunes = ['20st', '40st', '40hc', '20rf', '40rf', 'lcl']
        result = []
        for equipo in equipos_comunes:
            tarifas = self.search([('equipo', '=', equipo), ('state', '=', 'active')])
            if tarifas:
                result.append({
                    'equipo': equipo,
                    'label': dict(self._fields['equipo'].selection).get(equipo, equipo),
                    'count': len(tarifas),
                    'min': min(t.all_in for t in tarifas),
                    'max': max(t.all_in for t in tarifas),
                    'avg': round(sum(t.all_in for t in tarifas) / len(tarifas), 2),
                })
        return result

    @api.model
    def get_tarifa_mas_economica(self, pol_id=None, pod_id=None, equipo=None):
        domain = [('state', '=', 'active')]
        if pol_id: domain.append(('pol_id', '=', pol_id))
        if pod_id: domain.append(('pod_id', '=', pod_id))
        if equipo: domain.append(('equipo', '=', equipo))
        tarifas = self.search(domain, order='all_in asc', limit=5)
        return [{'id': t.id, 'name': t.name, 'forwarder': t.forwarder_id.name, 'naviera': t.naviera_id.name or '-', 'all_in': t.all_in, 'transit_time': t.transit_time} for t in tarifas]

    # =====================================================
    # MÉTODOS AUXILIARES Y CRUD
    # =====================================================

    def _get_or_create_tag(self, tag_name):
        tag = self.env['res.partner.category'].search([('name', '=', tag_name)], limit=1)
        if not tag:
            tag = self.env['res.partner.category'].create({'name': tag_name})
        return tag

    def _assign_tag_to_partner(self, partner_id, tag):
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
                if vals.get(field):
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