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
    som_route_forwarder_id = fields.Many2one(
        'res.partner',
        string='Forwarder',
        tracking=True,
        help='Solo forwarders con tarifa activa para el país elegido.',
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
    som_allowed_forwarder_ids = fields.Many2many(
        'res.partner', compute='_compute_som_route_domains',
        string='Forwarders con tarifa',
    )
    som_allowed_pol_ids = fields.Many2many(
        'res.partner', compute='_compute_som_route_domains',
        string='POLs con tarifa',
    )
    som_allowed_pod_ids = fields.Many2many(
        'res.partner', compute='_compute_som_route_domains',
        string='PODs con tarifa',
    )

    @api.depends('som_route_country_id', 'som_route_forwarder_id', 'som_route_pol_id')
    def _compute_som_route_domains(self):
        """El tarifario es la ÚNICA fuente: cascada país → forwarder →
        POL → POD. Si el forwarder solo tiene un puerto tarifado, esa es la
        única opción."""
        Tariff = self.env['freight.tariff'].sudo()
        tariffs = Tariff.search([('state', '=', 'active')])
        for order in self:
            order.som_allowed_country_ids = [(6, 0, tariffs.mapped('country_id').ids)]
            by_country = (
                tariffs.filtered(lambda t: t.country_id == order.som_route_country_id)
                if order.som_route_country_id else tariffs
            )
            order.som_allowed_forwarder_ids = [(6, 0, by_country.mapped('forwarder_id').ids)]
            by_fwd = (
                by_country.filtered(lambda t: t.forwarder_id == order.som_route_forwarder_id)
                if order.som_route_forwarder_id else by_country
            )
            order.som_allowed_pol_ids = [(6, 0, by_fwd.mapped('pol_id').ids)]
            by_pol = (
                by_fwd.filtered(lambda t: t.pol_id == order.som_route_pol_id)
                if order.som_route_pol_id else by_fwd
            )
            order.som_allowed_pod_ids = [(6, 0, by_pol.mapped('pod_id').ids)]

    def _som_apply_costing_update(self, products=None, naviera=False,
                                   forwarder=False, pol=False, pod=False):
        """NÚCLEO del costeo automático: escribe en los productos de esta OC
        los datos de la última compra (ruta, capacidad, arancel y naviera/
        forwarder con la regla 'la más costosa gana') y recalcula el ALL-IN.

        Disparadores:
        - PUBLICACIÓN del inventario en tránsito (torre de control): el
          momento en que el material queda disponible para venderse.
        - Validación de recepción SOLO en flujos sin torre de control
          (compras nacionales / recepciones directas).
        """
        Picking = self.env['stock.picking']
        templates = self.env['product.template'].sudo()
        for order in self:
            route_pol = pol or order.som_route_pol_id
            route_pod = pod or order.som_route_pod_id
            for line in order.order_line:
                if line.display_type or not line.product_id:
                    continue
                if products and line.product_id.product_tmpl_id.id not in products.ids:
                    continue
                tmpl = line.product_id.product_tmpl_id.sudo()
                tf = tmpl._fields
                vals = {}
                if order.som_route_country_id and 'x_origin_country_id' in tf                         and tmpl.x_origin_country_id != order.som_route_country_id:
                    vals['x_origin_country_id'] = order.som_route_country_id.id
                if route_pol and 'x_pol_id' in tf and tmpl.x_pol_id != route_pol:
                    vals['x_pol_id'] = route_pol.id
                if route_pod and 'x_pod_id' in tf and tmpl.x_pod_id != route_pod:
                    vals['x_pod_id'] = route_pod.id
                if (line.som_container_capacity or 0.0) > 0 and 'x_container_capacity' in tf                         and tmpl.x_container_capacity != line.som_container_capacity:
                    vals['x_container_capacity'] = line.som_container_capacity
                if (line.som_arancel_pct or 0.0) > 0 and 'x_arancel_pct' in tf                         and tmpl.x_arancel_pct != line.som_arancel_pct:
                    vals['x_arancel_pct'] = line.som_arancel_pct

                if naviera and 'x_naviera_id' in tf:
                    new_cost = Picking._som_tariff_all_in(
                        order.som_route_country_id, route_pol, route_pod,
                        naviera, forwarder)
                    cur_cost = (
                        Picking._som_tariff_all_in(
                            order.som_route_country_id, route_pol, route_pod,
                            tmpl.x_naviera_id, tmpl.x_forwarder_id)
                        if tmpl.x_naviera_id else -1.0
                    )
                    if new_cost >= cur_cost:
                        if tmpl.x_naviera_id != naviera:
                            vals['x_naviera_id'] = naviera.id
                        if forwarder and 'x_forwarder_id' in tf                                 and tmpl.x_forwarder_id != forwarder:
                            vals['x_forwarder_id'] = forwarder.id

                if vals:
                    tmpl.with_context(skip_costing_recompute=True).write(vals)
                    _logger.info(
                        "[TARIFARIO_PO] Costeo %s: producto %s ← %s",
                        order.name, tmpl.display_name, vals,
                    )
                templates |= tmpl

        if templates and hasattr(templates, '_compute_costo_all_in'):
            templates._compute_costo_all_in()
            _logger.info(
                "[TARIFARIO_PO] Costo ALL-IN recalculado para: %s",
                templates.mapped('display_name'),
            )
        return templates

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
            if order.som_route_forwarder_id and order.som_route_forwarder_id not in order.som_allowed_forwarder_ids:
                order.som_route_forwarder_id = False
            if order.som_route_pol_id and order.som_route_pol_id not in order.som_allowed_pol_ids:
                order.som_route_pol_id = False
            if order.som_route_pod_id and order.som_route_pod_id not in order.som_allowed_pod_ids:
                order.som_route_pod_id = False

    @api.onchange('som_route_forwarder_id')
    def _onchange_som_route_forwarder(self):
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
                # SOLO datos: el costo NO se recalcula aquí (regla estricta:
                # únicamente al publicar o al recibir en ubicación interna).
                tmpl.sudo().with_context(skip_costing_recompute=True).write(vals)
                _logger.info(
                    "[TARIFARIO_PO] Línea %s propagó a producto %s (vacío, sin "
                    "recálculo): %s", line.id, tmpl.display_name, vals,
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

    # Naviera/forwarder del EMBARQUE (nacen en el portal; capturables aquí
    # cuando no vinieron de ahí). Catálogo del tarifario vía etiquetas.
    som_naviera_id = fields.Many2one(
        'res.partner', string='Naviera',
        domain="[('category_id.name', '=', 'Naviera')]",
        help='Naviera real de este embarque. Se pre-llena desde el portal '
             'del proveedor; captúrala aquí si no vino de ahí.',
    )
    som_forwarder_id = fields.Many2one(
        'res.partner', string='Forwarder',
        domain="[('category_id.name', '=', 'Forwarder')]",
        help='Forwarder real de este embarque.',
    )

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

    def _som_resolve_purchase_order(self):
        """OC de esta recepción cuando los moves no traen purchase_line_id.
        Cadena defensiva: purchase_id nativo → OC de la carga (portal
        multi-PO) → OC del viaje de la Torre de Control."""
        self.ensure_one()
        po = getattr(self, 'purchase_id', False)
        if po:
            return po
        po = getattr(self, 'supplier_cargo_po_id', False)
        if po:
            return po
        if 'stock.transit.voyage' in self.env:
            voyage = self.env['stock.transit.voyage'].sudo().search(
                [('reception_picking_id', '=', self.id)], limit=1)
            if voyage and voyage.purchase_id:
                return voyage.purchase_id
        return self.env['purchase.order']

    def _som_tariff_all_in(self, country, pol, pod, naviera=False, forwarder=False):
        """All-in de la tarifa activa que MEJOR corresponde a la combinación
        (más específica primero). 0.0 si no hay tarifa."""
        Tariff = self.env['freight.tariff'].sudo()
        domain = [('state', '=', 'active')]
        if country:
            domain.append(('country_id', '=', country.id))
        if pol:
            domain.append(('pol_id', '=', pol.id))
        if pod:
            domain.append(('pod_id', '=', pod.id))
        candidates = Tariff.search(domain, order='create_date desc')
        if naviera:
            nav = candidates.filtered(lambda t: t.naviera_id == naviera)
            if forwarder:
                navf = nav.filtered(lambda t: t.forwarder_id == forwarder)
                nav = navf or nav
            candidates = nav or candidates
        return candidates[:1].all_in or 0.0

    def _som_apply_carrier_most_expensive(self, picking, order, tmpl):
        """REGLA 'LA MÁS COSTOSA GANA': si esta recepción usó una naviera
        cuya tarifa all-in supera (o el producto no tiene naviera) a la
        registrada, la naviera/forwarder del producto se actualizan. Así,
        con 3 contenedores por 3 navieras distintas, el costeo del producto
        usa la más cara."""
        tf = tmpl._fields
        if 'x_naviera_id' not in tf:
            return {}
        shipment = getattr(picking, 'supplier_shipment_id', False)
        new_nav = picking.som_naviera_id or (
            getattr(shipment, 'naviera_id', False) if shipment else False)
        new_fwd = picking.som_forwarder_id or (
            getattr(shipment, 'forwarder_id', False) if shipment else False)
        if not new_nav:
            return {}

        country = order.som_route_country_id or getattr(tmpl, 'x_origin_country_id', False)
        pol = order.som_route_pol_id or getattr(tmpl, 'x_pol_id', False)
        pod = order.som_route_pod_id or getattr(tmpl, 'x_pod_id', False)

        new_cost = self._som_tariff_all_in(country, pol, pod, new_nav, new_fwd)
        cur_cost = (
            self._som_tariff_all_in(country, pol, pod, tmpl.x_naviera_id, tmpl.x_forwarder_id)
            if tmpl.x_naviera_id else -1.0
        )

        vals = {}
        if new_cost >= cur_cost:
            if tmpl.x_naviera_id != new_nav:
                vals['x_naviera_id'] = new_nav.id
            if new_fwd and 'x_forwarder_id' in tf and tmpl.x_forwarder_id != new_fwd:
                vals['x_forwarder_id'] = new_fwd.id
        return vals

    def _som_update_products_from_last_purchase(self):
        """Disparador de RECEPCIÓN: cualquier recepción validada hacia una
        ubicación INTERNA (existencias) — con o sin torre de control, se haya
        publicado o no. Junto con la PUBLICACIÓN del inventario en tránsito,
        son los ÚNICOS dos momentos que actualizan el costo (regla estricta:
        ni la captura del portal ni la validación de tránsito lo hacen)."""
        templates_to_recompute = self.env['product.template'].sudo()

        for picking in self:
            if picking.state != 'done':
                continue
            # SOLO recepciones a ubicación INTERNA disparan costeo (recibir en
            # existencias). Tránsito validado NO es recepción interna: su
            # disparador es la publicación (o la recepción interna posterior).
            if picking.location_dest_id.usage != 'internal':
                _logger.info(
                    "[TARIFARIO_PO] Picking %s validado hacia '%s' (no "
                    "interna): el costeo espera publicación o recepción "
                    "interna.", picking.name, picking.location_dest_id.usage,
                )
                continue
            fallback_po = picking._som_resolve_purchase_order()
            for move in picking.move_ids:
                if not move.product_id:
                    continue
                po_line = getattr(move, 'purchase_line_id', False)
                if not po_line and fallback_po:
                    # Recepciones SIN vínculo directo en el move (p. ej. las
                    # generadas por la Torre de Control): se resuelve la línea
                    # por producto dentro de la OC de la recepción.
                    po_line = fallback_po.order_line.filtered(
                        lambda l, m=move: not l.display_type
                        and l.product_id == m.product_id
                    )[:1]
                if not po_line:
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

                vals.update(self._som_apply_carrier_most_expensive(picking, order, tmpl))

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
