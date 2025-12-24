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
