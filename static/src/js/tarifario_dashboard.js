/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class TarifarioDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.stats = [];
        
        onWillStart(async () => {
            // Carga de datos agrupados para el Dashboard
            this.stats = await this.orm.readGroup(
                "freight.tariff", 
                [], 
                ["all_in:avg", "id:count"], 
                ["state"]
            );
        });
    }
}

TarifarioDashboard.template = "logistica_tarifario.DashboardMain";
registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);