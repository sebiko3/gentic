---
type: regex
pattern: network.{0,160}(download|data\.csv|DoD)|(download|data\.csv|DoD).{0,160}network
flags: is
---
The Constraints forbid the network and D2 requires a download. The critic must name that specific collision, not merely print a 'Contradiction' heading.
