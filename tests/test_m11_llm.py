"""Executable offline adapter contracts required by the M13 planner."""

from dataclasses import asdict
import json
import unittest

from futureos.llm_provider import (
    FakeLLMProvider, LLMMessage, LLMProvider, LLMRequest, LLMResponse,
    LLMUnavailable, ProviderError, UsageMetadata,
)
from futureos.llm_registry import Registry


class LLMAdapterTests(unittest.TestCase):
    def request(self, size=7):
        return LLMRequest(
            messages=[LLMMessage("system", "Propose a synthetic population."),
                      LLMMessage("user", "A generic description for human review.")],
            metadata={"purpose": "population_plan", "population_size": size},
        )

    def test_fake_default_is_structured_generic_and_respects_requested_size(self):
        provider = FakeLLMProvider()
        response = provider.generate(self.request())
        self.assertIsInstance(response, LLMResponse)
        body = json.loads(response.content)
        self.assertEqual(body["size"], 7)
        self.assertEqual(body["source"], "llm_generated")
        self.assertEqual(body["archetypes"][0]["id"], "synthetic_default")
        self.assertEqual(body["warnings"], ["SYNTHETIC_POPULATION", "UNCALIBRATED_POPULATION"])
        self.assertTrue(body["assumptions"])
        self.assertEqual(response.provider, "fake")
        self.assertEqual(response.model, "fake-population-v1")
        default = LLMRequest([LLMMessage("user", "Generic")], metadata={"purpose": "population_plan"})
        self.assertEqual(json.loads(provider.generate(default).content)["size"], 100)
        self.assertEqual(json.loads(provider.generate(self.request(None)).content)["size"], 100)

    def test_configured_responses_allow_success_and_malformed_output_tests(self):
        for body in ({"key": "value"}, "{malformed", LLMResponse("{}", model="test")):
            response = FakeLLMProvider(body).generate(self.request())
            self.assertIsInstance(response, LLMResponse)
            if isinstance(body, dict):
                self.assertEqual(json.loads(response.content), body)
            elif isinstance(body, str):
                self.assertEqual(response.content, body)
            else:
                self.assertEqual(response, body)

    def test_request_record_is_independent_and_only_kept_in_memory(self):
        provider = FakeLLMProvider()
        request = self.request()
        provider.generate(request)
        request.metadata["population_size"] = 1000
        request.messages.append(LLMMessage("user", "Later change"))
        self.assertEqual(provider.requests[0].metadata["population_size"], 7)
        self.assertEqual(len(provider.requests[0].messages), 2)

    def test_provider_error_is_explicit(self):
        provider = FakeLLMProvider(error=ProviderError("offline failure"))
        with self.assertRaisesRegex(ProviderError, "offline failure"):
            provider.generate(self.request())
        self.assertEqual(len(provider.requests), 1)
        with self.assertRaises(ProviderError):
            FakeLLMProvider().generate("not a request")

    def test_registry_selects_registered_instance_and_class(self):
        registry = Registry()
        self.assertIsInstance(registry.get("fake"), FakeLLMProvider)
        instance = FakeLLMProvider({"fixture": True})
        registry.register("fixture", instance)
        self.assertIs(registry.get("fixture"), instance)
        registry.register("fake-class", FakeLLMProvider)
        self.assertIsInstance(registry.get("fake-class"), LLMProvider)

    def test_registry_rejects_unknown_duplicate_and_invalid_providers(self):
        registry = Registry()
        with self.assertRaises(LLMUnavailable):
            registry.get("unconfigured")
        with self.assertRaises(ValueError):
            registry.register("fake", FakeLLMProvider())
        for name, provider in ((" ", FakeLLMProvider), ("invalid", object()),
                               ("base", LLMProvider)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                registry.register(name, provider)

    def test_initialization_error_does_not_expose_credential_text(self):
        class BrokenProvider(LLMProvider):
            def __init__(self):
                raise RuntimeError("authorization: private-fixture-value")

        registry = Registry()
        registry.register("broken", BrokenProvider)
        with self.assertRaises(LLMUnavailable) as caught:
            registry.get("broken")
        self.assertNotIn("private-fixture-value", str(caught.exception))

    def test_contracts_reject_invalid_types_and_metadata(self):
        with self.assertRaises(ValueError):
            LLMMessage("tool", "unsupported")
        with self.assertRaises(ValueError):
            LLMRequest([])
        with self.assertRaises(ValueError):
            LLMRequest(["raw"])
        with self.assertRaises(ValueError):
            LLMRequest([LLMMessage("user", "test")], metadata={"value": float("nan")})
        with self.assertRaises(ValueError):
            UsageMetadata(input_tokens=True)
        with self.assertRaises(ValueError):
            LLMResponse("{}", usage={})
        with self.assertRaises(ProviderError):
            FakeLLMProvider().generate(self.request(True))

    def test_response_has_only_public_provenance_and_optional_usage(self):
        response = FakeLLMProvider().generate(self.request())
        data = asdict(response)
        self.assertEqual(set(data), {"content", "provider", "model", "usage"})
        self.assertNotIn("authorization", json.dumps(data).lower())
        self.assertIsNone(response.usage.input_tokens)
        self.assertIsNone(response.usage.output_tokens)


if __name__ == "__main__":
    unittest.main()
