"""
"""

import os
import unittest
from pathlib import Path

# path_to_homework_1_Log_Analyzer = str(Path(__file__).resolve().parent.parent.parent)
# sys.path.append(path_to_homework_1_Log_Analyzer)
# sys.path.append(path_to_homework_1_Log_Analyzer)

from homework_1_Log_Analyzer.log_analyzer.log_analyzer import main
from test.test_homework_1.line_format_config import LINE_LOG_FORMAT

BASE_PATH = Path(__file__).resolve().parent  # уровень tests

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": str(BASE_PATH / "reports"),
    "LOG_DIR": str(BASE_PATH / "log"),
    "LINE_LOG_FORMAT": LINE_LOG_FORMAT,
    "PARSING_ERROR_LIMIT_PERC": 10,
    "PROGRESS_INFORM_MODE": 1,
    "LOGS_REPORT_PATH": str(BASE_PATH / "logs_report" / "py_log.log"),
    # "LOGS_REPORT_PATH": None,
}


class Test(unittest.TestCase):
    def setUp(self) -> None:
        self.report_file_path = str(BASE_PATH / "reports" / "report-2017.05.30.html")

    def test_fail_parsing(self):
        config["LOG_DIR"] = str(BASE_PATH / "log_fail")

        try:
            main(config)
        except SystemError:
            self.assertTrue(True)

    def test_success_parsing(self):
        config["LOG_DIR"] = str(BASE_PATH / "log_seccess")
        main(config)

        with open(self.report_file_path) as f:
            report_file_exist = f is not None
        self.assertTrue(report_file_exist)

    def tearDown(self):
        if os.path.exists(self.report_file_path):
            os.remove(self.report_file_path)


if __name__ == "__main__":
    unittest.main()
