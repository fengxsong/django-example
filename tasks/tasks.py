import copy
from celery.task import task

from alpha.utils import MyRunner
from .models import RepoResult


def del_invocation(x):
    x1 = copy.deepcopy(x)
    x1.pop('invocation', None)
    return x1


def g_results(ret_code, callback, func, model, **kwargs):
    hosts = filter(lambda x: x if x() else None, [
                   callback.host_ok, callback.host_failed, callback.host_unreachable])
    results = map(func, hosts)
    model.objects.create(ret_code=ret_code, results=results, **kwargs)
    return results


@task
def repo_runner(user, repo, *args, **kwargs):
    ret_code, callback = MyRunner(**kwargs).run()
    results = g_results(ret_code, callback,
                        func=lambda x: {h: del_invocation(
                            r._result) for (h, r) in x().items()},
                        model=RepoResult,
                        repo=repo,
                        executor=user)
    if ret_code == 0:
        result = callback.host_ok.values()[0]
        repo.revision = result._result.get('after')[0].split(':')[1].strip()
        repo.save()
    return ret_code, results
