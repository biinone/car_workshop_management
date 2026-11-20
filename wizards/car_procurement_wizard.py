# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class CarProcurementWizard(models.TransientModel):
    _name = 'car.procurement.wizard'
    _description = 'معالج التكاليف والمشتريات المباشرة'

    project_id = fields.Many2one('project.project', string='المشروع', required=True)
    line_ids = fields.One2many('car.procurement.wizard.line', 'wizard_id', string='بنود التكلفة والمشتريات')

    def _load_lines_from_sale_orders(self):
        """سحب بنود المنتجات المخزنية من أوامر البيع بالمشروع"""
        lines = []
        for so in self.project_id.sale_order_ids:
            for so_line in so.order_line.filtered(lambda l: l.product_id.type in ('consu', 'product')):
                lines.append((0, 0, {
                    'product_id': so_line.product_id.id,
                    'description': so_line.name,
                    'quantity': so_line.product_uom_qty,
                    'cost_price': so_line.product_id.standard_price,
                }))
        self.line_ids = lines

    def action_confirm_and_generate(self):
        self.ensure_one()
        analytic_account = self.project_id.analytic_account_id
        if not analytic_account:
            raise UserError("يجب أن يحتوي مشروع السيارة على حساب تحليلي مرتبط.")

        AccountMove = self.env['account.move']
        AccountPayment = self.env['account.payment']

        for line in self.line_ids:
            if not line.employee_id:
                raise ValidationError(f"تنبيه: يجب تحديد الموظف المنفذ للسطر: {line.description or line.product_id.name}")

            is_refund = line.quantity < 0
            move_type = 'in_refund' if is_refund else 'in_invoice'
            qty = abs(line.quantity)

            # تحديد الشريك: المورد إن وجد، أو جهة اتصال الموظف
            partner = line.partner_id or line.employee_id.work_contact_id
            if not partner:
                raise ValidationError(f"يرجى تحديد المورد أو الموظف للسطر: {line.description or line.product_id.name}")

            # 1. إنشاء فاتورة المورد أو المرتجع
            move_vals = {
                'move_type': move_type,
                'partner_id': partner.id,
                'invoice_date': fields.Date.context_today(self),
                'ref': f"سيارة: {self.project_id.vehicle_id.license_plate} | موظف: {line.employee_id.name} | مرجع: {line.client_ref or ''}",
                'invoice_line_ids': [(0, 0, {
                    'product_id': line.product_id.id if line.product_id else False,
                    'name': line.description or line.product_id.display_name,
                    'quantity': qty,
                    'price_unit': line.cost_price,
                    'analytic_distribution': {str(analytic_account.id): 100},
                })],
            }
            move = AccountMove.create(move_vals)
            move.action_post()

            # 2. السداد التلقائي (كاش، بنك، أو عهدة موظف حسب الدفتر المختار)
            if line.payment_journal_id:
                payment_partner = line.employee_id.work_contact_id if line.is_custody else partner
                payment_vals = {
                    'amount': abs(move.amount_total),
                    'payment_type': 'outbound' if not is_refund else 'inbound',
                    'partner_type': 'supplier',
                    'partner_id': payment_partner.id,
                    'journal_id': line.payment_journal_id.id,
                    'currency_id': move.currency_id.id,
                    'ref': f"{line.payment_journal_id.name} - سيارة: {self.project_id.vehicle_id.license_plate} - {line.employee_id.name}",
                }
                payment = AccountPayment.create(payment_vals)
                payment.action_post()

                # تسوية الفاتورة بالسداد
                lines_to_rec = (move.line_ids + payment.move_id.line_ids).filtered(
                    lambda l: l.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
                )
                lines_to_rec.reconcile()

            line.generated_ref = move.name

        return {'type': 'ir.actions.act_window_close'}


class CarProcurementWizardLine(models.TransientModel):
    _name = 'car.procurement.wizard.line'
    _description = 'سطر تكاليف ومشتريات'

    wizard_id = fields.Many2one('car.procurement.wizard', string='النافذة')
    product_id = fields.Many2one('product.product', string='الصنف')
    description = fields.Char(string='الوصف / البيان', required=True)
    quantity = fields.Float(string='الكمية', default=1.0, required=True)
    cost_price = fields.Float(string='سعر التكلفة المباشر', required=True)

    employee_id = fields.Many2one('hr.employee', string='الموظف المنفذ', required=True)
    partner_id = fields.Many2one('res.partner', string='المورد')

    # قائمة دفاتر اليومية (تشمل الخزينة، البنك، ودفتر عهد الموظفين)
    payment_journal_id = fields.Many2one(
        'account.journal', 
        string='طريقة / دفتر الدفع',
        domain="[('type', 'in', ('cash', 'bank'))]"
    )
    is_custody = fields.Boolean(string='عهدة موظف؟', help='علم عليها إذا كان الدفتر يخص عهدة الموظف لتسجيل السداد باسمه مباشرة')

    client_ref = fields.Char(string='رقم فاتورة المحل / المرجع')
    generated_ref = fields.Char(string='رقم القيد / الفاتورة المنشأة', readonly=True)
