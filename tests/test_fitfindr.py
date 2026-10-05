"""Offline contract checks using the bundled data and explicit model doubles.

These tests verify deterministic search, inputs, and control flow. The model
responses below are test doubles, not evidence for the five-trial acceptance
targets or for the quality of a real generated caption.

Run from the repository root: python -m unittest discover -s tests -v
"""

import copy
import math
import unittest
from unittest.mock import call, patch

import agent
import config
import tools
from generate import ModelUnavailable
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings


MATCHING_QUERY = "vintage graphic tee under $30, size M"


class OfflineTestCase(unittest.TestCase):
    """Fail immediately if a test accidentally reaches real generation."""

    def setUp(self):
        self.model = self.enterContext(
            patch("tools.generate", side_effect=AssertionError("Unexpected model call"))
        )
        self.listings = {item["id"]: item for item in load_listings()}
        self.item = self.listings["lst_002"]
        self.wardrobe = get_example_wardrobe()

    def allow_model(self, response):
        self.model.side_effect = None
        self.model.return_value = response

    def sent_prompt(self):
        args, kwargs = self.model.call_args
        return "\n".join(str(value) for value in (*args, *kwargs.values()))


class SearchTests(OfflineTestCase):
    def test_five_documented_size_and_price_cases(self):
        cases = [
            ("butterfly", "M", 18, "lst_002", {"M", "S/M", "M/L"}),
            ("flannel", "XL", 22, "lst_003", {"XL", "XL (oversized)"}),
            ("platform sneakers", "8", 48, "lst_019", {"US 8"}),
            ("jeans", "W30 L30", 38, "lst_001", {"W30 L30"}),
            ("track jacket", "M", 45, "lst_004", {"M", "S/M", "M/L"}),
        ]
        for description, size, ceiling, expected_id, allowed_sizes in cases:
            with self.subTest(description=description, size=size, ceiling=ceiling):
                matches = tools.search_listings(description, size, ceiling)
                self.assertIn(expected_id, [item["id"] for item in matches])
                for item in matches:
                    self.assertLessEqual(item["price"], ceiling)
                    self.assertIn(item["size"], allowed_sizes)
                    self.assertEqual(item, self.listings[item["id"]])

    def test_inclusive_price_boundary_and_lower_ceiling(self):
        self.assertEqual(
            [item["id"] for item in tools.search_listings("butterfly", "M", 18)],
            ["lst_002"],
        )
        self.assertEqual(tools.search_listings("butterfly", "M", 17.99), [])

    def test_size_tokens_do_not_match_inside_other_labels(self):
        for description, size in [
            ("flannel", "L"),
            ("shoes", "S"),
            ("boots", "8"),
            ("cardigan", "M"),
            ("jeans", "W30 L32"),
        ]:
            with self.subTest(description=description, size=size):
                self.assertEqual(tools.search_listings(description, size), [])

    def test_supported_composite_and_annotated_sizes(self):
        for description, size, expected_id in [
            ("butterfly", "m", "lst_002"),
            ("linen blazer", "M", "lst_018"),
            ("linen blazer", "L", "lst_018"),
            ("flannel", "xl", "lst_003"),
            ("boots", "US 8.5", "lst_028"),
            ("jeans", "W30", "lst_001"),
            ("cardigan", "One Size", "lst_008"),
        ]:
            with self.subTest(description=description, size=size):
                self.assertIn(
                    expected_id,
                    [item["id"] for item in tools.search_listings(description, size)],
                )

    def test_all_meaningful_terms_are_required(self):
        self.assertEqual(tools.search_listings("vintage ballgown"), [])
        self.assertEqual(tools.search_listings("designer ballgown", "XXS", 5), [])

    def test_blank_and_only_request_words_return_empty(self):
        for description in ["", "   ", "?!", "looking for a"]:
            with self.subTest(description=description):
                self.assertEqual(tools.search_listings(description), [])

    def test_case_punctuation_and_request_words(self):
        expected = tools.search_listings("vintage graphic tee", "M", 30)
        self.assertTrue(expected)
        self.assertEqual(
            tools.search_listings("Looking for a VINTAGE, GRAPHIC TEE!", "m", 30),
            expected,
        )

    def test_order_is_repeatable_and_limit_keeps_the_best_results(self):
        with patch.object(config, "SEARCH_RESULT_LIMIT", 40):
            all_matches = tools.search_listings("vintage")
        self.assertGreater(len(all_matches), 3)
        with patch.object(config, "SEARCH_RESULT_LIMIT", 3):
            first = tools.search_listings("vintage")
            second = tools.search_listings("vintage")
        self.assertEqual(first, second)
        self.assertEqual(first, all_matches[:3])

    def test_invalid_price_ceiling_is_rejected(self):
        for ceiling in [-1, math.inf, -math.inf, math.nan]:
            with self.subTest(ceiling=ceiling):
                with self.assertRaises(ValueError):
                    tools.search_listings("graphic tee", max_price=ceiling)


