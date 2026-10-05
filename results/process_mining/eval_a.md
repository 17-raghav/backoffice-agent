# Evaluation on dataset A

Scored sessions: 62 (excluded, GT does not match recording: ses_20260701-054901-<host>). GT clipped to the recorded window. Boundary F1: all segment starts+ends vs GT starts+ends, one-to-one within τ. Segment F1: one-to-one matches with IoU ≥ 0.5. Labels: frame-level V-measure / purity vs GT process code.

| method | bF1@1s | bF1@2s | bF1@5s | startF1@2s | segF1(IoU≥.5) | segP | segR | labelV | purity | #labels |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline: idle gap > 5 s | 0.071 | 0.113 | 0.279 | 0.138 | 0.192 | 0.201 | 0.183 | 0.0 | 0.087 | 1 |
| baseline: idle gap > 2 s | 0.152 | 0.172 | 0.241 | 0.281 | 0.0 | 0.0 | 0.0 | 0.0 | 0.089 | 1 |
| baseline: screen-slot runs | 0.375 | 0.48 | 0.567 | 0.658 | 0.773 | 0.829 | 0.724 | 0.909 | 0.962 | 15 |
| procmine (full) | 0.925 | 0.949 | 0.96 | 0.976 | 0.972 | 0.969 | 0.974 | 0.956 | 0.978 | 15 |
|   subset: sessions with extension | 0.944 | 0.953 | 0.96 | 0.98 | 0.972 | 0.969 | 0.975 | 0.957 | 0.977 | 15 |
|   subset: sessions without extension | 0.733 | 0.909 | 0.963 | 0.943 | 0.972 | 0.972 | 0.972 | 0.963 | 0.985 | 15 |
| ablation: no navigation anchor | 0.72 | 0.895 | 0.96 | 0.918 | 0.972 | 0.969 | 0.974 | 0.939 | 0.97 | 15 |
| ablation: extension (L3) clicks only | 0.9 | 0.908 | 0.915 | 0.934 | 0.928 | 0.97 | 0.888 | 0.957 | 0.977 | 15 |
| ablation: cut idle gaps > 12 s | 0.852 | 0.89 | 0.903 | 0.976 | 0.892 | 0.89 | 0.895 | 0.97 | 0.988 | 15 |
| ablation: label = screen slot only | 0.925 | 0.949 | 0.96 | 0.976 | 0.972 | 0.969 | 0.974 | 0.956 | 0.978 | 15 |
| ablation: no lag calibration (cut at click) | 0.131 | 0.574 | 0.813 | 0.606 | 0.966 | 0.963 | 0.968 | 0.859 | 0.935 | 15 |

Case-type evidence used (full method): {'case_id': 1917, 'toast': 54, 'slot': 27, 'cell_text': 5}

Runtime: 30 s
