# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class CustomerVehicle(models.Model):
    _name = 'customer.vehicle'
    _description = 'Customer Vehicle / سيارة العميل'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'license_plate'

    partner_id = fields.Many2one('res.partner', string='مالك السيارة / العميل', required=True, tracking=True)
    license_plate = fields.Char(string='رقم اللوحة', required=True, index=True, tracking=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', string='الماركة', tracking=True)
    model_id = fields.Many2one('fleet.vehicle.model', string='الموديل', domain="[('brand_id', '=?', brand_id)]", tracking=True)
    model_year = fields.Selection([(str(y), str(y)) for y in range(1990, 2030)], string='سنة الصنع', tracking=True)
    vin_sn = fields.Char(string='رقم الشاسيه')
    last_odometer = fields.Float(string='آخر قراءة عداد (كم)', tracking=True)

    project_ids = fields.One2many('project.project', 'vehicle_id', string='سجل الزيارات السابقة')
    project_count = fields.Integer(compute='_compute_project_count', string='عدد الزيارات')

    @api.depends('project_ids')
    def _compute_project_count(self):
        for rec in self:
            rec.project_count = len(rec.project_ids)

    def action_view_visits(self):
        self.ensure_one()
        return {
            'name': f'زيارات السيارة: {self.license_plate}',
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'kanban,tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_partner_id': self.partner_id.id},
        }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vehicle_ids = fields.One2many('customer.vehicle', 'partner_id', string='السيارات المملوكة')


class ProjectProject(models.Model):
    _inherit = 'project.project'

    vehicle_id = fields.Many2one('customer.vehicle', string='السيارة', tracking=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string='رقم اللوحة', store=True)
    current_odometer = fields.Float(string='قراءة عداد الدخول (كم)')
    customer_issue = fields.Text(string='شكوى العميل المبدئية')

    sale_order_ids = fields.One2many('sale.order', 'project_id', string='عروض الأسعار / المقايسات')
    quotation_count = fields.Integer(compute='_compute_quotation_count', string='المقايسات')

    @api.depends('sale_order_ids')
    def _compute_quotation_count(self):
        for rec in self:
            rec.quotation_count = len(rec.sale_order_ids)

    def action_create_quotation(self):
        """زر إنشاء مقايسة جديدة مربوطة بالسيارة والعميل والحساب التحليلي"""
        self.ensure_one()
        return {
            'name': 'إنشاء مقايسة جديدة',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_project_id': self.id,
                'default_analytic_account_id': self.analytic_account_id.id,
            }
        }

    def action_open_procurement_wizard(self):
        """زر فتح جدول المشتريات والمصروفات المباشرة"""
        self.ensure_one()
        wizard = self.env['car.procurement.wizard'].create({
            'project_id': self.id,
        })
        wizard._load_lines_from_sale_orders()
        return {
            'name': 'جدول المشتريات والمصروفات والتكاليف المباشرة',
            'type': 'ir.actions.act_window',
            'res_model': 'car.procurement.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
