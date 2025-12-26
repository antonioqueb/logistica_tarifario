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
            this.state.error = null;
            const data = await this.orm.call("freight.tariff", "get_dashboard_data", []);
            this.state.data = data;
        } catch (error) {
            this.state.error = error.message;
            console.error("Dashboard error:", error);
        } finally {
            this.state.loading = false;
        }
    }

    async refresh() {
        await this.loadDashboardData();
    }

    // Getters
    get resumen() { return this.state.data?.resumen || {}; }
    get promedios() { return this.state.data?.promedios || {}; }
    get topForwarders() { return this.state.data?.top_forwarders || []; }
    get topRutas() { return this.state.data?.top_rutas || []; }
    get porEquipo() { return this.state.data?.por_equipo || []; }

    // =========================================================================
    // ACCIONES CORREGIDAS (Se añade views: [[false, "list"], [false, "form"]])
    // =========================================================================

    openAllTarifas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Catálogo General",
            res_model: "freight.tariff",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTarifasActivas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas Vigentes",
            res_model: "freight.tariff",
            domain: [["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTarifasExpiradas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Histórico de Expiradas",
            res_model: "freight.tariff",
            domain: [["state", "=", "expired"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openByForwarder(id) {
        if (!id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas del Forwarder",
            res_model: "freight.tariff",
            domain: [["forwarder_id", "=", id], ["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openByRuta(pol_id, pod_id) {
        if (!pol_id || !pod_id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas por Ruta",
            res_model: "freight.tariff",
            domain: [["pol_id", "=", pol_id], ["pod_id", "=", pod_id], ["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openByEquipo(equipo) {
        if (!equipo) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Tarifas Equipo: ${equipo}`,
            res_model: "freight.tariff",
            domain: [["equipo", "=", equipo], ["state", "=", "active"]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);