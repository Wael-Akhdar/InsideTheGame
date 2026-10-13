# Third-party data: licences checked, and what we may use

Why this file exists: the hackathon rules (4.6, 4.11) say a submission must not violate anyone's rights, and rule 7 gives Microsoft
a worldwide, perpetual, commercial licence on our Submission. So every dataset we touch must allow commercial reuse of what we derive
from it, and we must be able to show where its terms came from. Checked on 2026-10-13. This is our reading of the texts, not legal advice.

Organizers' support confirmed by email (13 Oct 2026) that open datasets may be used "as long as the hackathon rules are respected, no
trademark issues". That covers the hackathon rules only: each dataset's own licence still decides.

## Cleared for use (licence read and verified)
| Dataset | What | Licence (where verified) | Conditions |
|---|---|---|---|
| Wyscout public soccer event dataset (Pappalardo et al., 2019) | 1,941 matches, 3.25 M events, 7 competitions, 2017/18 | CC BY 4.0 (figshare records 7770422 and 7770599, `license` field) | Credit the paper; no endorsement implied |
| Sportec Open DFL dataset (Bassek, Rein, Weber, Memmert, 2025) | 7 German Bundesliga / 2. Bundesliga matches, 25 Hz positions of every player and the ball, events | CC BY 4.0 "with the authorization from the DFL" (paper, Data Records; figshare record 28196177, `license` field) | Credit the paper and DFL; match files contain real player and team names, so never publish them (aggregates only); no DFL or club logos |

Attribution text to use in the README and pitch:
- "Calibrated with the public Wyscout event dataset: Pappalardo et al. (2019), A public data set of spatio-temporal match events in soccer competitions, Scientific Data 6:236 (CC BY 4.0)."
- "Movement calibrated with the Sportec Open DFL dataset: Bassek et al. (2025), An integrated dataset of spatiotemporal and event data in elite soccer, Scientific Data (CC BY 4.0, released with the authorization of the DFL)."

## Do not use without written permission
| Dataset | Why |
|---|---|
| StatsBomb Open Data | User agreement forbids distributing the data and "commercially exploit[ing] the data or any analysis derived" from it (1.2.1, 1.2.2), and requires the StatsBomb logo on any published analysis (1.4). That clashes with rule 7 (commercial licence to Microsoft) and with "no trademark issues". |
| SkillCorner Open Data | The repository contains an MIT licence file, but the README states no terms for the data and only "kindly asks" for credit. Probably fine, not explicit: ask SkillCorner to confirm in writing before relying on it. |
| Metrica Sports sample data | The GitHub repository has no licence (GitHub API `license: null`); the README only says to be responsible and acknowledge the source. Ask first. |
| PFF FC World Cup 2022 data | Free via a request form, but the announcement page states no terms. Read the terms shown with the download (and ask PFF if they are unclear) before using it. |

## Rules we follow whatever the source
- Raw third-party data stays in `data/external/` (git-ignored). The public repository only holds code and aggregated results.
- No real club, player or competition logos in the demo, screenshots or video; real names are replaced when real data is shown.
- Every aggregated number derived from a dataset is credited in `docs/CALIBRATION.md`.
