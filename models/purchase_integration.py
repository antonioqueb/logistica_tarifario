# -*- coding: utf-8 -*-
"""Integración Tarifario ↔ Orden de Compra ↔ Producto (costeo automático).

Flujo de la regla de negocio:
1. En la OC se captura la RUTA (país de origen, POL, POD) eligiendo SOLO
   combinaciones que existen en el tarifario activo (verdad absoluta, sin
   mostrar precios). Capacidad de contenedor y arancel se definen POR LÍNEA.
2. Capacidad/arancel son VAIVÉN: se pre-llenan desde el producto si ya los
   tiene; si el producto está vacío, la OC los propaga al producto de
   inmediato. La ruta NO se pre-llena: se elige por compra.
3. El costo del producto NO se toca al confirmar la OC. Solo al VALIDAR una
   recepción (incluida la de tránsito) se escriben en el producto los datos
   de la última compra (ruta + capacidad + arancel) y se recalcula el costo
   ALL-IN (motor de inventory_shopping_cart, invocado de forma defensiva).
"""
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

# El default del producto es 1.0 (placeholder sin significado operativo):
# cualquier capacidad <= 1 se considera "no definida".
_CAPACITY_UNSET_THRESHOLD = 1.0


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    som_route_country_id = fields.Many2one(
        'res.country',
        string='País de Origen',
        tracking=True,
        help='País de origen de la mercancía. Solo países con tarifa activa '
             'en el tarifario.',
    )
    som_route_pol_id = fields.Many2one(
        'res.partner',
        string='Puerto de Carga (POL)',
        tracking=True,
        help='Solo puertos de carga con tarifa activa para el país elegido.',
    )
    som_route_pod_id = fields.Many2one(
        'res.partner',
        string='Puerto de Destino (POD)',
        tracking=True,
        help='Solo puertos destino con tarifa activa para país + POL.',
    )

    som_allowed_country_ids = fields.Many2many(
        'res.country', compute='_compute_som_route_domains',
        string='Países con tarifa',
    )
    som_allowed_pol_ids = fields.Many2many(
        'res.partner', compute='_compute_som_route_domains',
        string='POLs con tarifa',
    )
    som_allowed_pod_ids = fields.Many2many(
        'res.partner', compute='_compute_som_route_domains',
        string='PODs con tarifa',
    )

    @api.depends('som_route_country_id', 'som_route_pol_id')
    def _compute_som_route_domains(self):
        """El tarifario es la ÚNICA fuente: los selectores solo ofrecen
        combinaciones con tarifa activa, en cascada país → POL → POD."""
        Tariff = self.env['freight.tariff'].sudo()
        tariffs = Tariff.search([('state', '=', 'active')])
        for order in self:
            order.som_allowed_country_ids = [(6, 0, tariffs.mapped('country_id').ids)]
            by_country = (
                tariffs.filtered(lambda t: t.country_id == order.som_route_country_id)
                if order.som_route_country_id else tariffs
            )
            order.som_allowed_pol_ids = [(6, 0, by_country.mapped('pol_id').ids)]
            by_pol = (
                by_country.filtered(lambda t: t.pol_id == order.som_route_pol_id)
                if order.som_route_pol_id else by_country
            )
            order.som_allowed_pod_ids = [(6, 0, by_pol.mapped('pod_id').ids)]

    @api.onchange('partner_id')
    def _onchange_partner_som_route_country(self):
        """El país de origen toma por DEFECTO el país del proveedor (si ese
        país tiene tarifa activa), siempre editable. No pisa una ruta ya
        elegida a mano."""
        for order in self:
            if order.som_route_country_id or not order.partner_id.country_id:
                continue
            if order.partner_id.country_id in order.som_allowed_country_ids:
                order.som_route_country_id = order.partner_id.country_id

    @api.onchange('som_route_country_id')
    def _onchange_som_route_country(self):
        for order in self:
            if order.som_route_pol_id and order.som_route_pol_id not in order.som_allowed_pol_ids:
                order.som_route_pol_id = False
            if order.som_route_pod_id and order.som_route_pod_id not in order.som_allowed_pod_ids:
                order.som_route_pod_id = False

    @api.onchange('som_route_pol_id')
    def _onchange_som_route_pol(self):
        for order in self:
            if order.som_route_pod_id and order.som_route_pod_id not in order.som_allowed_pod_ids:
                order.som_route_pod_id = False


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    som_container_capacity = fields.Float(
        string='Cap. Contenedor (m²)',
        digits='Product Unit of Measure',
        help='Metros cuadrados de ESTE material por contenedor. Se pre-llena '
             'desde el producto; si el producto no lo tiene, se propaga hacia él.',
    )
    som_arancel_pct = fields.Float(
        string='Arancel (%)',
        digits=(5, 2),
        help='Arancel aplicable a este material. Vaivén con el producto.',
    )

    @api.onchange('product_id')
    def _onchange_product_som_logistics(self):
        """Producto → línea: si el producto ya tiene capacidad/arancel, la
        línea nace pre-llenada (no volver a capturar en cada compra)."""
        for line in self:
            if not line.product_id:
                continue
            tmpl = line.product_id.product_tmpl_id
            if 'x_container_capacity' in tmpl._fields:
                cap = tmpl.x_container_capacity or 0.0
                if cap > _CAPACITY_UNSET_THRESHOLD and not line.som_container_capacity:
                    line.som_container_capacity = cap
            if 'x_arancel_pct' in tmpl._fields:
                if (tmpl.x_arancel_pct or 0.0) > 0 and not line.som_arancel_pct:
                    line.som_arancel_pct = tmpl.x_arancel_pct

    def _som_propagate_to_empty_product(self):
        """Línea → producto INMEDIATO, solo cuando el producto está vacío
        (la actualización 'última compra manda' ocurre al validar recepción)."""
        for line in self:
            tmpl = line.product_id.product_tmpl_id if line.product_id else False
            if not tmpl:
                continue
            vals = {}
            if (
                'x_container_capacity' in tmpl._fields
                and (line.som_container_capacity or 0.0) > 0
                and (tmpl.x_container_capacity or 0.0) <= _CAPACITY_UNSET_THRESHOLD
            ):
                vals['x_container_capacity'] = line.som_container_capacity
            if (
                'x_arancel_pct' in tmpl._fields
                and (line.som_arancel_pct or 0.0) > 0
                and not (tmpl.x_arancel_pct or 0.0)
            ):
                vals['x_arancel_pct'] = line.som_arancel_pct
            if vals:
                tmpl.sudo().write(vals)
                _logger.info(
                    "[TARIFARIO_PO] Línea %s propagó a producto %s (vacío): %s",
                    line.id, tmpl.display_name, vals,
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._som_propagate_to_empty_product()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'som_container_capacity' in vals or 'som_arancel_pct' in vals:
            self._som_propagate_to_empty_product()
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super()._action_done()
        try:
            self._som_update_products_from_last_purchase()
        except Exception:
            # El costeo nunca debe bloquear una recepción física.
            _logger.exception(
                "[TARIFARIO_PO] Falló la actualización de costeo tras validar "
                "recepción %s.", self.mapped('name'),
            )
        return res

    def _som_update_products_from_last_purchase(self):
        """REGLA CLAVE: los datos logísticos/arancelarios y el costo del
        producto se actualizan SOLO al validar una recepción (aunque sea de
        tránsito). Siempre gana la última compra recibida; los valores vacíos
        de la OC no borran lo que el producto ya tiene."""
        templates_to_recompute = self.env['product.template'].sudo()

        for picking in self:
            if picking.state != 'done':
                continue
            for move in picking.move_ids:
                po_line = getattr(move, 'purchase_line_id', False)
                if not po_line or not move.product_id:
                    continue
                order = po_line.order_id
                tmpl = move.product_id.product_tmpl_id.sudo()
                tf = tmpl._fields
                vals = {}

                if order.som_route_country_id and 'x_origin_country_id' in tf:
                    if tmpl.x_origin_country_id != order.som_route_country_id:
                        vals['x_origin_country_id'] = order.som_route_country_id.id
                if order.som_route_pol_id and 'x_pol_id' in tf:
                    if tmpl.x_pol_id != order.som_route_pol_id:
                        vals['x_pol_id'] = order.som_route_pol_id.id
                if order.som_route_pod_id and 'x_pod_id' in tf:
                    if tmpl.x_pod_id != order.som_route_pod_id:
                        vals['x_pod_id'] = order.som_route_pod_id.id
                if (po_line.som_container_capacity or 0.0) > 0 and 'x_container_capacity' in tf:
                    if tmpl.x_container_capacity != po_line.som_container_capacity:
                        vals['x_container_capacity'] = po_line.som_container_capacity
                if (po_line.som_arancel_pct or 0.0) > 0 and 'x_arancel_pct' in tf:
                    if tmpl.x_arancel_pct != po_line.som_arancel_pct:
                        vals['x_arancel_pct'] = po_line.som_arancel_pct

                if vals:
                    tmpl.write(vals)
                    _logger.info(
                        "[TARIFARIO_PO] Recepción %s: producto %s actualizado "
                        "con la última compra (%s): %s",
                        picking.name, tmpl.display_name, order.name, vals,
                    )
                templates_to_recompute |= tmpl

        # Recalcular el costo ALL-IN (motor de inventory_shopping_cart).
        if templates_to_recompute and hasattr(templates_to_recompute, '_compute_costo_all_in'):
            templates_to_recompute._compute_costo_all_in()
            _logger.info(
                "[TARIFARIO_PO] Costo ALL-IN recalculado para: %s",
                templates_to_recompute.mapped('display_name'),
            )
