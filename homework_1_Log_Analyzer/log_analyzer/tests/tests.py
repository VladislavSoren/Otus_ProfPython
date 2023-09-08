"""
"""
import sys

import os
import re
import unittest
from pathlib import Path

from homework_1_Log_Analyzer.log_analyzer.log_analyzer import main

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "line_log_format": re.compile(
        r"""(?P<ipaddress>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) (?P<remote_user>(-|\S+))  - \[(?P<dateandtime>\d{2}\/[a-z]{3}\/\d{4}:\d{2}:\d{2}:\d{2} (\+|\-)\d{4})\] (\"(GET|POST) )(?P<url>.+)(http\/[1-2]\.[0-9]") (?P<statuscode>\d{3}) (?P<bytessent>\d+) (?P<refferer>-|"([^"]+)") (["](?P<useragent>[^"]+)["]) (?P<forwarded_for>"([^"]+)") (?P<request_id>"([^"]+)") (?P<rb_user>"([^"]+)") (?P<request_time>\d+\.\d{3})""",
        re.IGNORECASE),
    "parsing_error_limit_perc": 10,
    "progress_inform_mode": 1,
    "logs_report_path": str(Path('logs_report') / "py_log.log"),
    # "logs_report_path": None,
}


class Test(unittest.TestCase):

    def setUp(self) -> None:
        self.report_file_path = str(Path('reports') / 'report-2017.05.30.html')

    def test_fail_parsing(self):
        config['LOG_DIR'] = './log_fail'

        try:
            main(config)
        except SystemError as e:
            self.assertTrue(True)

    def test_success_parsing(self):
        config['LOG_DIR'] = './log_seccess'
        main(config)

        with open(self.report_file_path) as f:
            report_file_exist = f is not None
        self.assertTrue(report_file_exist)

    def tearDown(self):
        if os.path.exists(self.report_file_path):
            os.remove(self.report_file_path)


if __name__ == '__main__':
    unittest.main()
