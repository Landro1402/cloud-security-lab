import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import run_iam_lab as runner


ACCOUNT = "123456789012"
RUN_ID = "0123456789abcdef0123456789abcdef"

EXPECTED_KEYS = [
    f"training/iam-check-{RUN_ID}/sample.txt",
    f"private/iam-check-{RUN_ID}/sample.txt",
    f"training/iam-check-{RUN_ID}/upload.txt",
]


def success(payload=None):
    return subprocess.CompletedProcess(
        args=["aws"],
        returncode=0,
        stdout=json.dumps({} if payload is None else payload),
        stderr="",
    )


def failure(message):
    return subprocess.CompletedProcess(
        args=["aws"],
        returncode=254,
        stdout="",
        stderr=message,
    )


def preflight_responses():
    return [
        success({"Account": ACCOUNT}),
        success({
            "Arn": (
                f"arn:aws:sts::{ACCOUNT}:assumed-role/"
                "cloud-security-lab-training-reader/test"
            )
        }),
        success({}),
    ]


class RunnerTests(unittest.TestCase):
    def run_scenario(self, responses):
        arguments = [
            "run_iam_lab.py",
            "--bucket", "synthetic-test-bucket",
            "--account", ACCOUNT,
            "--operator-profile", "operator",
            "--reader-profile", "reader",
        ]

        with (
            patch.object(runner.sys, "argv", arguments),
            patch.object(
                runner,
                "uuid4",
                return_value=SimpleNamespace(hex=RUN_ID),
            ),
            patch.object(
                runner,
                "run_aws",
                side_effect=responses,
            ) as aws_mock,
            patch.object(
                runner.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0),
            ) as checker_mock,
            patch("builtins.print"),
        ):
            exit_code = runner.main()

        return exit_code, aws_mock, checker_mock

    def assert_cleanup_keys(self, aws_mock):
        deleted_keys = []

        for call in aws_mock.call_args_list:
            arguments, profile, region = call.args

            if (
                profile == "operator"
                and arguments[:2] == ["s3api", "delete-object"]
            ):
                key = arguments[arguments.index("--key") + 1]
                deleted_keys.append(key)

        self.assertEqual(deleted_keys, EXPECTED_KEYS)

    def test_success_cleans_up_all_run_keys(self):
        responses = preflight_responses() + [
            success(),                   # Training upload
            success(),                   # Private upload
            failure("(AccessDenied)"),   # Reader upload
            failure("(AccessDenied)"),   # Reader deletion
            success(),                   # Training cleanup
            success(),                   # Private cleanup
            success(),                   # Upload-target cleanup
        ]

        exit_code, aws_mock, checker_mock = self.run_scenario(
            responses
        )

        self.assertEqual(exit_code, 0)
        self.assert_cleanup_keys(aws_mock)
        checker_mock.assert_called_once()
        command = checker_mock.call_args.args[0]
        selected_profile = command[command.index("--profile") + 1]
        self.assertEqual(selected_profile, "reader")

    def test_partial_upload_failure_still_cleans_up(self):
        responses = preflight_responses() + [
            success(),                   # Training upload
            failure("Upload failed"),    # Private upload
            success(),                   # Training cleanup
            success(),                   # Private cleanup
            success(),                   # Upload-target cleanup
        ]

        exit_code, aws_mock, checker_mock = self.run_scenario(
            responses
        )

        self.assertEqual(exit_code, 2)
        self.assert_cleanup_keys(aws_mock)
        checker_mock.assert_not_called()

    def test_cleanup_failure_does_not_skip_remaining_keys(self):
        responses = preflight_responses() + [
            success(),
            success(),
            failure("(AccessDenied)"),
            failure("(AccessDenied)"),
            failure("Cleanup failed"),   # First cleanup fails
            success(),                   # Still attempt second
            success(),                   # Still attempt third
        ]

        exit_code, aws_mock, checker_mock = self.run_scenario(
            responses
        )

        self.assertEqual(exit_code, 2)
        self.assert_cleanup_keys(aws_mock)

    def test_unexpected_reader_upload_returns_failure(self):
        responses = preflight_responses() + [
            success(),                   # Training fixture upload
            success(),                   # Private fixture upload
            success(),                   # Reader upload unexpectedly allowed
            failure("(AccessDenied)"),   # Reader deletion denied
            success(),                   # Training cleanup
            success(),                   # Private cleanup
            success(),                   # Unexpected upload cleanup
        ]

        exit_code, aws_mock, checker_mock = self.run_scenario(
            responses
        )

        self.assertEqual(exit_code, 1)
        self.assert_cleanup_keys(aws_mock)

    def test_unexpected_reader_deletion_returns_failure(self):
        responses = preflight_responses() + [
            success(),                   # Training fixture upload
            success(),                   # Private fixture upload
            failure("(AccessDenied)"),   # Reader upload denied
            success(),                   # Reader deletion unexpectedly allowed
            success(),                   # Training cleanup
            success(),                   # Private cleanup
            success(),                   # Upload-target cleanup
        ]

        exit_code, aws_mock, checker_mock = self.run_scenario(
            responses
        )

        self.assertEqual(exit_code, 1)
        self.assert_cleanup_keys(aws_mock)


if __name__ == "__main__":
    unittest.main()