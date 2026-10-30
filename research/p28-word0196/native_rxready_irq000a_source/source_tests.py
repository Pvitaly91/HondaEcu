"""Small source/authority controls with independently frozen expectations."""
import json
import unittest

from native_rxready_irq000a_source import analysis, rx_pending, mask_lineage
from native_rxready_irq000a_source import reference_oracle as reference


def exact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


class RxReadySourceTests(unittest.TestCase):
    def assertExact(self, actual, expected):
        self.assertEqual(exact(actual), exact(expected))

    def test_all_twenty_three_complete_records_match_independent_reference(self):
        expected = reference.reference_records()
        self.assertEqual(len(expected), 23)
        self.assertEqual(len({r['caseId'] for r in expected}), 23)
        self.assertExact(analysis.canonical_records(), expected)

    def test_source_qualified_primary_findings_preserve_real_ie_conflict(self):
        self.assertExact(rx_pending.primary_findings(), reference.reference_primary())

    def test_eight_receive_controls_match_all_source_and_unknown_fields(self):
        for name, args in reference.RECEIVE_CASES:
            with self.subTest(case=name):
                self.assertExact(rx_pending.completion_relation(*args),
                                 reference.reference_completion(*args))

    def test_overrun_is_a_new_condition_and_does_not_fabricate_error_clear(self):
        accepted = rx_pending.completion_relation('uart_normal', False, True, False, None, False)
        self.assertIs(accepted['newOverrunConditionExpected'], False)
        self.assertIsNone(accepted['srstatOerrAfter'])
        ignored = rx_pending.completion_relation('uart_multiprocessor', False, True, True, 0, True)
        self.assertIs(ignored['rxReadyRequestExpected'], False)
        self.assertIsNone(ignored['newOverrunConditionExpected'])
        self.assertIsNone(ignored['srstatOerrAfter'])

    def test_mask_writer_findings_match_the_independent_source_join(self):
        self.assertExact(mask_lineage.mask_findings(), reference.reference_masks())

    def test_both_mask_pairs_keep_the_two_polarities_hypothetical(self):
        for name, args in reference.MASK_CASES:
            with self.subTest(case=name):
                self.assertExact(mask_lineage.mask_profile(*args), reference.reference_mask(*args))

    def test_post_clear_order_does_not_establish_current_pending_or_race_winner(self):
        for name, args in reference.PENDING_CASES:
            with self.subTest(case=name):
                self.assertExact(mask_lineage.pending_cut(*args), reference.reference_pending(*args))
        after_with_collision = mask_lineage.pending_cut('after54EA', True)
        self.assertIs(after_with_collision['postClearOrderingSatisfied'], True)
        self.assertIs(after_with_collision['orderingProvesPendingState'], False)
        self.assertIsNone(after_with_collision['setClearWinner'])
        self.assertIsNone(after_with_collision['currentPendingValue'])

    def test_three_frame_controls_never_promote_numeric_disjointness_to_safety(self):
        for name, ssp in reference.FRAME_CASES:
            with self.subTest(case=name):
                self.assertExact(analysis.frame_relation(ssp), reference.reference_frame(ssp))

    def test_single_flag_and_dag_match_source_obligations_not_execution(self):
        self.assertExact(analysis.single_invocation_findings(), reference.reference_single())
        self.assertExact(analysis.proof_dag(), reference.reference_dag())

    def test_exact_conditional_claim_has_no_actual_event_or_injected_context(self):
        self.assertExact(analysis.default_claim(), reference.reference_claim())
        self.assertIsNone(analysis.validate_claim(reference.reference_claim()))

    def test_twenty_five_meaningful_source_and_runtime_overclaims_are_refused(self):
        controls = reference.negative_claims()
        self.assertEqual(len(controls), 25)
        self.assertEqual(len({name for name, _ in controls}), 25)
        for name, claim in controls:
            with self.subTest(case=name), self.assertRaises(ValueError):
                analysis.validate_claim(claim)

    def test_false_boolean_cannot_replace_zero_counters_or_null_native_owners(self):
        for field, wrong in (('actualCpuExecutions', False), ('newPreservationExceptions', False),
                             ('actual03F3Generation', 0), ('actualRestoredPC', False)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.validate_claim({**reference.reference_claim(), field: wrong})

    def test_receive_mode_and_scalar_mismatches_are_refused(self):
        wrong = [
            ('not-a-reviewed-mode', False, True, False, None, False),
            ('uart_normal', True, True, False, None, False),
            ('uart_normal', False, True, True, None, False),
            ('uart_normal', False, True, False, 0, False),
            ('uart_multiprocessor', False, True, True, False, False),
            ('uart_multiprocessor', False, True, True, None, False),
            ('uart_normal', False, 1, False, None, False),
        ]
        for args in wrong:
            with self.subTest(args=args), self.assertRaises(ValueError):
                rx_pending.completion_relation(*args)

    def test_pending_mask_and_frame_type_mismatches_are_refused(self):
        for args in (('after54EA', 1), ('stale', False), (0, False)):
            with self.subTest(pending=args), self.assertRaises(ValueError):
                mask_lineage.pending_cut(*args)
        for args in ((False, 1), (0, True), (2, 1), (0, -1)):
            with self.subTest(mask=args), self.assertRaises(ValueError):
                mask_lineage.mask_profile(*args)
        for ssp in (False, -1, 65536, '07FE'):
            with self.subTest(ssp=ssp), self.assertRaises(ValueError):
                analysis.frame_relation(ssp)


if __name__ == '__main__':
    unittest.main()
