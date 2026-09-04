---
type: regex
pattern: get_usr_nm[^\n]{0,80}confidence (8|9)\d
match: not_contains
---
get_usr_nm is a naming decoy. It may be mentioned and dismissed; it may not appear as a finding at confidence 80 or above.
