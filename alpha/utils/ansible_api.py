#!/usr/bin/env python
# -*- coding:utf-8 -*-

from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase

Options = namedtuple('Options', ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection', 'module_path', 'forks', 'remote_user', 'private_key_file',
                                 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user', 'verbosity', 'check'])


class HostPatternError(BaseException):
    pass


class ResultsCollector(CallbackBase):

    def __init__(self, *args, **kwargs):
        super(ResultsCollector, self).__init__(*args, **kwargs)
        self._host_unreachable = {}
        self._host_ok = {}
        self._host_failed = {}
        # verbose mode (-vvv for more, -vvvv to enable connection debugging)
        # self._display.verbosity = 4

    def v2_runner_on_unreachable(self, result):
        self._host_unreachable[result._host.get_name()] = result

    def v2_runner_on_ok(self, result,  *args, **kwargs):
        self._host_ok[result._host.get_name()] = result

    def v2_runner_on_failed(self, result,  *args, **kwargs):
        self._host_failed[result._host.get_name()] = result

    def host_unreachable(self):
        return self._host_unreachable

    def host_ok(self):
        return self._host_ok

    def host_failed(self):
        return self._host_failed


class MyRunner(object):

    def __init__(self, task_name, host_list, module_name, module_args='', gather_facts='no', task_list=None, **kwargs):
        self.task_name = task_name
        self.host_list = host_list
        self.module_name = module_name
        self.module_args = module_args
        self.gather_facts = gather_facts
        self.task_list = task_list
        self.playbook = kwargs.get('playbook', None)
        self.inventory_file = kwargs.get(
            'inventory_file', '/etc/ansible/hosts')
        self.options = Options(
            listtags=kwargs.get('listtags', False),
            listtasks=kwargs.get('listtasks', False),
            listhosts=kwargs.get('listhosts', False),
            syntax=kwargs.get('syntax', False),
            connection=kwargs.get('connection', 'ssh'),
            module_path=kwargs.get('module_path', None),
            forks=kwargs.get('forks', 100),
            remote_user=kwargs.get('remote_user', 'root'),
            private_key_file=kwargs.get('private_key_file', None),
            ssh_common_args=kwargs.get('ssh_common_args', None),
            ssh_extra_args=kwargs.get('ssh_extra_args', None),
            sftp_extra_args=kwargs.get('sftp_extra_args', None),
            scp_extra_args=kwargs.get('scp_extra_args', None),
            become=kwargs.get('become', True),
            become_method=kwargs.get('become_method', 'su'),
            become_user=kwargs.get('become_user', 'root'),
            verbosity=kwargs.get('verbosity', None),
            check=kwargs.get('check', False)
        )

        self.variable_manager = self.initialize_variable_manager()
        self.loader = self.initialize_loader()
        self.passwords = self.initialize_passwords()
        self.inventory = self.initialize_inventory()
        for pattern in self.host_list.split(','):
            if len(self.inventory.get_hosts(pattern)) == 0:
                raise HostPatternError(
                    'ERROR! Specified hosts \033[91m{}\033[0m options do not match any hosts'.format(pattern))

    def initialize_variable_manager(self):
        return VariableManager()

    def initialize_loader(self):
        return DataLoader()

    def initialize_passwords(self):
        return dict(vault_pass='secret')

    def initialize_inventory(self):
        return Inventory(
            loader=self.loader,
            variable_manager=self.variable_manager,
            host_list=self.inventory_file
        )

    def create_play_tasks(self):
        if not self.playbook:
            return dict(
                name=self.task_name,
                hosts=self.host_list,
                gather_facts=self.gather_facts,
                tasks=self.get_task_list()
            )
        return self.playbook

    def get_task_list(self):
        if not self.task_list:
            return [
                dict(action=dict(module=self.module_name,
                                 args=self.module_args))
            ]
        return self.task_list

    def run(self):
        self.variable_manager.set_inventory(self.inventory)
        play = Play().load(self.create_play_tasks(),
                           variable_manager=self.variable_manager, loader=self.loader)
        tqm = None
        callback = ResultsCollector()

        tqm = TaskQueueManager(
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=self.passwords
        )
        tqm._stdout_callback = callback
        result = tqm.run(play)

        return result, callback


def gather_facts(result):
    ansible_facts = result._result['ansible_facts']
    return dict(
        hostname=ansible_facts['ansible_hostname'],
        ipv4_address=ansible_facts['ansible_default_ipv4']['address'],
        macaddress=ansible_facts['ansible_default_ipv4']['macaddress'],
        processor=tuple(set(ansible_facts['ansible_processor'])),
        processor_count=ansible_facts['ansible_processor_vcpus'],
        product_name=ansible_facts['ansible_product_name'],
        lsb_desc=ansible_facts['ansible_lsb']['description'],
        memtotal_mb=ansible_facts['ansible_memtotal_mb'],
        memfree_mb=ansible_facts['ansible_memfree_mb'],
        sn=ansible_facts['ansible_product_serial'],
    )

"""
_, callback = MyRunner('gathers_facts', 'host_pattern', module_name='setup').run()
for host, result in callback.host_ok.items():
    Host.objects.filter(hostname__iexact=host).update(**gather_facts(result))
"""