class QueryParsingTests(OfflineTestCase):
    def test_documented_queries_extract_constraints_in_either_order(self):
        cases = [
            (MATCHING_QUERY, "M", 30, ["vintage", "graphic", "tee"]),
            ("90s track jacket in size M", "M", None, ["90s", "track", "jacket"]),
            ("silk slip dress in midi length under $40", None, 40, ["silk", "slip", "dress"]),
            ("platform sneakers size 8", "8", None, ["platform", "sneakers"]),
            ("denim jacket under $50", None, 50, ["denim", "jacket"]),
            ("jeans size W30 L30 up to $38", "W30 L30", 38, ["jeans"]),
            ("under $48 platform sneakers size US 8", "US 8", 48, ["platform", "sneakers"]),
            ("cardigan max price 35 size One Size", "ONE SIZE", 35, ["cardigan"]),
            ("butterfly below 18 size M", "M", 18, ["butterfly"]),
            ("$18 butterfly size M", "M", 18, ["butterfly"]),
        ]
        for query, size, ceiling, words in cases:
            with self.subTest(query=query):
                parsed = agent.parse_query(query)
                self.assertEqual(set(parsed), {"description", "size", "max_price"})
                actual_size = parsed["size"]
                self.assertEqual(
                    actual_size.upper() if actual_size is not None else None,
                    size.upper() if size is not None else None,
                )
                self.assertEqual(parsed["max_price"], ceiling)
                for word in words:
                    self.assertIn(word, parsed["description"].lower())
                self.assertNotIn("$", parsed["description"])
                self.assertNotIn("size", parsed["description"].lower().split())


class ModelToolTests(OfflineTestCase):
    def test_outfit_passes_the_listing_and_real_wardrobe_to_adapter(self):
        self.allow_model("Offline outfit test double.")
        original_item = copy.deepcopy(self.item)
        original_wardrobe = copy.deepcopy(self.wardrobe)
        result = tools.suggest_outfit(self.item, self.wardrobe)
        self.assertEqual(result, "Offline outfit test double.")
        self.model.assert_called_once()
        prompt = self.sent_prompt()
        self.assertIn(self.item["id"], prompt)
        for item in self.wardrobe["items"]:
            self.assertIn(item["name"], prompt)
        self.assertEqual(self.item, original_item)
        self.assertEqual(self.wardrobe, original_wardrobe)

    def test_empty_wardrobe_requests_general_advice_without_owned_pieces(self):
        self.allow_model("Offline general-advice test double.")
        result = tools.suggest_outfit(self.item, get_empty_wardrobe())
        self.assertTrue(result.strip())
        self.model.assert_called_once()
        prompt = self.sent_prompt()
        self.assertIn(self.item["id"], prompt)
        self.assertRegex(prompt.lower(), r"general|styling ideas")
        self.assertRegex(prompt.lower(), r"empty|no wardrobe|no owned|not.*own|does not own")
        for item in self.wardrobe["items"]:
            self.assertNotIn(item["name"], prompt)

    def test_fit_card_receives_item_details_and_outfit(self):
        self.allow_model("Offline caption test double.")
        outfit = "Offline outfit with the supplied wardrobe pieces."
        result = tools.create_fit_card(outfit, self.item)
        self.assertEqual(result, "Offline caption test double.")
        self.model.assert_called_once()
        prompt = self.sent_prompt()
        self.assertIn(outfit, prompt)
        self.assertIn(self.item["id"], prompt)
        self.assertIn(str(self.item["price"]), prompt)
        self.assertIn(self.item["platform"], prompt)

    def test_absent_input_guards_do_not_call_model(self):
        self.assertEqual(
            tools.suggest_outfit({}, self.wardrobe),
            "Choose a listing before asking for an outfit.",
        )
        self.assertEqual(
            tools.create_fit_card("jeans and sneakers", {}),
            "Choose a listing before creating a fit card.",
        )
        for outfit in ["", " \n\t "]:
            self.assertEqual(
                tools.create_fit_card(outfit, self.item),
                "No outfit to caption. Generate an outfit suggestion first.",
            )
        self.model.assert_not_called()

    def test_blank_model_answers_are_not_successful_results(self):
        self.allow_model(" \n\t ")
        with self.assertRaises(ModelUnavailable):
            tools.suggest_outfit(self.item, self.wardrobe)
        with self.assertRaises(ModelUnavailable):
            tools.create_fit_card("jeans and sneakers", self.item)

    def test_model_unavailability_propagates_at_tool_boundary(self):
        self.model.side_effect = ModelUnavailable("Offline provider failure")
        with self.assertRaises(ModelUnavailable):
            tools.suggest_outfit(self.item, self.wardrobe)
        with self.assertRaises(ModelUnavailable):
            tools.create_fit_card("jeans and sneakers", self.item)


