from __future__ import annotations

import unittest
from unittest.mock import patch

from services.vision_extractor import (
    AZURE_OPENAI_API_KEY_ENV,
    TitleBlockExtractionSchema,
    VisionExtractor,
    extraction_has_values,
    normalize_extraction,
)


class VisionExtractorHelpersTests(unittest.TestCase):
    def test_normalize_extraction_trims_empty_strings_to_none(self) -> None:
        normalized = normalize_extraction(
            TitleBlockExtractionSchema(
                drawing_number="  A-101  ",
                drawing_revision="   ",
                revision_date=" 2026-03-12 ",
                drawing_title="\nGround Floor Plan\t",
            )
        )

        self.assertEqual(normalized.drawing_number, "A-101")
        self.assertIsNone(normalized.drawing_revision)
        self.assertEqual(normalized.revision_date, "2026-03-12")
        self.assertEqual(normalized.drawing_title, "Ground Floor Plan")

    def test_extraction_has_values_requires_at_least_one_non_empty_field(self) -> None:
        self.assertFalse(extraction_has_values(TitleBlockExtractionSchema()))
        self.assertTrue(
            extraction_has_values(
                TitleBlockExtractionSchema(revision_date="2026-03-12")
            )
        )

    @patch('services.vision_extractor.AzureOpenAI')
    @patch('services.vision_extractor.get_bearer_token_provider')
    def test_vision_extractor_uses_api_key_when_configured(
        self,
        mock_token_provider,
        mock_azure_openai,
    ) -> None:
        extractor = VisionExtractor(
            endpoint='https://example.openai.azure.com/',
            deployment_name='gpt-4.1-mini',
            api_key='test-key',
            api_version='2024-08-01-preview',
        )

        self.assertTrue(extractor.is_configured)
        mock_token_provider.assert_not_called()
        mock_azure_openai.assert_called_once_with(
            api_version='2024-08-01-preview',
            azure_endpoint='https://example.openai.azure.com/',
            api_key='test-key',
            max_retries=0,
        )

    @patch.dict('os.environ', {AZURE_OPENAI_API_KEY_ENV: 'env-test-key'}, clear=False)
    @patch('services.vision_extractor.AzureOpenAI')
    @patch('services.vision_extractor.get_bearer_token_provider')
    def test_vision_extractor_reads_api_key_from_env(
        self,
        mock_token_provider,
        mock_azure_openai,
    ) -> None:
        extractor = VisionExtractor(
            endpoint='https://example.openai.azure.com/',
            deployment_name='gpt-4.1-mini',
            api_version='2024-08-01-preview',
        )

        self.assertTrue(extractor.is_configured)
        mock_token_provider.assert_not_called()
        mock_azure_openai.assert_called_once_with(
            api_version='2024-08-01-preview',
            azure_endpoint='https://example.openai.azure.com/',
            api_key='env-test-key',
            max_retries=0,
        )

    @patch('services.vision_extractor.AzureOpenAI')
    @patch('services.vision_extractor.get_bearer_token_provider')
    def test_vision_extractor_falls_back_to_token_provider_without_api_key(
        self,
        mock_token_provider,
        mock_azure_openai,
    ) -> None:
        mock_token_provider.return_value = 'token-provider'

        extractor = VisionExtractor(
            endpoint='https://example.openai.azure.com/',
            deployment_name='gpt-4.1-mini',
            api_version='2024-08-01-preview',
        )

        self.assertTrue(extractor.is_configured)
        mock_token_provider.assert_called_once()
        mock_azure_openai.assert_called_once_with(
            api_version='2024-08-01-preview',
            azure_endpoint='https://example.openai.azure.com/',
            azure_ad_token_provider='token-provider',
            max_retries=0,
        )


if __name__ == '__main__':
    unittest.main()
