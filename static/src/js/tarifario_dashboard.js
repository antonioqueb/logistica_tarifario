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

    async refresh() {
        await this.loadDashboardData();
    }

    // Getters para el XML
    get resumen() { return this.state.data?.resumen || {}; }
    get promedios() { return this.state.data?.promedios || {}; }
    get topForwarders() { return this.state.data?.top_forwarders || []; }
    get topRutas() { return this.state.data?.top_rutas || []; }
    get porEquipo() { return this.state.data?.por_equipo || []; }

    // Acciones de navegación
    openAllTarifas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Catálogo General",
            res_model: "freight.tariff",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
        });
    }

    openTarifasActivas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas Vigentes",
            res_model: "freight.tariff",
            domain: [["state", "=", "active"]],
            view_mode: "list,form",
        });
    }

    openTarifasExpiradas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Histórico de Expiradas",
            res_model: "freight.tariff",
            domain: [["state", "=", "expired"]],
            view_mode: "list,form",
        });
    }

    openByForwarder(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.tariff",
            domain: [["forwarder_id", "=", id], ["state", "=", "active"]],
            view_mode: "list,form",
        });
    }

    openByRuta(pol_id, pod_id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.tariff",
            domain: [["pol_id", "=", pol_id], ["pod_id", "=", pod_id], ["state", "=", "active"]],
            view_mode: "list,form",
        });
    }

    openByEquipo(equipo) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "freight.tariff",
            domain: [["equipo", "=", equipo], ["state", "=", "active"]],
            view_mode: "list,form",
        });
    }
}

registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);