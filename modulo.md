## ./__init__.py
```py
from . import models
```

## ./__manifest__.py
```py
{
    'name': 'Gestión Profesional de Tarifas Logísticas',
    'version': '1.0.1',
    'author': 'Expert Developer',
    'category': 'Operations/Logistics',
    'summary': 'Control histórico de tarifas, KPIs y catálogo de fletes marítimos',
    'depends': ['base', 'web', 'board', 'mail'], # He añadido 'mail' porque usas _inherit mail.thread
    'data': [
        'security/ir.model.access.csv',
        'views/tarifario_views.xml',     # 1. CARGA PRIMERO (Define la acción)
        'views/tarifario_menus.xml',     # 2. CARGA DESPUÉS (Usa la acción)
        'views/dashboard_kpi.xml',       # 3. CARGA AL FINAL (Usa los menús raíz)
    ],
    'assets': {
        'web.assets_backend': [
            'logistica_tarifario/static/src/css/tarifario_style.css',
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
```

## ./static/src/js/tarifario_dashboard.js
```js
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart } = owl;

export class TarifarioDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.stats = {};
        
        onWillStart(async () => {
            this.stats = await this.orm.call("freight.tariff", "read_group", [
                [], ["all_in:avg", "id:count"], ["state"]
            ]);
        });
    }
}
TarifarioDashboard.template = "logistica_tarifario.DashboardMain";
registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);
```

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
<odoo>
    <!-- Búsqueda Avanzada -->
    <record id="view_freight_tariff_search" model="ir.ui.view">
        <field name="name">freight.tariff.search</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <search>
                <field name="forwarder_id"/>
                <field name="pol_id"/>
                <field name="pod_id"/>
                <filter string="Vigentes" name="filter_active" domain="[('state', '=', 'active')]"/>
                <group expand="1" string="Agrupar Por">
                    <filter name="group_anio" string="Año" context="{'group_by': 'anio'}"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Lista (Tree) -> CAMBIADO A <list> PARA ODOO 19 -->
    <record id="view_freight_tariff_list" model="ir.ui.view">
        <field name="name">freight.tariff.list</field>
        <field name="model">freight.tariff</field>
        <field name="arch" type="xml">
            <list decoration-danger="state == 'expired'" decoration-success="state == 'active'" sample="1">
                <field name="anio"/>
                <field name="mes"/>
                <field name="forwarder_id"/>
                <field name="pol_id"/>
                <field name="pod_id"/>
                <field name="all_in" sum="Total" widget="monetary"/>
                <field name="state" widget="badge"/>
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
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <h1><field name="name"/></h1>
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
                </sheet>
                <div class="oe_chatter">
                    <field name="message_follower_ids"/>
                    <field name="activity_ids"/>
                    <field name="message_ids"/>
                </div>
            </form>
        </field>
    </record>

    <!-- Acción: CAMBIADO tree por list -->
    <record id="action_freight_tariff" model="ir.actions.act_window">
        <field name="name">Catálogo de Tarifas</field>
        <field name="res_model">freight.tariff</field>
        <field name="view_mode">list,form,pivot</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">Crea tu primera tarifa</p>
        </field>
    </record>
</odoo>```

