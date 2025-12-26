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

            // Una sola llamada al backend
            const data = await this.orm.call("freight.tariff", "get_dashboard_data", []);
            this.state.data = data;

        } catch (error) {
            console.error("Error cargando dashboard:", error);
            this.state.error = error.message || "Error al cargar datos";
        } finally {
            this.state.loading = false;
        }
    }

    // Getters para acceso fácil en template
    get resumen() {
        return this.state.data?.resumen || {};
    }

    get promedios() {
        return this.state.data?.promedios || {};
    }

    get topForwarders() {
        return this.state.data?.top_forwarders || [];
    }

    get topNavieras() {
        return this.state.data?.top_navieras || [];
    }

    get topRutas() {
        return this.state.data?.top_rutas || [];
    }

    get porEquipo() {
        return this.state.data?.por_equipo || [];
    }

    get porPais() {
        return this.state.data?.por_pais || [];
    }

    get tendencia() {
        return this.state.data?.tendencia || [];
    }

    get variaciones() {
        return this.state.data?.variaciones || {};
    }

    get alertas() {
        return this.state.data?.alertas || [];
    }

    get comparativoEquipos() {
        return this.state.data?.comparativo_equipos || [];
    }

    // Helpers
    formatNumber(num) {
        return parseFloat(num || 0).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    getVariacionClass(valor) {
        if (valor > 0) return 'text-danger';
        if (valor < 0) return 'text-success';
        return 'text-muted';
    }

    getVariacionIcon(valor) {
        if (valor > 0) return 'fa-arrow-up';
        if (valor < 0) return 'fa-arrow-down';
        return 'fa-minus';
    }

    getTendenciaClass(tendencia) {
        if (tendencia === 'alza') return 'text-danger';
        if (tendencia === 'baja') return 'text-success';
        return 'text-warning';
    }

    // Acciones
    async refresh() {
        await this.loadDashboardData();
    }

    openTarifasActivas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas Activas",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["state", "=", "active"]],
            context: {},
        });
    }

    openTarifasExpiradas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas Expiradas",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["state", "=", "expired"]],
            context: {},
        });
    }

    openAllTarifas() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Todas las Tarifas",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [],
            context: {},
        });
    }

    openByForwarder(forwarderId) {
        if (!forwarderId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas por Forwarder",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["forwarder_id", "=", forwarderId], ["state", "=", "active"]],
            context: {},
        });
    }

    openByNaviera(navieraId) {
        if (!navieraId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas por Naviera",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["naviera_id", "=", navieraId], ["state", "=", "active"]],
            context: {},
        });
    }

    openByRuta(polId, podId) {
        if (!polId || !podId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas por Ruta",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["pol_id", "=", polId], ["pod_id", "=", podId], ["state", "=", "active"]],
            context: {},
        });
    }

    openByEquipo(equipo) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Tarifas - ${equipo}`,
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["equipo", "=", equipo], ["state", "=", "active"]],
            context: {},
        });
    }

    openByPais(countryId) {
        if (!countryId) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tarifas por País",
            res_model: "freight.tariff",
            view_mode: "list,form",
            domain: [["country_id", "=", countryId], ["state", "=", "active"]],
            context: {},
        });
    }
}

registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);