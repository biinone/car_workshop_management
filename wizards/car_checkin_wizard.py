# -*- coding: utf-8 -*-
from odoo import models, fields, api

class CarCheckinWizard(models.TransientModel):
    _name = 'car.checkin.wizard'
    _description = 'معالج دخول سيارة جديدة'

    partner_id = fields.Many2one('res.partner', string='العميل', required=True)
    vehicle_id = fields.Many2one('customer.vehicle', string='السيارة (إن كانت مسجلة)', domain="[('partner_id', '=', partner_id)]")

    license_plate = fields.Char(string='رقم اللوحة', required=True)
    brand_id = fields.Many2one('fleet.vehicle.model.brand', string='الماركة')
    model_id = fields.Many2one('fleet.vehicle.model', string='الموديل', domain="[('brand_id', '=?', brand_id)]")
    model_year = fields.Selection([(str(y), str(y)) for y in range(1990, 2030)], string='سنة الصنع')

    current_odometer = fields.Float(string='قراءة العداد الحالية (كم)', required=True)
    customer_issue = fields.Text(string='شكوى العميل والملاحظات')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.license_plate = self.vehicle_id.license_plate
            self.brand_id = self.vehicle_id.brand_id
            self.model_id = self.vehicle_id.model_id
            self.model_year = self.vehicle_id.model_year

    def action_confirm_checkin(self):
        self.ensure_one()

        # 1. إنشاء أو تحديث السيارة
        vehicle = self.vehicle_id
        if not vehicle:
            vehicle = self.env['customer.vehicle'].create({
                'partner_id': self.partner_id.id,
                'license_plate': self.license_plate,
                'brand_id': self.brand_id.id,
                'model_id': self.model_id.id,
                'model_year': self.model_year,
                'last_odometer': self.current_odometer,
            })
        else:
            vehicle.write({'last_odometer': self.current_odometer})

        # 2. إنشاء حساب تحليلي مباشر
        analytic_plan = self.env['account.analytic.plan'].search([], limit=1)
        analytic_account = self.env['account.analytic.account'].create({
            'name': f"[{vehicle.license_plate}] - {self.partner_id.name}",
            'partner_id': self.partner_id.id,
            'plan_id': analytic_plan.id if analytic_plan else False,
        })

        # 3. إنشاء مشروع الزيارة
        project = self.env['project.project'].create({
            'name': f"صيانة [{vehicle.license_plate}] - {self.partner_id.name}",
            'partner_id': self.partner_id.id,
            'vehicle_id': vehicle.id,
            'analytic_account_id': analytic_account.id,
            'current_odometer': self.current_odometer,
            'customer_issue': self.customer_issue,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
            'target': 'current',
        }
