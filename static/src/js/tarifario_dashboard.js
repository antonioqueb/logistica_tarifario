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

registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);