class PlanningLoopTests(OfflineTestCase):
    def test_happy_path_reads_and_records_the_same_session_values(self):
        outfit_text = "Offline outfit test double."
        card_text = "Offline caption test double."
        with (
            patch("agent.suggest_outfit", return_value=outfit_text) as outfit,
            patch("agent.create_fit_card", return_value=card_text) as card,
            patch("agent.trace.check_iterations", wraps=agent.trace.check_iterations) as guard,
        ):
            session = agent.run_agent(MATCHING_QUERY, self.wardrobe)
        self.assertIsNone(session["error"])
        selected = session["search_results"][0]
        self.assertEqual(selected["id"], "lst_002")
        self.assertEqual(session["selected_item"], selected)
        self.assertEqual(session["outfit_suggestion"], outfit_text)
        self.assertEqual(session["fit_card"], card_text)
        outfit.assert_called_once_with(new_item=selected, wardrobe=session["wardrobe"])
        card.assert_called_once_with(outfit=outfit_text, new_item=selected)
        calls = session["tool_calls"]
        self.assertEqual(
            [entry["tool"] for entry in calls],
            ["search_listings", "suggest_outfit", "create_fit_card"],
        )
        self.assertEqual(calls[0]["inputs"], session["parsed"])
        self.assertEqual(calls[1]["inputs"]["new_item"], selected)
        self.assertEqual(calls[1]["inputs"]["wardrobe"], session["wardrobe"])
        self.assertEqual(calls[2]["inputs"]["new_item"], selected)
        self.assertEqual(calls[2]["inputs"]["outfit"], outfit_text)
        self.assertEqual(guard.call_args_list, [call(1), call(2), call(3)])

        # The journal must keep actual input snapshots, not aliases that change
        # when a caller later changes the returned session.
        original_item = copy.deepcopy(selected)
        original_wardrobe = copy.deepcopy(session["wardrobe"])
        session["selected_item"]["price"] = -1
        session["selected_item"]["style_tags"].append("offline mutation")
        session["wardrobe"]["items"][0]["name"] = "offline mutation"
        self.assertEqual(calls[1]["inputs"]["new_item"], original_item)
        self.assertEqual(calls[2]["inputs"]["new_item"], original_item)
        self.assertEqual(calls[1]["inputs"]["wardrobe"], original_wardrobe)

    def test_no_match_stops_before_both_model_tools(self):
        with (
            patch("agent.suggest_outfit") as outfit,
            patch("agent.create_fit_card") as card,
        ):
            session = agent.run_agent("designer ballgown size XXS under $5", self.wardrobe)
        self.assertEqual(session["search_results"], [])
        self.assertIsNone(session["selected_item"])
        self.assertIsNone(session["outfit_suggestion"])
        self.assertIsNone(session["fit_card"])
        self.assertRegex(session["error"].lower(), r"keywords|size|budget")
        self.assertEqual([entry["tool"] for entry in session["tool_calls"]], ["search_listings"])
        outfit.assert_not_called()
        card.assert_not_called()

    def test_blank_outfit_stops_before_card(self):
        with (
            patch("agent.suggest_outfit", return_value=" \n "),
            patch("agent.create_fit_card") as card,
        ):
            session = agent.run_agent(MATCHING_QUERY, self.wardrobe)
        self.assertIsNotNone(session["selected_item"])
        self.assertIsNone(session["fit_card"])
        self.assertTrue(session["error"])
        card.assert_not_called()

    def test_model_failures_save_safe_errors_and_preserve_search_state(self):
        for failed_tool in ["suggest_outfit", "create_fit_card"]:
            with self.subTest(failed_tool=failed_tool):
                with (
                    patch("agent.suggest_outfit", return_value="Offline outfit.") as outfit,
                    patch("agent.create_fit_card", return_value="Offline card.") as card,
                ):
                    failing_mock = outfit if failed_tool == "suggest_outfit" else card
                    failing_mock.side_effect = ModelUnavailable("UNSAFE_PROVIDER_DETAIL_SENTINEL")
                    session = agent.run_agent(MATCHING_QUERY, self.wardrobe)
                self.assertEqual(session["selected_item"], session["search_results"][0])
                self.assertIsNone(session["fit_card"])
                self.assertTrue(session["error"])
                self.assertNotIn("UNSAFE_PROVIDER_DETAIL_SENTINEL", session["error"])
                if failed_tool == "suggest_outfit":
                    card.assert_not_called()
                else:
                    self.assertEqual(session["outfit_suggestion"], "Offline outfit.")

    def test_malformed_budget_stops_without_downstream_calls(self):
        with (
            patch("agent.suggest_outfit") as outfit,
            patch("agent.create_fit_card") as card,
        ):
            session = agent.run_agent("graphic tee under $-5", self.wardrobe)
        self.assertTrue(session["error"])
        self.assertIsNone(session["fit_card"])
        outfit.assert_not_called()
        card.assert_not_called()

    def test_iteration_limit_stops_before_any_tool(self):
        with (
            patch.object(config, "MAX_ITERATIONS", 0),
            patch("agent.search_listings") as search,
            patch("agent.suggest_outfit") as outfit,
            patch("agent.create_fit_card") as card,
        ):
            session = agent.run_agent(MATCHING_QUERY, self.wardrobe)
        self.assertTrue(session["error"])
        self.assertIsNone(session["fit_card"])
        search.assert_not_called()
        outfit.assert_not_called()
        card.assert_not_called()


if __name__ == "__main__":
    unittest.main()
