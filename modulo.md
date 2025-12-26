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

        return super().write(vals)```

## ./static/src/js/tarifario_dashboard.js
```js
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class TarifarioDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.stats = [];
        
        onWillStart(async () => {
            try {
                this.stats = await this.orm.readGroup(
                    "freight.tariff", 
                    [], 
                    ["all_in:avg", "id:count"], 
                    ["state"]
                );
            } catch (e) {
                console.log("Error cargando Dashboard stats:", e);
            }
        });
    }
}
TarifarioDashboard.template = "logistica_tarifario.DashboardMain";
registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);```

## ./static/src/xml/tarifario_dashboard.xml
```xml
<templates xml:space="preserve">
    <t t-name="logistica_tarifario.DashboardMain" owl="1">
        <div class="o_action_manager o_content bg-100 p-4">
            <div class="row m-0">
                <div class="col-12 mb-4">
                    <h2 class="fw-bold">Indicadores de Gestión de Tarifas</h2>
                </div>
                <!-- Card 1 -->
                <div class="col-md-4">
                    <div class="card shadow-sm border-0 bg-primary text-white p-3">
                        <div class="card-title text-uppercase opacity-75">Tarifa Promedio Global</div>
                        <div class="h2 fw-bold">$ <t t-esc="stats[0] ? stats[0].all_in : '0'"/></div>
                        <div class="mt-2"><i class="fa fa-line-chart"/> Actualizado este mes</div>
                    </div>
                </div>
                <!-- Card 2 -->
                <div class="col-md-4">
                    <div class="card shadow-sm border-0 bg-success text-white p-3">
                        <div class="card-title text-uppercase opacity-75">Tarifas Activas</div>
                        <div class="h2 fw-bold"><t t-esc="stats[0] ? stats[0].id_count : '0'"/> Registros</div>
                        <div class="mt-2"><i class="fa fa-check-circle"/> Listas para embarque</div>
                    </div>
                </div>
            </div>
            
            <div class="row m-0 mt-5">
                <div class="col-12 bg-white p-5 rounded shadow-sm text-center">
                    <i class="fa fa-ship fa-4x text-200 mb-3"/>
                    <h3>Bienvenido al Historial de Tarifas</h3>
                    <p class="text-muted">Utiliza los filtros de <b>Año</b> y <b>Mes</b> en el menú de Catálogo para comparar los montos históricos.</p>
                </div>
            </div>
        </div>
    </t>
</templates>
```

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
              name="Logística: Tarifario" 
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

