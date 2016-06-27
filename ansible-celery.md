由于服务器更新代码都是通过广域网，`ansible`的`subversion`模块返回执行结果相对较慢，需要等待数秒才能返回http请求，于是考虑使用队列的方式，请求之后放入队列，队列任务更新完成之后更新操作结果到数据库，`celery`正好派上用场。
### 安装

    pip install --upgrade celery django-celery ansible

开始一个django测试项目，`django-admin startproject demo`，添加以下到`demo/settings.py`

    import djcelery
    djcelery.setup_loader()

    BROKER_URL = 'localhost'
    BROKER_BACKEND = 'redis'
    BROKER_USER = ''
    BROKER_PASSWORD = ''

    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_CONNECT_RETRY = True

    CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
    CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

    INSTALLED_APPS += [
        'djcelery',
        'kombu.transport.django',
    ]

再添加`demo/celery.py`文件

    from __future__ import absolute_import

    import os
    from celery import Celery
    from django.conf import settings

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'demo.settings')

    app = Celery('demo')
    app.config_from_object('django.conf:settings')
    app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

新建app01，`python manage.py startapp app01`，新建`app01/tasks.py`
`ansible` < 2.0的栗子大概是这样子

    from celery.task import task
    from ansible.runner import Runner

    @task
    def get_runner_callback(module_name, module_args, pattern, forks, remote_user):
        runner = Runner(module_name=module_name,
            module_args=module_args,
            pattern=pattern,
            forks=forks,
            remote_user=remote_user)
        datastructure = runner.run()
        return datastructure

`ansible` >= 2.0的另外一个栗子大概是这样子

    from .ansible_api import MyRunner # 封装的官方的类

    @task
    def get_runner_callback2(task_name, host_list, module_name, module_args, remote_user, become_method, become_user):
        ...
        return MyRunner(task_name, host_list, module_name, module_args, remote_user, become_method, become_user)

开启celery worker

    python manage.py celery worker -l info

测试任务队列

    get_runner_callback.delay(**kwargs) 正常
    get_runner_callback2.delay(**kwargs) 报错
    result = tqm.run(play)
    File "/usr/local/lib/python2.7/site-packages/ansible/executor/task_queue_manager.py", line 212, in run
    self._initialize_processes(min(contenders))
    File "/usr/local/lib/python2.7/site-packages/ansible/executor/task_queue_manager.py", line 108, in _initialize_processes
    self._result_prc.start()
    File "/usr/local/lib/python2.7/multiprocessing/process.py", line 124, in start
    'daemonic processes are not allowed to have children'
    AssertionError: daemonic processes are not allowed to have children

查找到[issue][1]，@xiaods的comment，`export PYTHONOPTIMIZE=1`之后再次测试任务队列就正常了。

关于[PYTHONOPTIMIZE][2], To be honest, it confused me.
查看执行结果

    ret=get_runner_callback2(**kwargs)
    ret.status/ret.state
    ret.info/ret.result
    ret_code, callback = ret.result

[1]: https://github.com/celery/celery/issues/1709
[2]:https://docs.python.org/2/using/cmdline.html#envvar-PYTHONOPTIMIZE
