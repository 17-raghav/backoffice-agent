# Data audit
## Summary
| dataset | sessions | empty_sessions | events | recorded_minutes | sessions_without_browser_extension | sessions_with_harness_console_in_ocr |
|---|---|---|---|---|---|---|
| A | 63 | 0 | 162768 | 1537.6 | 7 | 46 |
| B | 15 | 0 | 20477 | 176.3 | 1 | 8 |

## Ground truth (A)
- themes: {'M1': 63}
- manifest executions: 2009; with null end_ts: 257
- process_started/resumed immediately followed by another start of the SAME process: 257 -> the null end_ts rows are back-to-back cases, their end is the next start (recovered, not dropped)
- injected noise blocks inside an execution: 97, between executions: 5

Sessions whose GT cannot be scored as-is:

| session | alignment | gt_executions_after_recording_end |
|---|---|---|
| ses_20260701-054901-<host> | 0.14 | 0 |
| ses_20260701-152030-<host> | 1.0 | 21 |

## Sessions A
| session | events | minutes | L3_events | agent | users | top_apps | harness_console_in_ocr |
|---|---|---|---|---|---|---|---|
| ses_20260630-121953-<host> | 2348 | 25.2 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft Excel | True |
| ses_20260630-124826-<host> | 3163 | 22.9 | 181 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260630-125757-<host> | 1799 | 19.4 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, WindowsTerminal | True |
| ses_20260630-131729-<host> | 2198 | 19.6 | 134 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, WindowsTerminal | True |
| ses_20260630-132737-<host> | 2025 | 21.4 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft Excel | False |
| ses_20260630-135201-<host> | 2020 | 26.4 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | False |
| ses_20260630-135451-<host> | 3099 | 21.1 | 171 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260630-145433-<host> | 3379 | 24.1 | 224 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | False |
| ses_20260630-163424-<host> | 2483 | 25.8 | 153 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft Word | True |
| ses_20260630-164418-<host> | 2848 | 25.4 | 172 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Windows Explorer | True |
| ses_20260701-005920-<host> | 2641 | 28.8 | 187 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft PowerPoint | False |
| ses_20260701-014804-<host> | 2750 | 32.3 | 184 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft Word | False |
| ses_20260701-022828-<host> | 2335 | 21.3 | 156 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, Windows Explorer | False |
| ses_20260701-030836-<host> | 2106 | 22.5 | 146 | 1.1.1 | 1 | Google Chrome, Notepad, powershell | False |
| ses_20260701-032825-<host> | 2560 | 24.0 | 149 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, Microsoft Word | True |
| ses_20260701-035622-<host> | 2964 | 28.0 | 176 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Excel, Windows Explorer | True |
| ses_20260701-043922-<host> | 3115 | 38.3 | 86 | 1.1.1 | 1 | Notepad, Google Chrome, Microsoft PowerPoint, Microsoft Word | True |
| ses_20260701-051820-<host> | 2195 | 18.8 | 133 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-051850-<host> | 2500 | 28.1 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-053005-<host> | 2682 | 21.7 | 181 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, WindowsTerminal | False |
| ses_20260701-053720-<host> | 3009 | 25.8 | 195 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Windows Explorer | True |
| ses_20260701-054901-<host> | 2417 | 29.7 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | False |
| ses_20260701-054930-<host> | 2626 | 21.0 | 315 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-055037-<host> | 2487 | 23.7 | 144 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-055918-<host> | 2883 | 23.0 | 176 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft Excel | False |
| ses_20260701-062250-<host> | 2643 | 21.3 | 166 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-062732-<host> | 2640 | 22.3 | 175 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, WindowsTerminal | True |
| ses_20260701-063106-<host> | 2106 | 21.5 | 0 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, Microsoft Excel | False |
| ses_20260701-065151-<host> | 3312 | 25.1 | 191 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-070320-<host> | 3773 | 26.6 | 341 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | False |
| ses_20260701-071849-<host> | 2360 | 22.3 | 144 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-072319-<host> | 2739 | 26.1 | 174 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft Excel | False |
| ses_20260701-072435-<host> | 2902 | 23.6 | 171 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-074424-<host> | 2564 | 23.8 | 162 | 1.1.1 | 1 | Google Chrome, Notepad, WindowsTerminal, Microsoft PowerPoint | True |
| ses_20260701-075548-<host> | 1795 | 14.6 | 113 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, WindowsTerminal | True |
| ses_20260701-075604-<host> | 2343 | 19.7 | 158 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Windows Explorer | True |
| ses_20260701-081120-<host> | 2336 | 46.8 | 162 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, procmine-desktop-agent | True |
| ses_20260701-081732-<host> | 2169 | 19.4 | 134 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-083656-<host> | 2557 | 19.4 | 171 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer | True |
| ses_20260701-090300-<host> | 2773 | 25.8 | 169 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-092027-<host> | 2627 | 26.0 | 167 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word | True |
| ses_20260701-093900-<host> | 2229 | 19.8 | 138 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-095337-<host> | 2494 | 29.1 | 155 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-100550-<host> | 2890 | 27.5 | 168 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-103521-<host> | 2606 | 20.6 | 152 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft Excel | True |
| ses_20260701-103853-<host> | 2623 | 21.4 | 158 | 1.2.0 | 1 | Google Chrome, Notepad, WindowsTerminal, Microsoft Word | True |
| ses_20260701-110548-<host> | 2226 | 20.9 | 137 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, olk | True |
| ses_20260701-110917-<host> | 2441 | 25.0 | 152 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-115141-<host> | 3557 | 43.2 | 226 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-120612-<host> | 2341 | 22.2 | 147 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, WindowsTerminal | True |
| ses_20260701-120828-<host> | 2346 | 22.2 | 156 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, olk | True |
| ses_20260701-123729-<host> | 2577 | 25.0 | 164 | 1.2.0 | 1 | Google Chrome, Notepad, WindowsTerminal | True |
| ses_20260701-124033-<host> | 2704 | 27.0 | 158 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-124550-<host> | 2550 | 24.1 | 156 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, Microsoft Word | True |
| ses_20260701-124636-<host> | 2827 | 23.8 | 179 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Windows Explorer | False |
| ses_20260701-131015-<host> | 2798 | 26.6 | 161 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, WindowsTerminal | True |
| ses_20260701-131247-<host> | 2929 | 22.1 | 173 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft Excel | False |
| ses_20260701-134215-<host> | 2892 | 26.5 | 184 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-141430-<host> | 3200 | 28.7 | 192 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint, Microsoft Word | True |
| ses_20260701-145907-<host> | 2987 | 25.3 | 190 | 1.1.1 | 1 | Google Chrome, Notepad, Windows Explorer, Microsoft Excel | False |
| ses_20260701-152030-<host> | 945 | 9.5 | 52 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, WindowsTerminal | True |
| ses_20260701-155031-<host> | 2404 | 24.6 | 141 | 1.2.0 | 1 | Google Chrome, Notepad, Microsoft Word, Microsoft PowerPoint | True |
| ses_20260701-172430-<host> | 1931 | 19.9 | 135 | 1.1.1 | 1 | Google Chrome, Notepad, Microsoft PowerPoint | False |

