## ./__init__.py
```py
from . import models
```

## ./__manifest__.py
```py
{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '1.0.1',
    'author': 'Alphaqueb Consulting',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas, KPIs y catálogo de fletes marítimos',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
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

## ./models/__init__.py
```py
from . import tarifario_master
```

## ./models/tarifario_master.py
```py
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
    
    # PERIODOS (Crucial: store=True para que funcione el Group By)
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
            name = f"{rec.forwarder_id.name or ''} | {rec.pol_id or ''}-{rec.pod_id or ''} ({date_str})"
            rec.name = name

    @api.depends('ocean_freight', 'ams_imo', 'lib_seguro')
    def _compute_all_in(self):
        for rec in self:
            rec.all_in = (rec.ocean_freight or 0.0) + (rec.ams_imo or 0.0) + (rec.lib_seguro or 0.0)

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
                rec.state = 'active'```

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
    <!-- Búsqueda Avanzada (Adaptada de tu ejemplo de Studio) -->
    <record id="view_freight_tariff_search" model="ir.ui.view">
        <field name="name">freight.tariff.search</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <search string="Búsqueda de Tarifas">
                <field name="name"/>
                <field name="anio"/>
                <field name="forwarder_id"/>
                <field name="pol_id"/>
                <field name="pod_id"/>
                
                <filter string="Vigentes" name="filter_active" domain="[('state', '=', 'active')]"/>
                <filter string="Expiradas" name="filter_expired" domain="[('state', '=', 'expired')]"/>
                
                <group expand="0" string="Agrupar Por">
                    <filter name="group_anio" string="Año" context="{'group_by': 'anio'}"/>
                    <filter name="group_forwarder" string="Forwarder" context="{'group_by': 'forwarder_id'}"/>
                    <filter name="group_pol" string="Puerto Carga (POL)" context="{'group_by': 'pol_id'}"/>
                    <filter name="group_pod" string="Puerto Destino (POD)" context="{'group_by': 'pod_id'}"/>
                    <filter name="group_state" string="Estado" context="{'group_by': 'state'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Lista -->
    <record id="view_freight_tariff_list" model="ir.ui.view">
        <field name="name">freight.tariff.list</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <list decoration-success="state == 'active'" decoration-danger="state == 'expired'">
                <field name="anio"/>
                <field name="forwarder_id"/>
                <field name="pol_id"/>
                <field name="pod_id"/>
                <field name="all_in" sum="Total"/>
                <field name="state" widget="badge" decoration-success="state == 'active'" decoration-danger="state == 'expired'"/>
            </list>
        </field>
    </record>

    <!-- Formulario -->
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
                        <group>
                            <field name="forwarder_id"/>
                            <field name="pol_id"/>
                            <field name="pod_id"/>
                        </group>
                        <group>
                            <field name="fecha_tarifa"/>
                            <field name="vigencia_fin"/>
                            <field name="equipo"/>
                            <field name="currency_id" invisible="1"/>
                        </group>
                    </group>
                    <group string="Costos">
                        <field name="ocean_freight"/>
                        <field name="ams_imo"/>
                        <field name="lib_seguro"/>
                        <field name="all_in" class="oe_subtotal_footer_separator"/>
                    </group>
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <!-- Acción -->
    <record id="action_freight_tariff" model="ir.actions.act_window">
        <field name="name">Catálogo de Tarifas</field>
        <field name="res_model">freight.tariff</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="view_freight_tariff_search"/>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">Crea tu primera tarifa</p>
        </field>
    </record>
</odoo>```

