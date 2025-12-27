## ./__init__.py
```py
from . import models
```

## ./__manifest__.py
```py
{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '1.1.0',
    'author': 'Alphaqueb Consulting',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas, KPIs y catálogo de fletes marítimos',
    'depends': ['base', 'web', 'mail', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/partner_category_data.xml',
        'views/tarifario_views.xml',
        'views/tarifario_menus.xml',
        'views/dashboard_kpi.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'logistica_tarifario/static/src/scss/tarifario_dashboard.scss',
            'logistica_tarifario/static/src/js/tarifario_dashboard.js',
            'logistica_tarifario/static/src/xml/tarifario_dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}```

## ./data/partner_category_data.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="partner_category_forwarder" model="res.partner.category">
            <field name="name">Forwarder</field>
        </record>
        <record id="partner_category_naviera" model="res.partner.category">
            <field name="name">Naviera</field>
        </record>
        <record id="partner_category_pol" model="res.partner.category">
            <field name="name">POL</field>
        </record>
        <record id="partner_category_pod" model="res.partner.category">
            <field name="name">POD</field>
        </record>
    </data>
</odoo>```

## ./models/__init__.py
```py
from . import tarifario_master
```

## ./models/tarifario_master.py
```py
from odoo import models, fields, api
from datetime import date, timedelta
from collections import defaultdict


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

    # Campos computados adicionales para análisis
    ruta_completa = fields.Char(
        string='Ruta', 
        compute='_compute_ruta_completa', 
        store=True,
        help='POL → POD'
    )
    costo_total_logistico = fields.Monetary(
        string='Costo Total Logístico',
        compute='_compute_costo_total',
        store=True,
        help='EXW + Ocean Freight + AMS/IMO + Lib/Seguro'
    )
    margen_estimado = fields.Float(
        string='% Extras sobre Ocean',
        compute='_compute_margen',
        store=True,
        help='Porcentaje de costos adicionales sobre Ocean Freight'
    )

    @api.depends('pol_id', 'pod_id')
    def _compute_ruta_completa(self):
        for rec in self:
            pol = rec.pol_id.name or '?'
            pod = rec.pod_id.name or '?'
            rec.ruta_completa = f"{pol} → {pod}"

    @api.depends('costo_exw', 'ocean_freight', 'ams_imo', 'lib_seguro')
    def _compute_costo_total(self):
        for rec in self:
            rec.costo_total_logistico = (
                (rec.costo_exw or 0.0) +
                (rec.ocean_freight or 0.0) +
                (rec.ams_imo or 0.0) +
                (rec.lib_seguro or 0.0)
            )

    @api.depends('ocean_freight', 'ams_imo', 'lib_seguro')
    def _compute_margen(self):
        for rec in self:
            if rec.ocean_freight:
                extras = (rec.ams_imo or 0.0) + (rec.lib_seguro or 0.0)
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

    # =====================================================
    # MÉTODOS PARA DASHBOARD KPIs (CORREGIDOS PARA ODOO 19)
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
            'costo_total': round(sum(t.costo_total_logistico for t in tarifas) / count, 2),
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
        
        expiran_este_mes = self.search_count([
            ('anio', '=', current_year), ('mes', '=', current_month), ('state', '=', 'active')
        ])
        if expiran_este_mes > 0:
            alertas.append({'tipo': 'warning', 'mensaje': f'{expiran_este_mes} tarifa(s) expiran este mes', 'icono': 'fa-clock-o'})
        
        tarifas_viejas = self.search_count([('state', '=', 'expired')])
        if tarifas_viejas > 10:
            alertas.append({'tipo': 'info', 'mensaje': f'{tarifas_viejas} tarifas expiradas en el sistema', 'icono': 'fa-archive'})
        
        # Corregido: Obtener forwarders activos de forma más directa
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
        return super().write(vals)```

## ./static/src/js/tarifario_dashboard.js
```js
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

