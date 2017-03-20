# Imports
# #######


import os
import sys
import shutil
import atexit
import traceback

from options              import Options
from lib.tarantool_server import TarantoolServer
from lib.unittest_server  import UnittestServer
from lib.test_suite       import TestSuite
from lib.parallel         import Supervisor

from lib.colorer import Colorer
color_stdout = Colorer()

# Public interface
##################


__all__ = ['options'] # TODO; needed?


class Worker:
    def __init__(self, suite, _id):
        #color_stdout('DEBUG: Worker.__init__(suite=%s)\n' % suite.suite_path, schema='error')
        self.id = _id
        self.suite = suite
        self.name = '%02d_%s' % (self.id, self.suite.suite_path)
        self.suite.ini['vardir'] += '/' + self.name
        self.server = suite.gen_server()
        self.inspector = suite.start_server(self.server)

    def run_task(self, task):
        #color_stdout('DEBUG: Worker.run(); suite=%s\n' % self.suite.suite_path, schema='error')
        try:
            res = self.suite.run_test(task, self.server, self.inspector)
        except Exception as e:
            color_stdout('Worker "%s" received the following error (and ignored it):\n' \
                % self.name, schema='error')
            color_stdout(traceback.format_exc() + '\n', schema='error')
        # TODO: add res to output queue

    def run_all(self, task_queue):
        while True:
            task_name = task_queue.get()
            # None is 'stop worker' marker
            if not task_name:
                task_queue.task_done()
                return
            # find task by name
            # XXX: should we abstract it somehow? don't access certain field
            for cur_task in self.suite.tests:
                if cur_task.name == task_name:
                    task = cur_task
                    break
            res = self.run_task(task)
            # TODO: add res to output queue
            task_queue.task_done()

    def __del__(self):
        #color_stdout('DEBUG: Worker.__del__(); suite=%s\n' % self.suite.suite_path, schema='error')
        self.suite.stop_server(self.server, self.inspector)


def find_suites():
    suite_names = options.args.suites
    if suite_names == []:
        for root, dirs, names in os.walk(os.getcwd(), followlinks=True):
            if "suite.ini" in names:
                suite_names.append(os.path.basename(root))

    if options.args.stress is None:
        suites = [TestSuite(suite_name, options.args) for suite_name in sorted(suite_names)]
    else:
        suite_names = [suite_name for suite_name in suite_names if suite_name.find(options.args.stress) != -1]
        suites = [Supervisor(suite_name, options.args) for suite_name in sorted(suite_names)]
    return suites


def task_baskets():
    suites = find_suites()
    res = {}
    for suite in suites:
        key = os.path.basename(suite.suite_path)
        gen_worker = lambda _id, suite=suite: Worker(suite, _id)
        tasks = suite.find_tests()
        if tasks:
            res[key] = {
                'gen_worker': gen_worker,
                'tasks': tasks,
            }
    return res


# Package (de)initialization
############################


def setenv():
    """Find where is tarantool dir by check_file"""
    check_file = 'src/fiber.h'
    path = os.path.abspath('../')
    while path != '/':
        if os.path.isfile('%s/%s' % (path, check_file)):
            os.putenv('TARANTOOL_SRC_DIR', path)
            break
        path = os.path.abspath(os.path.join(path, '../'))


def module_init():
    """ Called at import """
    options = Options()
    oldcwd = os.getcwd()
    # Change the current working directory to where all test
    # collections are supposed to reside
    # If script executed with (python test-run.py) dirname is ''
    # so we need to make it .
    path = os.path.dirname(sys.argv[0])
    if not path:
        path = '.'
    os.chdir(path)
    setenv()

    # always run with clean (non-existent) 'var' directory
    try:
        shutil.rmtree(options.args.vardir)
    except OSError:
        pass

    options.args.builddir = os.path.abspath(os.path.expanduser(options.args.builddir))
    os.environ["SOURCEDIR"] = os.path.dirname(os.path.abspath(path))
    os.environ["BUILDDIR"] = os.path.abspath(options.args.builddir)

    TarantoolServer.find_exe(options.args.builddir) # XXX: can raise
    UnittestServer.find_exe(options.args.builddir)

    return (options, oldcwd)

@atexit.register
def module_del():
    """ Called before exit """
    os.chdir(oldcwd)


# Globals
#########


options, oldcwd = module_init()
