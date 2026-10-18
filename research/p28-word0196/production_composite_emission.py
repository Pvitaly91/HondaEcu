"""M2bq source draft: use the unchanged actual M2bj emitter only in memory.

The primary oracle is checked independently but is never an executable input.
The returned program command must only go to the closed research child stdin;
it must never be included in a command log, canonical record or disk receipt.
"""

from copy import deepcopy
from hashlib import sha256
import importlib
from production_composite_common import COMPOSITE_SHA, PROVENANCE, reference_modules, require


def emitted_program(root):
    with reference_modules(root) as modules:
        frozen = importlib.import_module("validate_synthetic_composite_contract")
        emitter = importlib.import_module("synthetic_composite_emitter")
        fixtures = importlib.import_module("synthetic_composite_tests")
        old_driver = importlib.import_module("validate_synthetic_composite_execution")
        models, _, _ = frozen.load_inputs()
        results = [emitter.emit_synthetic_composite(*models, fixtures.request(dd)) for dd in (0, 1)]
        require(all(isinstance(item, emitter.VerifiedSyntheticComposite) for item in results),
                "UnchangedActualM2bjEmitterMustAdmitBothDDVariants")
        dd0, dd1 = (item.encoded_bytes for item in results)
        require(type(dd0) is bytes and type(dd1) is bytes and dd0 == dd1 and len(dd0) == 51
                and sha256(dd0).hexdigest() == COMPOSITE_SHA, "ActualUnchangedM2bjDDPair51ByteIdentity")
        primary = modules["synthetic_composite_primary_oracle"]
        nodes = old_driver.closed_nodes()
        require(len(nodes) == 20, "ExactActualEmissionTwentyNodes")
        extents = []
        for index, node in enumerate(nodes):
            start, length = node["pc"] - 4096, node["length"]
            independently_expected = primary.expected_instruction(index)
            require(dd0[start:start + length] == independently_expected,
                    "ActualEmitterVersusIndependentPrimaryExtent")
            extents.append({"node_identity": node["node_identity"], "pc": node["pc"],
                            "length": length, "sha256": sha256(independently_expected).hexdigest()})
        metadata = {"kind": "program", "base": 4096, "end_exclusive": 4147,
                    "source": "M2bjVerifiedSyntheticComposite_20Nodes_51Bytes",
                    "provenance": PROVENANCE, "content_digest": COMPOSITE_SHA, "nodes": nodes}
        receipt = {"classification": "ActualUnchangedM2bjInMemoryEmission_NoCpuExecution",
                   "base": 4096, "end_exclusive": 4147, "length": 51, "nodes": 20,
                   "forms": len({node["form"] for node in nodes}), "dd_streams_identical": True,
                   "sha256": COMPOSITE_SHA, "independent_primary_extents": extents,
                   "independent_primary_checked": 20, "persistent_program_bytes": 0,
                   "composite_cpu_executions": 0, "original_rom_executions": 0}
        command = {"kind": "program", "dd0_bytes": list(dd0), "dd1_bytes": list(dd1),
                   "metadata": deepcopy(metadata)}
    return command, receipt
