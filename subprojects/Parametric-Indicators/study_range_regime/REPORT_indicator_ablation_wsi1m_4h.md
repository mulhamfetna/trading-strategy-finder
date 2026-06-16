# Indicator ablation — wsh4 1-min 4h champion

Baseline (all 8 on) = **$142,203** P/L. All 256 subsets backtested full-period (ind_1min). Ranked by score = PnL + $5,000 per indicator dropped (no hard filter — pick your tolerance by eye).

| rank | kept | #drop | PnL | ΔPnL% | maxDD | win% | decision-pause d | source | footprint(1m) |
|--:|---|--:|--:|--:|--:|--:|--:|---|--:|
| 1 | cci, order_block, structure_trend | 5 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 2 | bollinger, cci, order_block, structure_trend | 4 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 3 | cci, keltner, order_block, structure_trend | 4 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 4 | cci, obv, order_block, structure_trend | 4 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 5 | cci, order_block, sma_trend, structure_trend | 4 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 6 | bollinger, cci, keltner, order_block, structure_trend | 3 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 7 | bollinger, cci, obv, order_block, structure_trend | 3 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 8 | bollinger, cci, order_block, sma_trend, structure_trend | 3 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 9 | cci, keltner, obv, order_block, structure_trend | 3 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 10 | cci, keltner, order_block, sma_trend, structure_trend | 3 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 11 | cci, obv, order_block, sma_trend, structure_trend | 3 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 12 | cci, mfi, order_block, structure_trend | 4 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 13 | bollinger, cci, keltner, obv, order_block, structure_trend | 2 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 138 |
| 14 | bollinger, cci, keltner, order_block, sma_trend, structure_trend | 2 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 15 | bollinger, cci, obv, order_block, sma_trend, structure_trend | 2 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 16 | cci, keltner, obv, order_block, sma_trend, structure_trend | 2 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 17 | bollinger, cci, mfi, order_block, structure_trend | 3 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 18 | cci, keltner, mfi, order_block, structure_trend | 3 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 19 | cci, mfi, obv, order_block, structure_trend | 3 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 20 | cci, mfi, order_block, sma_trend, structure_trend | 3 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 21 | cci, structure_trend | 6 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 22 | mfi, order_block, structure_trend | 5 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 39 |
| 23 | bollinger, cci, keltner, obv, order_block, sma_trend, structure_trend | 1 | $149,989 | +5.5 | $15,491 | 67.8 | 11.5 | decision | 346 |
| 24 | bollinger, cci, keltner, mfi, order_block, structure_trend | 2 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 25 | bollinger, cci, mfi, obv, order_block, structure_trend | 2 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 26 | bollinger, cci, mfi, order_block, sma_trend, structure_trend | 2 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 27 | cci, keltner, mfi, obv, order_block, structure_trend | 2 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 28 | cci, keltner, mfi, order_block, sma_trend, structure_trend | 2 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 29 | cci, mfi, obv, order_block, sma_trend, structure_trend | 2 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 30 | bollinger, cci, structure_trend | 5 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 31 | cci, keltner, structure_trend | 5 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 32 | cci, obv, structure_trend | 5 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 33 | cci, sma_trend, structure_trend | 5 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 34 | bollinger, mfi, order_block, structure_trend | 4 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 45 |
| 35 | keltner, mfi, order_block, structure_trend | 4 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 40 |
| 36 | mfi, obv, order_block, structure_trend | 4 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 39 |
| 37 | mfi, order_block, sma_trend, structure_trend | 4 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 38 | order_block, structure_trend | 6 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 10 |
| 39 | cci, mfi, order_block | 5 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 40 | cci, mfi, structure_trend | 5 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 41 | cci, obv, order_block | 5 | $123,562 | -13.1 | $26,561 | 64.5 | 10.8 | decision | 138 |
| 42 | bollinger, cci, keltner, mfi, obv, order_block, structure_trend | 1 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 138 |
| 43 | bollinger, cci, keltner, mfi, order_block, sma_trend, structure_trend | 1 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 44 | bollinger, cci, mfi, obv, order_block, sma_trend, structure_trend | 1 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 45 | cci, keltner, mfi, obv, order_block, sma_trend, structure_trend | 1 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 46 | bollinger, cci, keltner, structure_trend | 4 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 47 | bollinger, cci, obv, structure_trend | 4 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 48 | bollinger, cci, sma_trend, structure_trend | 4 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 49 | cci, keltner, obv, structure_trend | 4 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 50 | cci, keltner, sma_trend, structure_trend | 4 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 51 | cci, obv, sma_trend, structure_trend | 4 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 52 | mfi, order_block | 6 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 39 |
| 53 | bollinger, keltner, mfi, order_block, structure_trend | 3 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 45 |
| 54 | bollinger, mfi, obv, order_block, structure_trend | 3 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 45 |
| 55 | bollinger, mfi, order_block, sma_trend, structure_trend | 3 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 56 | keltner, mfi, obv, order_block, structure_trend | 3 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 40 |
| 57 | keltner, mfi, order_block, sma_trend, structure_trend | 3 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 58 | mfi, obv, order_block, sma_trend, structure_trend | 3 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 59 | bollinger, order_block, structure_trend | 5 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 45 |
| 60 | keltner, order_block, structure_trend | 5 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 40 |
| 61 | obv, order_block, structure_trend | 5 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 18 |
| 62 | order_block, sma_trend, structure_trend | 5 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 63 | bollinger, cci, mfi, order_block | 4 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 64 | cci, keltner, mfi, order_block | 4 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 65 | cci, mfi, obv, order_block | 4 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 66 | cci, mfi, order_block, sma_trend | 4 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 67 | bollinger, cci, mfi, structure_trend | 4 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 68 | cci, keltner, mfi, structure_trend | 4 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 69 | cci, mfi, obv, structure_trend | 4 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 70 | cci, mfi, sma_trend, structure_trend | 4 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 71 | mfi, structure_trend | 6 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 39 |
| 72 | bollinger, cci, obv, order_block | 4 | $123,562 | -13.1 | $26,561 | 64.5 | 10.8 | decision | 138 |
| 73 | cci, obv, order_block, sma_trend | 4 | $122,886 | -13.6 | $25,622 | 64.4 | 10.8 | decision | 346 |
| 74 | cci, order_block, sma_trend | 5 | $117,626 | -17.3 | $25,622 | 64.4 | 12.0 | decision | 346 |
| 75 | bollinger, cci, keltner, mfi, obv, order_block, sma_trend, structure_trend | 0 | $142,203 | +0.0 | $14,082 | 69.2 | 11.5 | decision | 346 |
| 76 | bollinger, cci, keltner, obv, structure_trend | 3 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 138 |
| 77 | bollinger, cci, keltner, sma_trend, structure_trend | 3 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 78 | bollinger, cci, obv, sma_trend, structure_trend | 3 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 79 | cci, keltner, obv, sma_trend, structure_trend | 3 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 80 | bollinger, mfi, order_block | 5 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 45 |
| 81 | keltner, mfi, order_block | 5 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 40 |
| 82 | mfi, obv, order_block | 5 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 39 |
| 83 | mfi, order_block, sma_trend | 5 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 84 | cci, keltner, obv, order_block | 4 | $121,983 | -14.2 | $25,622 | 64.3 | 10.8 | decision | 138 |
| 85 | bollinger, keltner, mfi, obv, order_block, structure_trend | 2 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 45 |
| 86 | bollinger, keltner, mfi, order_block, sma_trend, structure_trend | 2 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 87 | bollinger, mfi, obv, order_block, sma_trend, structure_trend | 2 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 88 | keltner, mfi, obv, order_block, sma_trend, structure_trend | 2 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 89 | bollinger, keltner, order_block, structure_trend | 4 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 45 |
| 90 | bollinger, obv, order_block, structure_trend | 4 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 45 |
| 91 | bollinger, order_block, sma_trend, structure_trend | 4 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 92 | keltner, obv, order_block, structure_trend | 4 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 40 |
| 93 | keltner, order_block, sma_trend, structure_trend | 4 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 94 | obv, order_block, sma_trend, structure_trend | 4 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 95 | bollinger, cci, keltner, mfi, order_block | 3 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 96 | bollinger, cci, mfi, obv, order_block | 3 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 97 | bollinger, cci, mfi, order_block, sma_trend | 3 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 98 | cci, keltner, mfi, obv, order_block | 3 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 99 | cci, keltner, mfi, order_block, sma_trend | 3 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 100 | cci, mfi, obv, order_block, sma_trend | 3 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 101 | bollinger, cci, keltner, mfi, structure_trend | 3 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 102 | bollinger, cci, mfi, obv, structure_trend | 3 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 103 | bollinger, cci, mfi, sma_trend, structure_trend | 3 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 104 | cci, keltner, mfi, obv, structure_trend | 3 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 105 | cci, keltner, mfi, sma_trend, structure_trend | 3 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 106 | cci, mfi, obv, sma_trend, structure_trend | 3 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 107 | bollinger, mfi, structure_trend | 5 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 45 |
| 108 | keltner, mfi, structure_trend | 5 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 40 |
| 109 | mfi, obv, structure_trend | 5 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 39 |
| 110 | mfi, sma_trend, structure_trend | 5 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 111 | bollinger, cci, obv, order_block, sma_trend | 3 | $122,886 | -13.6 | $25,622 | 64.4 | 10.8 | decision | 346 |
| 112 | bollinger, cci, order_block, sma_trend | 4 | $117,626 | -17.3 | $25,622 | 64.4 | 12.0 | decision | 346 |
| 113 | bollinger, cci, keltner, obv, sma_trend, structure_trend | 2 | $127,078 | -10.6 | $14,025 | 65.5 | 11.5 | decision | 346 |
| 114 | bollinger, keltner, mfi, order_block | 4 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 45 |
| 115 | bollinger, mfi, obv, order_block | 4 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 45 |
| 116 | bollinger, mfi, order_block, sma_trend | 4 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 117 | keltner, mfi, obv, order_block | 4 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 40 |
| 118 | keltner, mfi, order_block, sma_trend | 4 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 119 | mfi, obv, order_block, sma_trend | 4 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 120 | bollinger, cci, keltner, obv, order_block | 3 | $121,983 | -14.2 | $25,622 | 64.3 | 10.8 | decision | 138 |
| 121 | cci, order_block | 6 | $106,883 | -24.8 | $28,308 | 64.0 | 12.0 | decision | 138 |
| 122 | bollinger, keltner, mfi, obv, order_block, sma_trend, structure_trend | 1 | $131,663 | -7.4 | $17,424 | 68.0 | 11.5 | decision | 346 |
| 123 | cci, keltner, obv, order_block, sma_trend | 3 | $121,307 | -14.7 | $25,622 | 64.2 | 10.8 | decision | 346 |
| 124 | bollinger, keltner, obv, order_block, structure_trend | 3 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 45 |
| 125 | bollinger, keltner, order_block, sma_trend, structure_trend | 3 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 126 | bollinger, obv, order_block, sma_trend, structure_trend | 3 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 127 | keltner, obv, order_block, sma_trend, structure_trend | 3 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 128 | structure_trend | 7 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 6 |
| 129 | bollinger, cci, keltner, mfi, obv, order_block | 2 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 138 |
| 130 | bollinger, cci, keltner, mfi, order_block, sma_trend | 2 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 131 | bollinger, cci, mfi, obv, order_block, sma_trend | 2 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 132 | cci, keltner, mfi, obv, order_block, sma_trend | 2 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 133 | bollinger, cci, keltner, mfi, obv, structure_trend | 2 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 138 |
| 134 | bollinger, cci, keltner, mfi, sma_trend, structure_trend | 2 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 135 | bollinger, cci, mfi, obv, sma_trend, structure_trend | 2 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 136 | cci, keltner, mfi, obv, sma_trend, structure_trend | 2 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 137 | bollinger, keltner, mfi, structure_trend | 4 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 45 |
| 138 | bollinger, mfi, obv, structure_trend | 4 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 45 |
| 139 | bollinger, mfi, sma_trend, structure_trend | 4 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 140 | keltner, mfi, obv, structure_trend | 4 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 40 |
| 141 | keltner, mfi, sma_trend, structure_trend | 4 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 142 | mfi, obv, sma_trend, structure_trend | 4 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 143 | cci, keltner, order_block, sma_trend | 4 | $113,233 | -20.4 | $25,622 | 63.9 | 10.8 | decision | 346 |
| 144 | bollinger, keltner, mfi, obv, order_block | 3 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 45 |
| 145 | bollinger, keltner, mfi, order_block, sma_trend | 3 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 146 | bollinger, mfi, obv, order_block, sma_trend | 3 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 147 | keltner, mfi, obv, order_block, sma_trend | 3 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 148 | bollinger, cci, order_block | 5 | $106,883 | -24.8 | $28,308 | 64.0 | 12.0 | decision | 138 |
| 149 | bollinger, cci, keltner, obv, order_block, sma_trend | 2 | $121,307 | -14.7 | $25,622 | 64.2 | 10.8 | decision | 346 |
| 150 | bollinger, keltner, obv, order_block, sma_trend, structure_trend | 2 | $120,833 | -15.0 | $15,491 | 65.3 | 11.5 | decision | 346 |
| 151 | bollinger, structure_trend | 6 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 45 |
| 152 | keltner, structure_trend | 6 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 40 |
| 153 | obv, structure_trend | 6 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 18 |
| 154 | sma_trend, structure_trend | 6 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 155 | bollinger, cci, keltner, mfi, obv, order_block, sma_trend | 1 | $125,194 | -12.0 | $26,209 | 65.8 | 10.8 | decision | 346 |
| 156 | bollinger, cci, keltner, mfi, obv, sma_trend, structure_trend | 1 | $125,066 | -12.1 | $16,455 | 67.1 | 11.5 | decision | 346 |
| 157 | bollinger, keltner, mfi, obv, structure_trend | 3 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 45 |
| 158 | bollinger, keltner, mfi, sma_trend, structure_trend | 3 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 159 | bollinger, mfi, obv, sma_trend, structure_trend | 3 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 160 | keltner, mfi, obv, sma_trend, structure_trend | 3 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 161 | bollinger, cci, keltner, order_block, sma_trend | 3 | $113,233 | -20.4 | $25,622 | 63.9 | 10.8 | decision | 346 |
| 162 | bollinger, keltner, mfi, obv, order_block, sma_trend | 2 | $117,058 | -17.7 | $30,282 | 65.1 | 10.8 | decision | 346 |
| 163 | cci, keltner, order_block | 5 | $101,889 | -28.4 | $28,263 | 63.4 | 10.8 | decision | 138 |
| 164 | bollinger, keltner, structure_trend | 5 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 45 |
| 165 | bollinger, obv, structure_trend | 5 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 45 |
| 166 | bollinger, sma_trend, structure_trend | 5 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 167 | keltner, obv, structure_trend | 5 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 40 |
| 168 | keltner, sma_trend, structure_trend | 5 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 169 | obv, sma_trend, structure_trend | 5 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 170 | bollinger, keltner, mfi, obv, sma_trend, structure_trend | 2 | $114,526 | -19.5 | $19,797 | 66.1 | 11.5 | decision | 346 |
| 171 | keltner, obv, order_block | 5 | $97,013 | -31.8 | $20,404 | 63.2 | 10.8 | decision | 40 |
| 172 | bollinger, cci, keltner, order_block | 4 | $101,889 | -28.4 | $28,263 | 63.4 | 10.8 | decision | 138 |
| 173 | bollinger, keltner, obv, structure_trend | 4 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 45 |
| 174 | bollinger, keltner, sma_trend, structure_trend | 4 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 175 | bollinger, obv, sma_trend, structure_trend | 4 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 176 | keltner, obv, sma_trend, structure_trend | 4 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 177 | mfi | 7 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 39 |
| 178 | bollinger, keltner, obv, order_block | 4 | $97,013 | -31.8 | $20,404 | 63.2 | 10.8 | decision | 45 |
| 179 | cci, mfi | 6 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 180 | obv, order_block | 6 | $85,960 | -39.5 | $30,125 | 63.5 | 10.8 | decision | 18 |
| 181 | bollinger, keltner, obv, sma_trend, structure_trend | 3 | $100,326 | -29.4 | $18,720 | 63.4 | 11.5 | decision | 346 |
| 182 | bollinger, mfi | 6 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 45 |
| 183 | keltner, mfi | 6 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 40 |
| 184 | mfi, obv | 6 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 39 |
| 185 | mfi, sma_trend | 6 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 186 | bollinger, cci, mfi | 5 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 187 | cci, keltner, mfi | 5 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 188 | cci, mfi, obv | 5 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 189 | cci, mfi, sma_trend | 5 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 190 | bollinger, obv, order_block | 5 | $85,960 | -39.5 | $30,125 | 63.5 | 10.8 | decision | 45 |
| 191 | cci, obv | 6 | $80,898 | -43.1 | $37,126 | 61.6 | 10.8 | decision | 138 |
| 192 | cci, sma_trend | 6 | $80,275 | -43.5 | $36,716 | 61.8 | 12.0 | decision | 346 |
| 193 | keltner, order_block, sma_trend | 5 | $85,059 | -40.2 | $20,404 | 62.7 | 10.8 | decision | 346 |
| 194 | bollinger, keltner, mfi | 5 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 45 |
| 195 | bollinger, mfi, obv | 5 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 45 |
| 196 | bollinger, mfi, sma_trend | 5 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 197 | keltner, mfi, obv | 5 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 40 |
| 198 | keltner, mfi, sma_trend | 5 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 199 | mfi, obv, sma_trend | 5 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 200 | keltner, order_block | 6 | $79,317 | -44.2 | $20,404 | 62.6 | 10.8 | decision | 40 |
| 201 | cci | 7 | $73,490 | -48.3 | $43,928 | 61.6 | 12.0 | decision | 138 |
| 202 | bollinger, cci, keltner, mfi | 4 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 203 | bollinger, cci, mfi, obv | 4 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 204 | bollinger, cci, mfi, sma_trend | 4 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 205 | cci, keltner, mfi, obv | 4 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 206 | cci, keltner, mfi, sma_trend | 4 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 207 | cci, mfi, obv, sma_trend | 4 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 208 | (none) | 8 | $66,709 | -53.1 | $35,728 | 60.3 | 10.8 | decision | 0 |
| 209 | obv, order_block, sma_trend | 5 | $81,534 | -42.7 | $26,994 | 62.7 | 10.8 | decision | 346 |
| 210 | keltner, obv, order_block, sma_trend | 4 | $85,927 | -39.6 | $20,404 | 62.4 | 10.8 | decision | 346 |
| 211 | bollinger, cci, obv | 5 | $80,898 | -43.1 | $37,126 | 61.6 | 10.8 | decision | 138 |
| 212 | bollinger, cci, sma_trend | 5 | $80,275 | -43.5 | $36,716 | 61.8 | 12.0 | decision | 346 |
| 213 | bollinger, keltner, order_block, sma_trend | 4 | $85,059 | -40.2 | $20,404 | 62.7 | 10.8 | decision | 346 |
| 214 | bollinger, keltner, mfi, obv | 4 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 45 |
| 215 | bollinger, keltner, mfi, sma_trend | 4 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 216 | bollinger, mfi, obv, sma_trend | 4 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 217 | keltner, mfi, obv, sma_trend | 4 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 218 | bollinger, keltner, order_block | 5 | $79,317 | -44.2 | $20,404 | 62.6 | 10.8 | decision | 45 |
| 219 | bollinger, cci | 6 | $73,490 | -48.3 | $43,928 | 61.6 | 12.0 | decision | 138 |
| 220 | cci, obv, sma_trend | 5 | $77,202 | -45.7 | $31,380 | 61.4 | 10.8 | decision | 346 |
| 221 | cci, keltner, obv | 5 | $76,945 | -45.9 | $34,722 | 61.4 | 10.8 | decision | 138 |
| 222 | bollinger, cci, keltner, mfi, obv | 3 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 138 |
| 223 | bollinger, cci, keltner, mfi, sma_trend | 3 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 224 | bollinger, cci, mfi, obv, sma_trend | 3 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 225 | cci, keltner, mfi, obv, sma_trend | 3 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 226 | bollinger | 7 | $66,709 | -53.1 | $35,728 | 60.3 | 10.8 | decision | 45 |
| 227 | bollinger, obv, order_block, sma_trend | 4 | $81,534 | -42.7 | $26,994 | 62.7 | 10.8 | decision | 346 |
| 228 | bollinger, keltner, obv, order_block, sma_trend | 3 | $85,927 | -39.6 | $20,404 | 62.4 | 10.8 | decision | 346 |
| 229 | bollinger, keltner, mfi, obv, sma_trend | 3 | $84,430 | -40.6 | $34,619 | 62.5 | 10.8 | decision | 346 |
| 230 | bollinger, cci, obv, sma_trend | 4 | $77,202 | -45.7 | $31,380 | 61.4 | 10.8 | decision | 346 |
| 231 | bollinger, cci, keltner, obv | 4 | $76,945 | -45.9 | $34,722 | 61.4 | 10.8 | decision | 138 |
| 232 | bollinger, cci, keltner, mfi, obv, sma_trend | 2 | $86,820 | -39.0 | $34,619 | 62.7 | 10.8 | decision | 346 |
| 233 | cci, keltner, obv, sma_trend | 4 | $73,249 | -48.5 | $28,976 | 61.1 | 10.8 | decision | 346 |
| 234 | bollinger, cci, keltner, obv, sma_trend | 3 | $73,249 | -48.5 | $28,976 | 61.1 | 10.8 | decision | 346 |
| 235 | cci, keltner | 6 | $57,789 | -59.4 | $42,417 | 60.5 | 10.8 | decision | 138 |
| 236 | cci, keltner, sma_trend | 5 | $62,771 | -55.9 | $36,188 | 60.7 | 10.8 | decision | 346 |
| 237 | bollinger, cci, keltner | 5 | $57,789 | -59.4 | $42,417 | 60.5 | 10.8 | decision | 138 |
| 238 | bollinger, cci, keltner, sma_trend | 4 | $62,771 | -55.9 | $36,188 | 60.7 | 10.8 | decision | 346 |
| 239 | keltner, obv | 6 | $52,625 | -63.0 | $21,123 | 60.2 | 10.8 | decision | 40 |
| 240 | bollinger, keltner, obv | 5 | $52,625 | -63.0 | $21,123 | 60.2 | 10.8 | decision | 45 |
| 241 | order_block, sma_trend | 6 | $46,688 | -67.2 | $15,771 | 62.8 | 12.3 | decision | 346 |
| 242 | obv | 7 | $39,585 | -72.2 | $42,118 | 60.0 | 10.8 | decision | 18 |
| 243 | obv, sma_trend | 6 | $41,755 | -70.6 | $36,161 | 59.9 | 10.8 | decision | 346 |
| 244 | bollinger, order_block, sma_trend | 5 | $46,688 | -67.2 | $15,771 | 62.8 | 12.3 | decision | 346 |
| 245 | keltner | 7 | $35,022 | -75.4 | $29,420 | 59.5 | 10.8 | decision | 40 |
| 246 | bollinger, obv | 6 | $39,585 | -72.2 | $42,118 | 60.0 | 10.8 | decision | 45 |
| 247 | keltner, sma_trend | 6 | $37,744 | -73.5 | $29,397 | 59.5 | 10.8 | decision | 346 |
| 248 | keltner, obv, sma_trend | 5 | $41,861 | -70.6 | $22,188 | 59.5 | 10.8 | decision | 346 |
| 249 | bollinger, obv, sma_trend | 5 | $41,755 | -70.6 | $36,161 | 59.9 | 10.8 | decision | 346 |
| 250 | bollinger, keltner | 6 | $35,022 | -75.4 | $29,420 | 59.5 | 10.8 | decision | 45 |
| 251 | bollinger, keltner, sma_trend | 5 | $37,744 | -73.5 | $29,397 | 59.5 | 10.8 | decision | 346 |
| 252 | bollinger, keltner, obv, sma_trend | 4 | $41,861 | -70.6 | $22,188 | 59.5 | 10.8 | decision | 346 |
| 253 | order_block | 7 | $18,653 | -86.9 | $13,531 | 64.6 | 36.0 | decision | 10 |
| 254 | bollinger, order_block | 6 | $18,653 | -86.9 | $13,531 | 64.6 | 36.0 | decision | 45 |
| 255 | sma_trend | 7 | $9,974 | -93.0 | $34,578 | 58.6 | 12.3 | decision | 346 |
| 256 | bollinger, sma_trend | 6 | $9,974 | -93.0 | $34,578 | 58.6 | 12.3 | decision | 346 |

_… 0 more rows in the JSON._

## Per-indicator marginal impact (avg ΔPnL when removed; sorted cheapest-to-drop first)

| indicator | avg PnL with | avg PnL without | avg drop cost |
|---|--:|--:|--:|
| sma_trend | $107,810 | $108,110 | $-300 |
| bollinger | $107,960 | $107,960 | $0 |
| keltner | $108,507 | $107,413 | $1,094 |
| obv | $109,766 | $106,154 | $3,612 |
| mfi | $115,870 | $100,050 | $15,820 |
| cci | $118,169 | $97,752 | $20,417 |
| order_block | $121,954 | $93,967 | $27,987 |
| structure_trend | $126,461 | $89,460 | $37,001 |
