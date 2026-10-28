"""Independent functional bit-plane oracle for invented provenance scenarios.

This module has no dependency on the ownership implementation or production
Rust. Immutable bit triples carry a numerical value, semantic source and path;
storage generations are separate. All observations here are invented static
calculations and grant no native execution authority.
"""


_EMPTY = tuple((None, None, ()) for _ in range(8))


def _from_byte(value, owner=None):
    return tuple((None if value is None else (value >> bit) & 1,
                  None if owner is None else owner + ":" + str(bit), ())
                 for bit in range(8))


def _byte_value(plane):
    return (sum(bit[0] << index for index, bit in enumerate(plane))
            if all(bit[0] is not None for bit in plane) else None)


def _retire_storage(plane, generation):
    return tuple((value, source, path + (generation,) if source is not None else ())
                 for value, source, path in plane)


def reference_scenario(scenario):
    """Calculate the closed invented scenario independently of the main model.

    Input schema/admission is separately checked. This oracle accepts the valid
    schema and computes full semantic planes, write chronology and obligations.
    """
    machine = scenario["machineId"]
    planes = {row["address"]: _from_byte(row["value"], row["owner"])
              for row in scenario["seeds"]}
    generations = {address: None for address in planes}
    writes, unknown_aliases = [], []

    def get(address):
        if address not in planes:
            planes[address] = _EMPTY
            generations[address] = None
        return planes[address]

    def commit(event_index, event, addresses, incoming, source_address):
        ordinal = len(writes) + 1
        generation = machine + ":" + str(ordinal)
        old_values = [_byte_value(get(address)) for address in addresses]
        new_values = [_byte_value(plane) for plane in incoming]
        same_value = (all(value is not None for value in old_values + new_values)
                      and old_values == new_values)
        for address, plane in zip(addresses, incoming):
            planes[address] = _retire_storage(plane, generation)
            generations[address] = generation
        combined = (sum(value << (8 * index) for index, value in enumerate(new_values))
                    if all(value is not None for value in new_values) else None)
        writes.append({
            "ordinal": ordinal, "eventIndex": event_index, "writerPC": event["pc"],
            "address": addresses[0], "widthBits": len(addresses) * 8,
            "value": combined, "sourceAddress": source_address,
            "storageGeneration": generation, "sameValue": same_value, "op": event["op"],
        })

    for index, event in enumerate(scenario["events"]):
        operation = event["op"]
        if operation == "copy":
            source, target = event["source"], event["target"]
            # Snapshot both source bytes before either destination is replaced.
            incoming = (get(source), get(source + 1))
            commit(index, event, (target, target + 1), incoming, source)
        elif operation == "programBit":
            previous = get(0x0217)
            program = event["programByte"]
            replacement = (None, None, ()) if program is None else (
                (program >> 7) & 1, "invented:PROGRAM60EC:7", ())
            incoming = previous[:3] + (replacement,) + previous[4:]
            commit(index, event, (0x0217,), (incoming,), 0x60EC)
        elif operation == "overlap":
            address, value = event["address"], event["value"]
            incoming = tuple(_from_byte(None if value is None else (value >> shift) & 0xFF)
                             for shift in (0, 8))
            commit(index, event, (address, address + 1), incoming, None)
        elif operation == "unknownAlias":
            addresses = list(event["addresses"])
            for address in addresses:
                planes[address] = _EMPTY
                generations[address] = None
            unknown_aliases.append({"eventIndex": index, "addresses": addresses,
                                    "reason": "IndirectAliasPreservationUnknown"})
        else:
            raise ValueError("UnsupportedInventedOracleEvent")

    address, selected_bit = scenario["reader"]["address"], scenario["reader"]["bit"]
    value, source, lineage = get(address)[selected_bit]
    reader = {"address": address, "bit": selected_bit, "value": value,
              "source": source, "lineage": list(lineage),
              "storageGeneration": generations[address]}
    memory = []
    for address in sorted(planes):
        plane = planes[address]
        memory.append({"address": address, "value": _byte_value(plane),
                       "bitValues": [bit[0] for bit in plane],
                       "bitSources": [bit[1] for bit in plane],
                       "bitPaths": [list(bit[2]) for bit in plane],
                       "storageGeneration": generations[address]})
    compatible = scenario["history"] == scenario["context012A"]
    missing = {name for name, satisfied in scenario["constraints"].items() if not satisfied}
    if not compatible:
        missing.add("Incompatible012AHistory")
    if source is None:
        missing.add("ReaderSourceUnknown")
    selected_plane = get(reader["address"])
    if _byte_value(selected_plane) is None:
        missing.add("WholeReaderByteUnknown")
    if any(bit[1] is None for bit in selected_plane):
        missing.add("WholeReaderByteOwnerUnknown")
    if not lineage:
        missing.add("NoObservedEvenInventedWriterChain")
    if unknown_aliases:
        missing.add("UnknownAliasPresent")
    return {
        "caseId": scenario["caseId"],
        "classification": "StaticProvenanceCanonical_NotOriginalRomCpuExecution",
        "machineId": machine, "memory": memory, "writes": writes, "reader": reader,
        "aliasUnknowns": unknown_aliases,
        "conditionalBit3Terminal": 0x0667 if scenario["old012A"] & 8 else 0x0664,
        "context012ACompatible": compatible, "missingObligations": sorted(missing),
        "symbolicBridge": ("SameMachineBridgeBlocked" if missing
                           else "InventedOnly_SourceToReaderObligationsSatisfied"),
        "sourceValueKnownIsNativeOwner": False,
        "actualCpuExecutions": 0, "actualOriginalRomExecutions": 0,
        "actualRetiredInstructions": 0, "nativeSourceOwnershipEstablished": False,
        "firmwareReady": False,
    }
