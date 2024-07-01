import inspect
import subprocess
import json
from slither.slither import Slither
from slither.detectors import all_detectors
from typing import List, Tuple, Type
from slither.detectors.abstract_detector import AbstractDetector
from pkg_resources import iter_entry_points
from typing import Tuple, List, Dict, Type
import slitherin


# NOTE: Removed printers because of some deep down the stack errors
def get_detectors() -> Tuple[List[Type[AbstractDetector]]]:
    detectors_ = [getattr(all_detectors, name) for name in dir(all_detectors)]
    detectors = [
        d for d in detectors_ if inspect.isclass(d) and issubclass(d, AbstractDetector)
    ]

    # Handle plugins!
    for entry_point in iter_entry_points(group="slither_analyzer.plugin", name=None):
        make_plugin = entry_point.load()

        plugin_detectors, _ = make_plugin()

        detector = None
        if not all(
            issubclass(detector, AbstractDetector) for detector in plugin_detectors
        ):
            raise Exception(
                f"Error when loading plugin {entry_point}, {detector} is not a detector"
            )

        # We convert those to lists in case someone returns a tuple
        detectors += list(plugin_detectors)
    return detectors


def get_slitherin_detectors() -> List[Dict]:
    return slitherin.plugin_detectors


# NOTE: Removed printers because of some deep down the stack errors
def run_all_detectors(
    slither: Slither,
    detector_classes: List[Type[AbstractDetector]],
) -> Tuple[Slither, List[Dict], int]:
    for detector_cls in detector_classes:
        slither.register_detector(detector_cls)

    analyzed_contracts_count = len(slither.contracts)

    results_detectors = []

    for detector in slither._detectors:
        try:
            detector_results = detector.detect()
            detector_results = [x for x in detector_results if x]
            results_detectors.extend(detector_results)
        except Exception as e:
            print(f"Error running detector {detector.__class__.__name__}: {e}")
            continue

    return slither, results_detectors, analyzed_contracts_count