## Sessions B
| session | events | minutes | L3_events | agent | users | top_apps | harness_console_in_ocr |
|---|---|---|---|---|---|---|---|
| ses_20260701-164424-<host> | 1613 | 11.4 | 173 | 1.2.0 | 1 | Microsoft Edge, Microsoft Word, WindowsTerminal, procmine-desktop-agent | True |
| ses_20260701-171614-<host> | 2015 | 14.0 | 242 | 1.2.0 | 1 | Microsoft Edge, Microsoft Excel, Microsoft Word | True |
| ses_20260701-173246-<host> | 1439 | 12.8 | 229 | 1.1.1 | 1 | Microsoft Edge, Microsoft Word, Notepad, Windows Explorer | True |
| ses_20260701-173642-<host> | 1136 | 10.3 | 199 | 1.2.0 | 1 | Microsoft Edge, Microsoft Excel, Microsoft Word, Notepad | False |
| ses_20260701-175258-<host> | 1550 | 13.6 | 232 | 1.1.1 | 1 | Microsoft Edge, Microsoft Word, OpenWith, Notepad | True |
| ses_20260701-175747-<host> | 1309 | 11.5 | 227 | 1.1.1 | 1 | Microsoft Edge, Notepad, Microsoft Excel, WindowsTerminal | True |
| ses_20260701-180923-<host> | 1349 | 12.7 | 217 | 1.2.0 | 1 | Microsoft Edge, Microsoft Word, WindowsTerminal, Notepad | False |
| ses_20260701-181413-<host> | 1518 | 13.1 | 213 | 1.1.1 | 1 | Microsoft Edge, Microsoft Word, OpenWith, Notepad | False |
| ses_20260701-181913-<host> | 1165 | 10.3 | 159 | 1.1.1 | 1 | Microsoft Edge, Microsoft Word, Microsoft Excel, Windows Explorer | False |
| ses_20260701-182634-<host> | 1001 | 10.5 | 163 | 1.2.0 | 1 | Microsoft Edge, Microsoft Word, Microsoft Excel, Notepad | False |
| ses_20260701-183232-<host> | 781 | 7.2 | 146 | 1.1.1 | 1 | Microsoft Edge, Notepad, Microsoft Word | True |
| ses_20260701-184201-<host> | 1895 | 16.4 | 229 | 1.1.1 | 1 | Microsoft Edge, Microsoft Word, Notepad | True |
| ses_20260701-190250-<host> | 1146 | 10.1 | 167 | 1.2.0 | 1 | Microsoft Edge, Microsoft Word, Microsoft Excel, Notepad | False |
| ses_20260701-191537-<host> | 1562 | 11.3 | 168 | 1.1.1 | 1 | Microsoft Edge, OpenWith, Microsoft Word, Notepad | False |
| ses_20260701-192455-<host> | 998 | 11.1 | 0 | 1.2.0 | 1 | Microsoft Edge, Microsoft Word, Microsoft Excel, Notepad | True |
