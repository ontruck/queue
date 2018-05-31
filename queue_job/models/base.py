# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import inspect

from openerp import api, models, SUPERUSER_ID, _
from ..job import DelayableRecordset


@api.cr_uid_context
def _register_hook(self, cr, context=None):
    """Register marked jobs."""
    # super(Model, self)._register_hook(cr)
    if not context:
        context = {}
    job_methods = [
        method for __, method
        in inspect.getmembers(self.__class__, predicate=inspect.ismethod)
        if getattr(method, 'delayable', None)
    ]
    for job_method in job_methods:
        self.pool('queue.job.function')._register_job(
            cr, SUPERUSER_ID, job_method, context=context)
    # add_to_job_registry(job_methods)


@api.multi
def with_delay(self, priority=None, eta=None,
               max_retries=None, description=None,
               channel=None):
    """Return a ``DelayableRecordset``.

    The returned instance allow to enqueue any method of the recordset's
    Model which is decorated by :func:`~openerp.addons.queue_job.job.job`.

    Usage::

        self.env['res.users'].with_delay().write({'name': 'test'})

    In the line above, in so far ``write`` is allowed to be delayed with
    ``@job``, the write will be executed in an asynchronous job.


    :param priority: Priority of the job, 0 being the higher priority.
                     Default is 10.
    :param eta: Estimated Time of Arrival of the job. It will not be
                executed before this date/time.
    :param max_retries: maximum number of retries before giving up and set
                        the job state to 'failed'. A value of 0 means
                        infinite retries.  Default is 5.
    :param description: human description of the job. If None, description
                        is computed from the function doc or name
    :param channel: the complete name of the channel to use to process
                    the function. If specified it overrides the one
                    defined on the function
    :return: instance of a DelayableRecordset
    :rtype: :class:`openerp.addons.queue_job.job.DelayableRecordset`

    """
    return DelayableRecordset(self, priority=priority,
                              eta=eta,
                              max_retries=max_retries,
                              description=description,
                              channel=channel)


@api.multi
def delay_group(self, func, priority=None, eta=None, max_retries=None,
                description=None, channel=None, **kwargs):
    group = self.env['queue.job.group'].create({})
    for obj in self:
        delayable = obj.with_delay(priority=priority,
                                   eta=eta,
                                   max_retries=max_retries,
                                   description=description,
                                   channel=channel)
        job = delayable.__getattr__(func)(**kwargs)
        job.db_record().group = group.id
    return {
        'name': _("Job group"),
        'type': 'ir.actions.act_window',
        'res_model': 'queue.job.group',
        'res_id': group.id,
        'view_mode': 'form,tree',
        'view_type': 'tree',
        'target': 'current',
    }


models.Model._register_hook = _register_hook
models.Model.with_delay = with_delay
models.Model.delay_group = delay_group
