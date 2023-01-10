from typing import Dict, List, Tuple
from racetrack_client.utils.semver import SemanticVersion
from racetrack_client.utils.time import days_ago
from racetrack_commons.entities.dto import FatmanDto, FatmanStatus


def enrich_fatmen_purge_info(fatmen: List[FatmanDto]) -> List[Dict]:
    """Enrich fatmen with removal candidates info: score and reasons"""
    fatman_dicts = []
    for fatman in fatmen:
        score, reasons = assess_fatman_usability(fatman, fatmen)
        fatman_dict = fatman.dict()
        fatman_dict['purge_score'] = -score
        fatman_dict['purge_reasons'] = '\n'.join(reasons)
        fatman_dict['purge_newer_versions'] = _count_fatman_newer_versions(fatman, fatmen)
        fatman_dicts.append(fatman_dict)
    return sorted(fatman_dicts, key=lambda f: -f['purge_score'])


def assess_fatman_usability(fatman: FatmanDto, all_fatmen: List[FatmanDto]) -> Tuple[float, List[str]]:
    """
    Assess usability of a fatman.
    Return score number representing penalty points with descriptions of reasons.
    A lower value means a better candidate for removal.
    Positive score means the fatman shouldn't be removed.
    """
    score: float = 0
    reasons = []

    if fatman.status == FatmanStatus.ORPHANED.value:
        score -= 100
        reasons.append('Orphaned fatman is most likely a useless remnant.')
    elif fatman.status == FatmanStatus.LOST.value:
        score -= 50
        reasons.append('Fatman is lost - can\'t be found in a cluster. It should be redeployed or removed.')
    elif fatman.status == FatmanStatus.ERROR.value:
        score -= 20
        reasons.append('Fatman is failing. It should be fixed or removed.')

    deployed_days_ago = days_ago(fatman.update_time)
    if deployed_days_ago >= 1:  # wait a day until we decide it was never called
        never_called = fatman.last_call_time is None or fatman.last_call_time == 0
        if never_called:
            score -= 10
            reasons.append('Fatman seems to be unused as it was never called.')
        else:
            last_call_days_ago = days_ago(fatman.last_call_time)
            if last_call_days_ago > 1:
                score -= 10 * _interpolate(last_call_days_ago, 0, 30)
                reasons.append(f'Fatman hasn\'t been called for {last_call_days_ago:.1f} days.')

    newer_versions = _count_fatman_newer_versions(fatman, all_fatmen)
    if newer_versions > 0:
        score -= 1 * newer_versions
        reasons.append(f'Fatman has {newer_versions} newer versions.')

    return score, reasons


def _count_fatman_newer_versions(fatman: FatmanDto, all_fatmen: List[FatmanDto]) -> int:
    """Count how many fatman (from the same family) are newer than this one"""
    count = 0
    fatman_version = SemanticVersion(fatman.version)
    family_fatmen = [f for f in all_fatmen if f.name == fatman.name]
    for f in family_fatmen:
        if SemanticVersion(f.version) > fatman_version:
            count += 1
    return count


def _interpolate(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return 0
    if value > max_value:
        return 1
    return (value - min_value) / (max_value - min_value)
