import json
import os
import tempfile
import unittest

from fastapi import HTTPException

import main


class ApiContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_token_file = main.TOKEN_FILE
        self.original_api_key = main.API_KEY
        main.API_KEY = "test-key"

    def tearDown(self):
        main.TOKEN_FILE = self.original_token_file
        main.API_KEY = self.original_api_key

    def test_verify_api_key_requires_header(self):
        with self.assertRaises(HTTPException) as ctx:
            main.verify_api_key(None)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Missing X-API-Key", ctx.exception.detail)

    def test_verify_api_key_rejects_bad_key(self):
        with self.assertRaises(HTTPException) as ctx:
            main.verify_api_key("wrong-key")

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Invalid API key", ctx.exception.detail)

    async def test_health_token_missing_token_file(self):
        main.TOKEN_FILE = "/tmp/googleapp_missing_token_test.json"
        if os.path.exists(main.TOKEN_FILE):
            os.remove(main.TOKEN_FILE)

        with self.assertRaises(HTTPException) as ctx:
            await main.health_token(auth=True)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("token_missing", ctx.exception.detail)

    async def test_health_token_invalid_format(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            json.dump({"token": "x"}, f)
            temp_path = f.name

        try:
            main.TOKEN_FILE = temp_path
            with self.assertRaises(HTTPException) as ctx:
                await main.health_token(auth=True)

            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("token_invalid_format", ctx.exception.detail)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def test_read_emails_missing_token_returns_401(self):
        main.TOKEN_FILE = "/tmp/googleapp_missing_token_test.json"
        if os.path.exists(main.TOKEN_FILE):
            os.remove(main.TOKEN_FILE)

        with self.assertRaises(HTTPException) as ctx:
            await main.read_emails(auth=True)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Token non trovato", ctx.exception.detail)

    async def test_write_email_with_uploads_missing_token_returns_401(self):
        main.TOKEN_FILE = "/tmp/googleapp_missing_token_test.json"
        if os.path.exists(main.TOKEN_FILE):
            os.remove(main.TOKEN_FILE)

        with self.assertRaises(HTTPException) as ctx:
            await main.write_and_send_email_with_uploads(
                auth=True,
                to="recipient@example.com",
                subject="Subject",
                body="Body",
                cc=None,
                bcc=None,
                files=None,
            )

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Token non trovato", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
