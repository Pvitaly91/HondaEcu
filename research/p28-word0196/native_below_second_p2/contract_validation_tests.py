"""Independent contract mutations; static refusals are never CPU evidence."""
from copy import deepcopy
import unittest
from . import contract_validation as validation

# Twenty-six functional/state/CFG/effect relations, and six authority/metadata
# relations are deliberately accounted separately.
FUNCTIONAL_MUTATIONS = (
    (('program','entryPc'),0x55D2), (('program','segmentBytes'),402),
    (('program','instructionNodes'),48), (('program','privateEndExclusive'),0x5689),
    (('program','stopBeforeRt5688'),False), (('program','rtExecuted'),True),
    (('entry','oneCpuBusPerCase'),False), (('entry','noHostPcJump'),False),
    (('entry','noMidExecutionReseed'),False), (('entry','noSnapshotImport'),False),
    (('entry','newCanaryValue'),1), (('entry','logicalSetupWrites'),48),
    (('entry','rawSetupWrites'),80), (('below','reachableRolInput'),'IndependentArbitraryCarry'),
    (('below','reachableAh'),1), (('below','jneTaken'),False),
    (('below','wordStores',1,'width'),8), (('below','wordStores',2,'value'),0),
    (('below','secondP2Al'),0), (('below','finalRbZf'),'NewBit7'),
    (('control','nativeReadsPerCase'),2), (('control','sameValueWritesCreateGeneration'),False),
    (('p2','generations'),1), (('p2','secondGenerationFreshEvenSameValue'),False),
    (('path','budget'),40), (('trace','canonicalFieldExclusions'),['psw']),
)
AUTHORITY_MUTATIONS = (
    (('manufacturer','semanticsAuthority'),'ProductionOutput'),
    (('program','returnFrame'),'Established'),
    (('delivery','privateRomInCi'),True),
    (('delivery','strictHistoricalPreservationPass'),True),
    (('cycleAccounting','timingEquivalenceEstablished'),True),
    (('firmwareReady',),True),
)

class ContractValidationTests(unittest.TestCase):
    def test_independent_closed_facts_and_counts(self):
        result=validation.validate_contract()
        self.assertTrue(result['passed'])
        self.assertEqual(result['casesPerMode'],16)
        self.assertEqual(result['retirementsPerMode'],624)
        self.assertEqual(result['actualCpuExecutions'],0)
        self.assertFalse(result['initialNativeControlOwnerEstablished'])
        self.assertEqual(len(validation.facts()['unresolved']),18)

    def test_twenty_six_functional_and_six_authority_categories_refuse(self):
        self.assertEqual(len(FUNCTIONAL_MUTATIONS),26)
        self.assertEqual(len(AUTHORITY_MUTATIONS),6)
        original=validation.facts()
        for domain,variants in (('functional',FUNCTIONAL_MUTATIONS),('authority',AUTHORITY_MUTATIONS)):
            for path,value in variants:
                changed=deepcopy(original); target=changed
                for part in path[:-1]: target=target[part]
                self.assertNotEqual(target[path[-1]],value)
                target[path[-1]]=value
                with self.subTest(domain=domain,path=path),self.assertRaises(ValueError):
                    validation.validate_contract(changed)

    def test_historical_authorities_cannot_be_replaced_by_current_json(self):
        rows=deepcopy(validation.facts()['sourceBindings']); rows[0]['sha256']='0'*64
        with self.assertRaises(ValueError): validation.validate_contract(source_bindings=rows)

    def test_diag_timing_source_and_all_counters_remain_visible(self):
        facts=validation.facts()
        accounting=facts['cycleAccounting']
        self.assertEqual(accounting['belowSoftwareDiagnosticTotal'],101)
        self.assertEqual(accounting['belowManufacturerIntTotal'],102)
        self.assertEqual(accounting['secondP2SoftwareDiagnosticDelta'],6)
        self.assertEqual(accounting['secondP2ManufacturerInt'],7)
        self.assertIn('DiagnosticCycleTimingEquivalenceNotEstablished',facts['unresolved'])
        self.assertEqual(facts['trace']['canonicalFieldExclusions'],[])

if __name__=='__main__': unittest.main()
