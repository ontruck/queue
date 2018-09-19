# -*- coding: utf-8 -*-
# Copyright 2018 Ismael Calvo <ismael.calvo@ontruck.com>

from openerp import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class JobGroup(models.Model):
    _name = 'queue.job.group'
    _order = 'id desc'

    name = fields.Char(readonly=True)
    group_type = fields.Char()
    jobs = fields.One2many('queue.job', inverse_name='group')
    jobs_count = fields.Integer(readonly=True)
    jobs_in_progress_count = fields.Integer(readonly=True)
    jobs_done_count = fields.Integer(readonly=True)
    jobs_failed_count = fields.Integer(readonly=True)
    state = fields.Selection([
        ('in_progress', 'In progress'),
        ('done_with_fails', 'Done with fails'),
        ('failed', 'Failed'),
        ('done', 'Done')], readonly=True)
    progress = fields.Float(readonly=True)
    date_started = fields.Datetime(string='Start Date', readonly=True)
    date_done = fields.Datetime(string='Date Done', readonly=True)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('queue.job.group')
        return super(JobGroup, self).create(vals)

    @api.multi
    def check_state(self):
        for group in self:
            in_progress = 0
            done = 0
            failed = 0
            for job in group.jobs:
                if job.state in ['pending', 'enqueued', 'started']:
                    in_progress += 1
                elif job.state == 'done':
                    done += 1
                else:
                    failed += 1

            if in_progress > 0:
                state = 'in_progress'
            elif in_progress == 0 and failed == 0 and done > 0:
                state = 'done'
            elif in_progress == 0 and failed > 0:
                state = 'done_with_fails'
            else:
                state = 'failed'

            progress = 1.0 * done / (len(group.jobs) or 1) * 100
            data = {
                'jobs_count': len(group.jobs),
                'jobs_in_progress_count': in_progress,
                'jobs_done_count': done,
                'jobs_failed_count': failed,
                'state': state,
                'progress': progress,
            }
            if progress == 100:
                data['date_done'] = group.jobs[0].date_done
            group.write(data)

    @api.multi
    def retry_jobs(self):
        for group in self:
            jobs = self.env['queue.job'].search([
                ('group', '=', group.id),
                ('state', 'in', ['enqueued', 'started', 'failed'])
            ])
            jobs.requeue()

    @api.multi
    def cancel_jobs(self):
        for group in self:
            jobs = self.env['queue.job'].search([
                ('group', '=', group.id),
                ('state', 'not in', ['done'])
            ])
            jobs.button_done()

    @api.multi
    def reload_group(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
