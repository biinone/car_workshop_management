# -*- coding: utf-8 -*-
{
    'name': 'Car Workshop Management',
    'version': '1.0',
    'summary': 'نظام إدارة ورش صيانة السيارات وتشغيل التكاليف المباشرة والعهد',
    'category': 'Services',
    'author': 'Custom Workshop',
    'depends': [
        'base',
        'sale_management',
        'project',
        'account',
        'fleet',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/customer_vehicle_views.xml',
        'views/res_partner_views.xml',
        'views/project_project_views.xml',
        'wizards/car_checkin_wizard_views.xml',
        'wizards/car_procurement_wizard_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
