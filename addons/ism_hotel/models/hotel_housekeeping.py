from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HotelHousekeeping(models.Model):
    _name = 'hotel.housekeeping'
    _description = 'Hotel Housekeeping'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string="Task Number", required=True, copy=False, readonly=True, default=lambda self: _('New'))
    room_id = fields.Many2one('hotel.room', string="Room", required=True, tracking=True)
    assigned_to_id = fields.Many2one('res.users', string="Housekeeper", tracking=True)
    cleaning_type = fields.Selection([
        ('routine', 'Routine'),
        ('deep', 'Deep Cleaning'),
        ('checkout', 'Post-Checkout'),
        ('touchup', 'Touch Up')
    ], string="Cleaning Type", default='routine', required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string="Priority", default='1', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('cleaning', 'Cleaning'),
        ('done', 'Clean / Done'),
        ('inspected', 'Inspected'),
        ('cancelled', 'Cancelled')
    ], string="Status", default='draft', required=True, tracking=True)
    start_date = fields.Datetime(string="Start Time", tracking=True)
    end_date = fields.Datetime(string="End Time", tracking=True)
    notes = fields.Text(string="Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.housekeeping.number') or _('New')
        records = super(HotelHousekeeping, self).create(vals_list)
        for record in records:
            if record.room_id:
                record.room_id._compute_housekeeping_state_from_tasks()
        return records

    def write(self, vals):
        res = super(HotelHousekeeping, self).write(vals)
        if 'state' in vals or 'room_id' in vals:
            for record in self:
                if record.room_id:
                    record.room_id._compute_housekeeping_state_from_tasks()
        return res

    def action_assign(self):
        for record in self:
            if not record.assigned_to_id:
                raise UserError(_("Please assign a housekeeper first."))
            record.state = 'assigned'
            if record.room_id:
                record.room_id.housekeeping_state = 'dirty'

    def action_start(self):
        for record in self:
            record.state = 'cleaning'
            record.start_date = fields.Datetime.now()
            if record.room_id:
                record.room_id.housekeeping_state = 'cleaning'

    def action_done(self):
        for record in self:
            record.state = 'done'
            record.end_date = fields.Datetime.now()
            if record.room_id:
                record.room_id.housekeeping_state = 'clean'

    def action_inspect(self):
        for record in self:
            record.state = 'inspected'
            if record.room_id:
                record.room_id.housekeeping_state = 'clean'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'
            if record.room_id:
                record.room_id._compute_housekeeping_state_from_tasks()
