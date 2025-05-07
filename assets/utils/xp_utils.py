import math

# IMPORTANT: This formula MUST match the one used by your bot (lvl)
# Example formula: 5 * (level^2) + 50*level + 100
def xp_needed_for_level(level: int) -> int:
    """Calculates the XP needed to complete a given level."""
    if level <= 0:
        return 0
    return (100 * (level ** 1.8)) 

# Cache for total XP calculation
_total_xp_cache = {0: 0}

def total_xp_for_level(level: int) -> int:
    """Calculates the total cumulative XP required to reach the START of a given level."""
    if level <= 0:
        return 0
    
    # Check cache first
    if level in _total_xp_cache:
        return _total_xp_cache[level]

    # Calculate iteratively if not in cache
    # Find highest cached level below target
    max_cached_level = max(k for k in _total_xp_cache if k < level)
    current_total = _total_xp_cache[max_cached_level]
    
    for i in range(max_cached_level, level):
         # XP needed to complete level i (to reach level i+1)
        xp_for_i = xp_needed_for_level(i) 
        current_total += xp_for_i
        _total_xp_cache[i + 1] = current_total # Cache result for next level start

    return _total_xp_cache[level]


def calculate_cumulative_xp(level: int, current_xp: int) -> int:
    """Calculates the total cumulative XP a user has."""
    if level <= 0:
        return max(0, current_xp) # Ensure non-negative XP
        
    base_xp_for_level = total_xp_for_level(level)
    return base_xp_for_level + current_xp

# Example usage:
# user_level = 10
# user_current_xp = 150
# cumulative = calculate_cumulative_xp(user_level, user_current_xp) 
# print(f"Cumulative XP for Level {user_level} with {user_current_xp} XP: {cumulative}") 