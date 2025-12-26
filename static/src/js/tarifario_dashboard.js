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
            // Resumen general
            totalTarifas: 0,
            tarifasActivas: 0,
            tarifasExpiradas: 0,
            promedioAllIn: 0,
            // Por estado
            statsByState: [],
            // Por equipo
            statsByEquipo: [],
            // Por forwarder (top 5)
            topForwarders: [],
            // Por naviera
            topNavieras: [],
            // Por ruta (POL-POD)
            topRutas: [],
            // Por país
            statsByCountry: [],
            // Tendencia mensual (último año)
            tendenciaMensual: [],
            // Comparativo de costos
            promedioOceanFreight: 0,
            promedioAmsImo: 0,
            transitTimePromedio: 0,
            demorasPromedio: 0,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            this.state.error = null;

            // 1. Total de tarifas
            const allTariffs = await this.orm.searchCount("freight.tariff", []);
            this.state.totalTarifas = allTariffs;

            // 2. Tarifas por estado
            const activeCount = await this.orm.searchCount("freight.tariff", [["state", "=", "active"]]);
            const expiredCount = await this.orm.searchCount("freight.tariff", [["state", "=", "expired"]]);
            this.state.tarifasActivas = activeCount;
            this.state.tarifasExpiradas = expiredCount;

            // 3. Promedios generales (solo tarifas activas)
            const avgData = await this.orm.readGroup(
                "freight.tariff",
                [["state", "=", "active"]],
                ["all_in:avg", "ocean_freight:avg", "ams_imo:avg", "transit_time:avg", "demoras:avg"],
                []
            );
            
            if (avgData.length > 0) {
                this.state.promedioAllIn = this._formatNumber(avgData[0].all_in || 0);
                this.state.promedioOceanFreight = this._formatNumber(avgData[0].ocean_freight || 0);
                this.state.promedioAmsImo = this._formatNumber(avgData[0].ams_imo || 0);
                this.state.transitTimePromedio = Math.round(avgData[0].transit_time || 0);
                this.state.demorasPromedio = Math.round(avgData[0].demoras || 0);
            }

            // 4. Stats por equipo (top 6)
            const equipoStats = await this.orm.readGroup(
                "freight.tariff",
                [["state", "=", "active"]],
                ["equipo", "all_in:avg", "__count"],
                ["equipo"],
                { limit: 6, orderby: "__count desc" }
            );
            this.state.statsByEquipo = equipoStats.map(e => ({
                equipo: this._formatEquipo(e.equipo),
                count: e.__count,
                avgAllIn: this._formatNumber(e.all_in || 0)
            }));

            // 5. Top forwarders
            const forwarderStats = await this.orm.readGroup(
                "freight.tariff",
                [["state", "=", "active"]],
                ["forwarder_id", "all_in:avg", "__count"],
                ["forwarder_id"],
                { limit: 5, orderby: "__count desc" }
            );
            this.state.topForwarders = forwarderStats.map(f => ({
                name: f.forwarder_id ? f.forwarder_id[1] : "Sin asignar",
                count: f.__count,
                avgAllIn: this._formatNumber(f.all_in || 0)
            }));

            // 6. Top navieras
            const navieraStats = await this.orm.readGroup(
                "freight.tariff",
                [["state", "=", "active"], ["naviera_id", "!=", false]],
                ["naviera_id", "all_in:avg", "__count"],
                ["naviera_id"],
                { limit: 5, orderby: "__count desc" }
            );
            this.state.topNavieras = navieraStats.map(n => ({
                name: n.naviera_id ? n.naviera_id[1] : "Sin asignar",
                count: n.__count,
                avgAllIn: this._formatNumber(n.all_in || 0)
            }));

            // 7. Top rutas (POL -> POD)
            const rutaStats = await this.orm.readGroup(
                "freight.tariff",
                [["state", "=", "active"]],
                ["pol_id", "pod_id", "all_in:avg", "__count"],
                ["pol_id", "pod_id"],
                { limit: 5, orderby: "__count desc" }
            );
            this.state.topRutas = rutaStats.map(r => ({
                pol: r.pol_id ? r.pol_id[1] : "?",
                pod: r.pod_id ? r.pod_id[1] : "?",
                count: r.__count,
                avgAllIn: this._formatNumber(r.all_in || 0)
            }));

            // 8. Por país
            const countryStats = await this.orm.readGroup(
                "freight.tariff",
                [["state", "=", "active"]],
                ["country_id", "all_in:avg", "__count"],
                ["country_id"],
                { limit: 5, orderby: "__count desc" }
            );
            this.state.statsByCountry = countryStats.map(c => ({
                name: c.country_id ? c.country_id[1] : "Sin país",
                count: c.__count,
                avgAllIn: this._formatNumber(c.all_in || 0)
            }));

            // 9. Tendencia mensual (agrupado por año-mes)
            const tendencia = await this.orm.readGroup(
                "freight.tariff",
                [],
                ["anio", "mes", "all_in:avg", "__count"],
                ["anio", "mes"],
                { orderby: "anio desc, mes desc", limit: 12 }
            );
            this.state.tendenciaMensual = tendencia.reverse().map(t => ({
                periodo: `${this._formatMes(t.mes)}/${t.anio}`,
                count: t.__count,
                avgAllIn: this._formatNumber(t.all_in || 0)
            }));

        } catch (error) {
            console.error("Error cargando dashboard:", error);
            this.state.error = error.message || "Error al cargar datos";
        } finally {
            this.state.loading = false;
        }
    }

    _formatNumber(num) {
        return parseFloat(num || 0).toFixed(2);
    }

    _formatMes(mes) {
        const meses = {
            '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
            '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic'
        };
        return meses[mes] || mes;
    }

    _formatEquipo(equipo) {
        const equipos = {
            '20st': "20' ST", '40st': "40' ST", '40hc': "40' HC",
            '45hc': "45' HC", '20rf': "20' RF", '40rf': "40' RF",
            '40rh': "40' RH", 'lcl': "LCL", 'bbk': "BBK",
            '20ot': "20' OT", '40ot': "40' OT", '20fr': "20' FR",
            '40fr': "40' FR", 'roro': "RoRo"
        };
        return equipos[equipo] || equipo;
    }

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
}

registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);