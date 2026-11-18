# What each cable draws

Every Filaire cable draws its own values, aspect by aspect (see
[openusd.md](openusd.md) for where they are written). Each value follows a
rule applied to its preset's own numbers: the rules first, then the numbers
of every preset.

Both tables are written from `filaire/declared.py` and the presets, and
`tests/test_distributions.py` draws 1500 cables of every preset to check
that the generator follows them: every value lies in its declared range and
follows its rule (chi-square for choices, Kolmogorov-Smirnov for numbers, at
p > 0.001). It also builds one cable of each preset, to check that what the
cable records is what was drawn. Regenerate the tables with
`python -m filaire.declared`.

Weights are shown as shares of their total. The stiffness and density
ranges are realistic orders of magnitude, not measurements of real cables:
see [limits.md](limits.md).

The `clearance` aspect draws the opening of a receptacle whose opening is
published with a tolerance: today the USB-C (8.32 to 8.40 × 2.52 to
2.60 mm) and the USB-A (12.40 to 12.60 × 5.02 to 5.22 mm), each from one
manufacturer's drawing ([Sources](sources.md)). Each receptacle draws its own
width and height, uniformly over that tolerance, on its own stream: the
USB-C extension at the end of a `usb_c` cable, and the USB-C and USB-A ports
of `sockets.usdc`. Its cavity and its colliders follow. The plug is not
drawn (no published tolerance), nor are the families whose opening has
none. A cable or socket without such a receptacle does not list the aspect.

<!-- declared: begin -->
### Rules

| Column | Aspect | Drawn as | Note |
|---|---|---|---|
| `variation:nominal_length_m` | length | one of the preset's `lengths`, with its weights | with `--length preset`; else the length given (1 m) |
| `variation:length_m` | length | nominal × (1 + `tolerance` × e), e normal, kept within ±2.5 | with `--length preset`; else the length given, exact |
| `variation:layout` | layout | one of the preset's `layouts`, with its weights |  |
| `variation:end_a` | ends | one of the preset's `ends.a`, with its weights |  |
| `variation:end_b` | ends | one of the preset's `ends.b`, with its weights |  |
| `variation:color` | color | one of the preset's `colors`, each as likely |  |
| `variation:youngs_modulus_pa` | stiffness | uniform over the preset's `youngs_modulus`, × 1e+06 | the preset gives MPa |
| `variation:linear_density_kg_per_m` | density | uniform over the preset's `linear_density`, × 0.001 | the preset gives g/m |
| `variation:coil_leads_m` | length | uniform over the preset's `coil.leads`, × 0.001 | coiled cords only, one per end, in mm in the preset; recorded as built: rounded to whole segments |
| `variation:end_a_opening_m` | clearance | uniform over the opening's published tolerance, width and height each ([Sources](sources.md)) | width and height of a receptacle on the cable whose opening is published with a tolerance |
| `variation:end_b_opening_m` | clearance | uniform over the opening's published tolerance, width and height each ([Sources](sources.md)) | the same at end b (the `usb_c` extension) |
| `variation:opening_m` | clearance | uniform over the opening's published tolerance, width and height each ([Sources](sources.md)) | the fixed receptacles of `sockets.usdc` (USB-C, USB-A ports) |

### The presets' numbers

