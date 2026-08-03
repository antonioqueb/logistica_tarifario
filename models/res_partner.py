from odoo import api, models

# Etiquetas del tarifario y su xmlid de datos (data/partner_category_data.xml)
TARIFARIO_TAG_XMLIDS = {
    'Forwarder': 'logistica_tarifario.partner_category_forwarder',
    'Naviera': 'logistica_tarifario.partner_category_naviera',
    'POL': 'logistica_tarifario.partner_category_pol',
    'POD': 'logistica_tarifario.partner_category_pod',
}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _tarifario_get_tag(self, tag_name):
        """Resuelve la categoría del tarifario: xmlid → por nombre → la crea."""
        Category = self.env['res.partner.category']
        xmlid = TARIFARIO_TAG_XMLIDS.get(tag_name)
        tag = xmlid and self.env.ref(xmlid, raise_if_not_found=False)
        if not tag:
            tag = Category.search([('name', '=', tag_name)], limit=1)
        if not tag:
            tag = Category.sudo().create({'name': tag_name})
        return tag

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        # tarifario_partner_tag viaja en el context de los many2one del
        # tarifario: garantiza la etiqueta aunque el diálogo 'Crear y editar'
        # o el quick-create no apliquen default_category_id.
        tag_name = self.env.context.get('tarifario_partner_tag')
        if tag_name in TARIFARIO_TAG_XMLIDS:
            tag = self._tarifario_get_tag(tag_name)
            missing = partners.filtered(lambda p: tag not in p.category_id)
            if missing:
                missing.sudo().write({'category_id': [(4, tag.id)]})
        return partners
