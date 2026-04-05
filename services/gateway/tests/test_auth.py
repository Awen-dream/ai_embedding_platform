import unittest

from embedding_platform_common.auth import is_api_key_valid


class AuthHelpersTest(unittest.TestCase):
    def test_is_api_key_valid_accepts_matching_value(self) -> None:
        self.assertTrue(is_api_key_valid("local-dev-key", "local-dev-key"))

    def test_is_api_key_valid_rejects_wrong_value(self) -> None:
        self.assertFalse(is_api_key_valid("local-dev-key", "wrong-key"))
