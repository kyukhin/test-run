from pathlib import Path

from lib import Options
from lib.log_helper import Log


class TestHangingXLog:

    def test_hanging_xlog(self, test_run_log: Log) -> None:
        """Check if tarantool is hanging it will be stopped by start_timeout.

        Check next patterns in the test-run log:
        There are (timeout // 10 - 1) lines with 'No output' warnings, which
        are going sequentially.
        There are no (timeout // 10)th line with same warning.
        Next, find log line with failing on start server timeout.
        Finally, check log contains '[ fail ]'.
        """

        timeout = Options().args.server_start_timeout
        no_output_timeout = Options().args.no_output_timeout
        assert Path(test_run_log.path).stat().st_size != 0
        for _ in range(10, timeout, 10):
            assert test_run_log.seek_wait(
                r"No output during \d+ seconds. "
                r"Will abort after {} seconds".format(no_output_timeout),
                start_from_beginning=False)
        assert not test_run_log.seek_wait(
                r"No output during {} seconds. "
                r"Will abort after {} seconds".format(
                    timeout, no_output_timeout),
                start_from_beginning=False, timeout=1)
        assert test_run_log.seek_wait(
            r"\[Instance 'replica'\] "
            r"Start timeout {} was reached.".format(timeout),
            start_from_beginning=False, timeout=1)
        assert test_run_log.seek_wait(
            r'\[ fail \]', start_from_beginning=False, timeout=1)