| Preset | `lengths` (m) | `tolerance` | `layouts` | `ends.a` | `ends.b` | `colors` | `youngs_modulus` (MPa) | `linear_density` (g/m) | `coil.leads` (mm) |
|---|---|---|---|---|---|---|---|---|---|
| `power_c13` | 1.0 20 %, 1.5 30 %, 1.8 30 %, 2.0 20 % | 0.01 | slack 60 %, coil 25 %, straight 15 % | c13_plug 100 % | cee77_plug 70 %, c13_inline 20 %, stripped 10 % | 4 | 60 to 120 | 60 to 70 |  |
| `power_c7` | 1.5 60 %, 1.8 40 % | 0.01 | slack 70 %, coil 15 %, straight 15 % | c7_plug 100 % | cee716_plug 85 %, stripped 15 % | 3 | 50 to 100 | 32 to 40 |  |
| `dc_barrel` | 1.0 30 %, 1.5 40 %, 1.8 30 % | 0.01 | slack 60 %, coil 25 %, straight 15 % | dc5521_plug 50 %, dc5525_plug 30 %, dc4017_plug 20 % | stripped 50 %, cut 20 %, dc5521_inline 30 % | 3 | 50 to 100 | 17 to 22 |  |
| `usb_c` | 0.5 20 %, 1.0 50 %, 2.0 30 % | 0.01 | slack 60 %, coil 20 %, straight 20 % | usb_c_plug 100 % | usb_c_plug 80 %, usb_c_inline 20 % | 4 | 40 to 90 | 20 to 30 |  |
| `usb_micro` | 0.5 30 %, 1.0 50 %, 2.0 20 % | 0.01 | slack 60 %, coil 20 %, straight 20 % | usb_a_plug 100 % | usb_micro_plug 100 % | 3 | 40 to 90 | 17 to 23 |  |
| `usb_a_to_c` | 1.0 60 %, 2.0 40 % | 0.01 | slack 60 %, coil 20 %, straight 20 % | usb_a_plug 100 % | usb_c_plug 100 % | 3 | 40 to 90 | 18 to 26 |  |
| `ethernet` | 0.5 20 %, 1.0 30 %, 2.0 30 %, 3.0 20 % | 0.005 | slack 60 %, coil 25 %, straight 15 % | rj45_plug 100 % | rj45_plug 85 %, rj45_inline 15 % | 6 | 80 to 150 | 30 to 36 |  |
| `hdmi` | 1.0 30 %, 1.5 30 %, 2.0 40 % | 0.01 | slack 60 %, coil 25 %, straight 15 % | hdmi_a_plug 100 % | hdmi_a_plug 85 %, hdmi_a_inline 15 % | 2 | 80 to 160 | 60 to 75 |  |
| `audio_jack` | 0.5 20 %, 1.0 50 %, 2.0 30 % | 0.01 | slack 65 %, coil 20 %, straight 15 % | jack35_plug 100 % | jack35_plug 80 %, jack35_inline 20 % | 4 | 30 to 70 | 12 to 20 |  |
| `xlr_mic` | 3.0 40 %, 5.0 40 %, 10.0 20 % | 0.01 | coil 50 %, slack 40 %, straight 10 % | xlr3_plug 100 % | xlr3_inline 100 % | 2 | 20 to 50 | 40 to 56 |  |
| `speaker_wire` | 2.0 40 %, 3.0 40 %, 5.0 20 % | 0.02 | slack 60 %, coil 30 %, straight 10 % | stripped 70 %, cut 30 % | stripped 70 %, cut 30 % | 3 | 40 to 90 | 34 to 40 |  |
| `m12_sensor` | 2.0 50 %, 5.0 50 % | 0.01 | coil 50 %, slack 40 %, straight 10 % | m12a_plug 100 % | stripped 80 %, cut 20 % | 3 | 50 to 100 | 28 to 36 |  |
| `ribbon_idc` | 0.15 40 %, 0.3 40 %, 0.5 20 % | 0.02 | straight 50 %, slack 50 % | idc10_plug 100 % | idc10_plug 90 %, cut 10 % | 2 | 150 to 300 | 17 to 22 |  |
| `can_bus` | 0.5 20 %, 1.0 30 %, 2.0 30 %, 5.0 20 % | 0.01 | slack 50 %, coil 40 %, straight 10 % | dsub9_plug 100 % | dsub9_plug 60 %, dsub9_inline 25 %, stripped 15 % | 3 | 60 to 120 | 68 to 80 |  |
| `servo_lead` | 0.15 30 %, 0.3 50 %, 0.5 20 % | 0.02 | slack 60 %, coil 20 %, straight 20 % | servo3_plug 100 % | servo3_inline 50 %, cut 30 %, stripped 20 % | 2 | 30 to 60 | 6 to 7.5 |  |
| `jumper_wire` | 0.1 30 %, 0.2 50 %, 0.3 20 % | 0.03 | slack 70 %, straight 30 % | pin_m_plug 50 %, pin_f_plug 50 % | pin_m_plug 50 %, pin_f_plug 30 %, pin_m_inline 20 % | 8 | 30 to 80 | 2.4 to 2.9 |  |
| `battery_lead` | 0.1 30 %, 0.15 30 %, 0.3 40 % | 0.03 | slack 60 %, straight 25 %, coil 15 % | batt35_plug 100 % | stripped 50 %, batt35_inline 50 % | 1 | 10 to 25 | 66 to 80 |  |
| `balance_lead` | 0.08 40 %, 0.1 40 %, 0.15 20 % | 0.03 | slack 60 %, straight 40 % | bal5_plug 100 % | stripped 80 %, cut 20 % | 1 | 10 to 25 | 18 to 23 |  |
| `bnc_coax` | 0.5 30 %, 1.0 40 %, 2.0 30 % | 0.01 | slack 60 %, coil 30 %, straight 10 % | bnc_plug 100 % | bnc_plug 70 %, bnc_inline 15 %, stripped 15 % | 3 | 150 to 250 | 36 to 40 |  |
| `coiled_handset` | 0.25 50 %, 0.35 50 % | 0.03 | straight 40 %, slack 60 % | rj9_plug 100 % | rj9_plug 100 % | 4 | 30 to 60 | 9 to 12 | 40 to 80 |
<!-- declared: end -->