export class TarifarioDashboard extends Component {
    static template = "logistica_tarifario.DashboardMain";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            loading: true,
            error: null,
            data: null,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            const data = await this.orm.call("freight.tariff", "get_dashboard_data", []);
            this.state.data = data;
        } catch (error) {
            this.state.error = error.message;
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Formatea un número a estilo moneda MXN: 1,234.56
     */
    formatMonetary(number) {
        if (number === undefined || number === null) return "0.00";
        return new Intl.NumberFormat('es-MX', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(number);
    }

    async refresh() {
        await this.loadDashboardData();
    }

    get resumen() { return this.state.data?.resumen || {}; }
    get promedios() { return this.state.data?.promedios || {}; }
    get topForwarders() { return this.state.data?.top_forwarders || []; }
    get topRutas() { return this.state.data?.top_rutas || []; }
    get porEquipo() { return this.state.data?.por_equipo || []; }

    // Acciones de navegación corregidas (views: [[false, "list"]...])
    openAllTarifas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Catálogo General",
            res_model: "freight.tariff",
            views: [[false, "list"], [false, "form"]],
        });
    }

    openTarifasActivas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas Vigentes",
            res_model: "freight.tariff",
            domain: [["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openTarifasExpiradas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Histórico de Expiradas",
            res_model: "freight.tariff",
            domain: [["state", "=", "expired"]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openByForwarder(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.tariff",
            domain: [["forwarder_id", "=", id], ["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openByRuta(pol_id, pod_id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.tariff",
            domain: [["pol_id", "=", pol_id], ["pod_id", "=", pod_id], ["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openByEquipo(equipo) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.tariff",
            domain: [["equipo", "=", equipo], ["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
        });
    }
}

registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);```

## ./static/src/scss/tarifario_dashboard.scss
```scss
.tarifario-dashboard {
    background-color: #f8f9fa;
    min-height: 100%;
    height: auto !important;
    overflow: visible !important;
    padding: 1.5rem;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

    &.o_action {
        overflow: auto !important;
        height: 100% !important;
    }

    .dashboard-header {
        margin-bottom: 2rem;
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        border: 1px solid #edf2f7;
    }

    .kpi-card {
        background: white;
        border: none;
        border-radius: 12px;
        transition: transform 0.2s, box-shadow 0.2s;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        
        &:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        .icon-box {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 10px;
        }
    }

    .card-title-custom {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }

    .stat-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1e293b;
    }

    // Scroll interno para tablas
    .scrollable-table-container {
        max-height: 320px;
        overflow-y: auto;
        
        &::-webkit-scrollbar {
            width: 6px;
        }
        &::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 3px;
        }
        &::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
            &:hover { background: #94a3b8; }
        }
    }

    // Scroll interno para listas
    .scrollable-list {
        max-height: 320px;
        overflow-y: auto;
        
        &::-webkit-scrollbar {
            width: 6px;
        }
        &::-webkit-scrollbar-track {
            background: #f1f5f9;
            border-radius: 3px;
        }
        &::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 3px;
            &:hover { background: #94a3b8; }
        }
    }

    .table-custom {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #edf2f7;
        margin-bottom: 0;

        thead {
            background-color: #f1f5f9;
            position: sticky;
            top: 0;
            z-index: 1;
            
            th {
                border-bottom: none;
                color: #475569;
                font-weight: 600;
                text-transform: uppercase;
                font-size: 0.75rem;
                padding: 1rem;
            }
        }

        tbody td {
            padding: 1rem;
            vertical-align: middle;
            border-bottom: 1px solid #f1f5f9;
        }
    }

    .badge-soft-primary { background: #e0e7ff; color: #4338ca; }
    .badge-soft-success { background: #dcfce7; color: #15803d; }
    .badge-soft-info { background: #e0f2fe; color: #0369a1; }
}```

## ./static/src/xml/tarifario_dashboard.xml
```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <t t-name="logistica_tarifario.DashboardMain">
        <div class="o_action tarifario-dashboard">
            <div t-if="state.loading" class="d-flex justify-content-center align-items-center" style="min-height: 80vh;">
                <div class="spinner-border text-primary" role="status"></div>
            </div>

            <div t-if="!state.loading" class="container-fluid">
                <!-- Header -->
                <div class="dashboard-header d-flex justify-content-between align-items-center">
                    <div>
                        <h2 class="fw-bold text-dark mb-1">Logística Global</h2>
                        <nav aria-label="breadcrumb">
                            <ol class="breadcrumb mb-0">
                                <li class="breadcrumb-item text-primary">Intelligence Hub</li>
                                <li class="breadcrumb-item active">Tarifario v1.1</li>
                            </ol>
                        </nav>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-white shadow-sm border" t-on-click="refresh">
                            <i class="fa fa-refresh me-2 text-primary"/>Sincronizar
                        </button>
                    </div>
                </div>

                <!-- KPIs -->
                <div class="row g-4 mb-4">
                    <div class="col-md-3">
                        <div class="card kpi-card p-3" t-on-click="openTarifasActivas" style="cursor:pointer;">
                            <div class="d-flex align-items-center justify-content-between">
                                <div>
                                    <p class="card-title-custom mb-1">Fletes Vigentes</p>
                                    <h2 class="stat-value mb-0"><t t-esc="resumen.activas"/></h2>
                                </div>
                                <div class="icon-box bg-soft-success">
                                    <i class="fa fa-check-circle fa-2x text-success"/>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card kpi-card p-3">
                            <div class="d-flex align-items-center justify-content-between">
                                <div>
                                    <p class="card-title-custom mb-1">Promedio All In</p>
                                    <h2 class="stat-value mb-0 text-primary">$<t t-esc="formatMonetary(promedios.all_in)"/></h2>
                                </div>
                                <div class="icon-box bg-soft-primary">
                                    <i class="fa fa-dollar fa-2x text-primary"/>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card kpi-card p-3">
                            <div class="d-flex align-items-center justify-content-between">
                                <div>
                                    <p class="card-title-custom mb-1">Tiempo de Tránsito</p>
                                    <h2 class="stat-value mb-0 text-info"><t t-esc="promedios.transit_time"/> <small style="font-size: 1rem">días</small></h2>
                                </div>
                                <div class="icon-box bg-soft-info">
                                    <i class="fa fa-ship fa-2x text-info"/>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card kpi-card p-3" t-on-click="openTarifasExpiradas" style="cursor:pointer;">
                            <div class="d-flex align-items-center justify-content-between">
                                <div>
                                    <p class="card-title-custom mb-1">Tarifas Vencidas</p>
                                    <h2 class="stat-value mb-0 text-danger"><t t-esc="resumen.expiradas"/></h2>
                                </div>
                                <div class="icon-box" style="background: #fee2e2;">
                                    <i class="fa fa-exclamation-triangle fa-2x text-danger"/>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tablas -->
                <div class="row g-4 mb-4">
                    <div class="col-lg-8">
                        <div class="card shadow-sm border-0 rounded-4">
                            <div class="card-header bg-white py-3 border-0">
                                <h5 class="fw-bold mb-0 text-dark">Rendimiento de Forwarders</h5>
                            </div>
                            <div class="scrollable-table-container">
                                <table class="table table-custom mb-0">
                                    <thead>
                                        <tr>
                                            <th>Proveedor</th>
                                            <th class="text-center">Tarifas</th>
                                            <th class="text-end">Avg. All In</th>
                                            <th class="text-end">Avg. Transit</th>
                                            <th class="text-end">Acción</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <t t-foreach="topForwarders" t-as="f" t-key="f.id">
                                            <tr>
                                                <td class="fw-bold text-dark"><t t-esc="f.name"/></td>
                                                <td class="text-center"><span class="badge rounded-pill bg-light text-dark border"><t t-esc="f.count"/></span></td>
                                                <td class="text-end text-primary fw-bold">$<t t-esc="formatMonetary(f.avg_all_in)"/></td>
                                                <td class="text-end"><t t-esc="f.avg_transit"/> d</td>
                                                <td class="text-end">
                                                    <button class="btn btn-sm btn-light" t-on-click="() => this.openByForwarder(f.id)">
                                                        <i class="fa fa-eye"/>
                                                    </button>
                                                </td>
                                            </tr>
                                        </t>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="card shadow-sm border-0 rounded-4 h-100">
                            <div class="card-header bg-white py-3 border-0">
                                <h5 class="fw-bold mb-0 text-dark">Rutas Frecuentes</h5>
                            </div>
                            <div class="scrollable-list">
                                <div class="list-group list-group-flush">
                                    <t t-foreach="topRutas" t-as="r" t-key="r_index">
                                        <div class="list-group-item border-0 px-4 py-3" t-on-click="() => this.openByRuta(r.pol_id, r.pod_id)" style="cursor:pointer">
                                            <div class="d-flex justify-content-between align-items-center mb-1">
                                                <span class="fw-bold text-dark small text-truncate"><t t-esc="r.ruta"/></span>
                                                <span class="badge bg-soft-primary"><t t-esc="r.count"/> cot.</span>
                                            </div>
                                            <div class="d-flex justify-content-between small">
                                                <span class="text-muted"><i class="fa fa-clock-o me-1"/> <t t-esc="r.avg_transit"/> días</span>
                                                <span class="text-success fw-bold">$<t t-esc="formatMonetary(r.avg_all_in)"/></span>
                                            </div>
                                        </div>
                                    </t>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </t>
</templates>```

## ./views/dashboard_kpi.xml
```xml
<odoo>
    <record id="action_tarifario_dashboard" model="ir.actions.client">
        <field name="name">Panel de Control KPIs</field>
        <field name="tag">tarifario_dashboard_tag</field>
    </record>

    <menuitem id="menu_tarifario_kpi" 
              name="Dashboard KPIs" 
              parent="menu_tarifario_root" 
              action="action_tarifario_dashboard" 
              sequence="1"/>
</odoo>
```

## ./views/tarifario_menus.xml
```xml
<odoo>
    <!-- Menú Principal -->
    <menuitem id="menu_tarifario_root" 
              name="Tarifario" 
              web_icon="logistica_tarifario,static/description/icon.png"
              sequence="1"/>

    <!-- Contenedor Operaciones -->
    <menuitem id="menu_tarifario_operaciones" 
              name="Operaciones" 
              parent="menu_tarifario_root" 
              sequence="10"/>

    <!-- Acción al Catálogo -->
    <menuitem id="menu_freight_tariff_main" 
              name="Catálogo de Tarifas" 
              parent="menu_tarifario_operaciones" 
              action="action_freight_tariff"
              sequence="20"/>
</odoo>```

## ./views/tarifario_views.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_freight_tariff_search" model="ir.ui.view">
        <field name="name">freight.tariff.search</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <search string="Búsqueda de Tarifas">
                <field name="name"/>
                <field name="country_id"/>
                <field name="anio"/>
                <field name="mes"/>
                <field name="forwarder_id"/>
                <field name="naviera_id"/>
                <field name="pol_id"/>
                <field name="pod_id"/>
                
                <separator/>
                <filter string="Vigentes" name="filter_active" domain="[('state', '=', 'active')]"/>
                <filter string="Expiradas" name="filter_expired" domain="[('state', '=', 'expired')]"/>
                
                <separator/>
                <filter name="group_country" string="País" context="{'group_by': 'country_id'}"/>
                <filter name="group_anio" string="Año" context="{'group_by': 'anio'}"/>
                <filter name="group_mes" string="Mes" context="{'group_by': 'mes'}"/>
                <filter name="group_forwarder" string="Forwarder" context="{'group_by': 'forwarder_id'}"/>
                <filter name="group_naviera" string="Naviera" context="{'group_by': 'naviera_id'}"/>
                <filter name="group_pol" string="Puerto Carga (POL)" context="{'group_by': 'pol_id'}"/>
                <filter name="group_pod" string="Puerto Destino (POD)" context="{'group_by': 'pod_id'}"/>
                <filter name="group_state" string="Estado" context="{'group_by': 'state'}"/>
            </search>
        </field>
    </record>

    <record id="view_freight_tariff_list" model="ir.ui.view">
        <field name="name">freight.tariff.list</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <list decoration-success="state == 'active'" decoration-danger="state == 'expired'">
                <field name="country_id"/>
                <field name="anio"/>
                <field name="mes"/>
                <field name="forwarder_id"/>
                <field name="naviera_id"/>
                <field name="pol_id"/>
                <field name="pod_id"/>
                <field name="equipo"/>
                <field name="costo_exw" optional="show"/>
                <field name="ocean_freight" optional="show"/>
                <field name="ams_imo" optional="show"/>
                <field name="lib_seguro" optional="show"/>
                <field name="all_in" sum="Total"/>
                <field name="transit_time"/>
                <field name="demoras"/>
                <field name="state" widget="badge" decoration-success="state == 'active'" decoration-danger="state == 'expired'"/>
            </list>
        </field>
    </record>

    <record id="view_freight_tariff_form" model="ir.ui.view">
        <field name="name">freight.tariff.form</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <field name="state" widget="statusbar" statusbar_visible="active,expired"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name" readonly="1"/></h1>
                    </div>
                    <group>
                        <group string="Origen y Destino">
                            <field name="country_id"/>
                            <field name="forwarder_id" options="{'no_quick_create': True}"/>
                            <field name="naviera_id" options="{'no_quick_create': True}"/>
                            <field name="pol_id" options="{'no_quick_create': True}"/>
                            <field name="pod_id" options="{'no_quick_create': True}"/>
                        </group>
                        <group string="Periodo y Equipo">
                            <field name="anio"/>
                            <field name="mes"/>
                            <field name="equipo"/>
                            <field name="currency_id" invisible="1"/>
                        </group>
                    </group>
                    <group>
                        <group string="Costos">
                            <field name="costo_exw"/>
                            <field name="ocean_freight"/>
                            <field name="ams_imo"/>
                            <field name="lib_seguro"/>
                            <field name="all_in" class="oe_subtotal_footer_separator"/>
                        </group>
                        <group string="Tiempos">
                            <field name="transit_time"/>
                            <field name="demoras"/>
                        </group>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <record id="action_freight_tariff" model="ir.actions.act_window">
        <field name="name">Catálogo de Tarifas</field>
        <field name="res_model">freight.tariff</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="view_freight_tariff_search"/>
        <field name="context">{'search_default_filter_active': 1}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">Crea tu primera tarifa</p>
        </field>
    </record>
</odoo>```

