import pytest
import psutil
from pathlib import Path
from gevent import subprocess
from lib import Options
from lib.log_helper import Log

TEST_RUN_NAMES = {
    'test_hanging_xlog': 'hang.test.lua'
}


@pytest.yield_fixture(scope="session", autouse=True)
def clean_all_subprocesses() -> None:
    """Kill remained subprocess. Raise an exception for not killed procs."""
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    yield
    not_terminated_processes = []
    for child in children:
        if psutil.pid_exists(child.pid):
            not_terminated_processes.append(child)
            child.terminate()
    if not_terminated_processes:
        raise Exception(
            "Next processes were not terminated: {}\n".format(
                not_terminated_processes))


@pytest.fixture
def test_run_log(path_to_test_run_log: Path) -> Log:
    """Return test-run log file as Log object"""
    test_run_log = Log(path_to_test_run_log)
    return test_run_log


@pytest.yield_fixture
def path_to_test_run_log(test_run_name: str) -> Path:
    """Execute test and return path to test-run log."""
    dir_path = Path(__file__).resolve().parent
    with open(dir_path / 'outfile.txt', 'w') as file:
        test = subprocess.Popen(
            ['../../test/test-run.py', test_run_name],
            cwd=dir_path, stdout=file)
        test.wait(timeout=Options().args.no_output_timeout + 10)
    yield Path(dir_path / 'outfile.txt')
    test.kill()


@pytest.fixture
def test_run_name(request):
    """Return name of test in test-run suite for current pytest test."""
    return TEST_RUN_NAMES[request.node.name]
