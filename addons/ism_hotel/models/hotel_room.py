from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HotelRoom(models.Model):
    _name = 'hotel.room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hotel Room'
    
    # TODO: add a new field called 'status' with the following options:
    STATUS_COLOR = {
        'available': 'success',
        'reserved': 'warning',
        'occupied': 'danger',
        'maintenance': 'info',
        'unavailable': 'dark',
    }

    # field model 
    name = fields.Char(string="Name", required=True)
    booking_count = fields.Integer(string="Booking Count", compute="_compute_booking_count", store=False)
    state = fields.Selection([
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('reserved', 'Reserved'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Maintenance'),
        ('unavailable', 'Unavailable'),
    ], string="State", default='available', store=True)
    housekeeping_state = fields.Selection([
        ('clean', 'Clean'),
        ('dirty', 'Dirty'),
        ('cleaning', 'Cleaning')
    ], string="Housekeeping Status", default='clean', tracking=True)
    housekeeping_count = fields.Integer(string="Housekeeping Tasks Count", compute="_compute_housekeeping_count")

    # field constraint 
    booking_ids = fields.Many2many('hotel.book.history', string="Booking History")
    room_type = fields.Many2one('product.template', string="Room Type", required=True)

    current_guest_name = fields.Char(string="Current Guest Name", compute="_compute_current_booking_info")

    def _compute_current_booking_info(self):
        for record in self:
            booking = self.env['hotel.book.history'].search([
                ('room_ids', 'in', record.id),
                ('state', '=', 'checked_in')
            ], limit=1)
            record.current_guest_name = booking.partner_id.name if booking else False

    # function compute booking > booking_ids 
    def _compute_booking_count(self):
        for record in self:
            record.booking_count = len(record.booking_ids)

    def _compute_housekeeping_count(self):
        for record in self:
            record.housekeeping_count = self.env['hotel.housekeeping'].search_count([('room_id', '=', record.id)])

    # action view reservation 
    def action_view_reservations(self):
        self.ensure_one()
        action = self.env.ref('ism_hotel.action_hotel_book_history_all').read()[0]
        action['domain'] = [('room_ids', 'in', self.id)]
        return action

    def action_view_housekeeping_tasks(self):
        self.ensure_one()
        return {
            'name': _('Housekeeping Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.housekeeping',
            'view_mode': 'tree,form,kanban',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }

    def _compute_housekeeping_state_from_tasks(self):
        for record in self:
            latest_task = self.env['hotel.housekeeping'].search([
                ('room_id', '=', record.id),
                ('state', 'not in', ['cancelled', 'inspected'])
            ], order='write_date desc', limit=1)
            if latest_task:
                if latest_task.state in ['draft', 'assigned']:
                    record.housekeeping_state = 'dirty'
                elif latest_task.state == 'cleaning':
                    record.housekeeping_state = 'cleaning'
                elif latest_task.state == 'done':
                    record.housekeeping_state = 'clean'
            else:
                record.housekeeping_state = 'clean'
    
    # button set to maintenance if occupied raised error 
    def action_maintenance(self):
        self.ensure_one()
        if self.state == 'occupied':
            raise UserError(_("You cannot set a room to maintenance while it is occupied."))
        
        self.state = 'maintenance'

    # button set available 
    def action_available(self):
        self.ensure_one()
        self.state = 'available'

    # function open booking form menu room 
    def open_booking_form(self):
        return {
            'name': 'Create Room Booking',
            'view_mode': 'form',
            'res_model': 'hotel.book.history',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {
                'active_room_id': self.id
            }
        }

    # function open checkin form menu room
    def open_checkin_form(self):
        booking_id = self._search_currently_booked_rooms()
        print('booking_id', booking_id)
        if booking_id:
            return {
                'name': _('Check In'),
                'view_mode': 'form',
                'res_model': 'hotel.book.history',
                'res_id': booking_id.id,
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': {
                    'active_id': booking_id.id
                },
            }
        else:
            raise UserError(_("There is no room currently occupied."))    

    # function open checkout form menu room
    def open_checkout_form(self):
        booking_id = self._search_currently_occupied_rooms()
        print('booking_id', booking_id)
        if booking_id:
            return {
                'name': _('Check Out'),
                'view_mode': 'form',
                'res_model': 'hotel.book.history',
                'res_id': booking_id.id,
                'type': 'ir.actions.act_window',
                'target': 'current',
                'context': {
                    'active_id': booking_id.id
                },
            }
        else:
            raise UserError(_("There is no room currently occupied."))

    # function search booked room
    def _search_currently_booked_rooms(self):
        room_id = self._context.get('default_room_id')
        # look for the first room booking that is available or reserved
        print('room_id', room_id)
        room_booking = self.env['hotel.book.history'].search([
            ('room_ids', 'in', room_id),
            ('state', '=', 'booked'),
        ], limit=1)
        return room_booking

    # function search occupied room
    def _search_currently_occupied_rooms(self):
        room_id = self._context.get('default_room_id')
        # look for the first room booking that is available or reserved
        print('room_id', room_id)
        room_booking = self.env['hotel.book.history'].search([
            ('room_ids', 'in', room_id),
            ('state', '=', 'checked_in'),
        ], limit=1)
        return room_booking