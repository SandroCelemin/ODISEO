from services.utils import similarity

threshold = 0.6

def directional_match_want(current, candidate):
    return similarity(current["want"], candidate["have"]) >= threshold
    
def directional_match_have(current, candidate):
    return similarity(current["have"], candidate["want"]) >= threshold

"""
def directional_match_want(current, candidate, threshold=0.6):
    return similarity(current["want"], candidate["have"]) >= threshold
    
def directional_match_have(current, candidate, threshold=0.6):
    return similarity(current["have"], candidate["want"]) >= threshold
    """