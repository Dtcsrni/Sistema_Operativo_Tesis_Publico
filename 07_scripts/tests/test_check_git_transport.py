import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from check_git_transport import is_ssh_auth_success  # noqa: E402


class TestCheckGitTransport(unittest.TestCase):
    def test_success_phrase_with_exit_code_one_is_valid(self):
        stdout = "Hi Dtcsrni! You've successfully authenticated, but GitHub does not provide shell access."
        self.assertTrue(is_ssh_auth_success(stdout, "", 1))

    def test_permission_denied_is_invalid(self):
        stderr = "git@ssh.github.com: Permission denied (publickey)."
        self.assertFalse(is_ssh_auth_success("", stderr, 255))


if __name__ == "__main__":
    unittest.main()
