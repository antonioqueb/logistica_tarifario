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
registry.category("actions").add("tarifario_dashboard_tag", TarifarioDashboard);