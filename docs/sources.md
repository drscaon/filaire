# Sources of the physical values

Every value of Filaire that describes the real world (a cable's diameter and
weight, a stiffness, a friction, a connector's dimensions) names its source
below: a manufacturer's datasheet of a cable of that kind, an engineering
table, or, where none was found, an estimate with what it rests on. Where a
source gives a range, the value lies within it, and so does every cable the
generator draws (`tests/test_sources.py`).

A preset is a kind of cable, not a product: its source is the datasheet of one
or two common cables of that kind (an H05VV-F 3G0.75 mm² cord for the C13
power cord, an RG-58 C/U for the BNC lead). Where a datasheet gives a single,
approximate weight, the range it allows is read as that weight ± 10 %. No
datasheet gives a cable's bending stiffness: every modulus is an estimate, and
nothing is calibrated (see [Checking a preset against a real
cable](physics.md#checking-a-preset-against-a-real-cable)).

Each connector family keeps the published figures it uses and the dimensions
that are not from a source in `filaire/connectors.py`; the second table lists
them, and [Connectors](connectors.md) describes each family.

The tables are written from `filaire/sources.py`
(`python -m filaire.sources`).

Part of the [Filaire](../README.md) documentation.

<!-- sources: begin -->
| Value | | Unit | Range the source gives | Source |
|---|---|---|---|---|
| `PRESETS.power_c13.profile.d` | 6.4 | mm | 6 to 7.6 | [h05vvf](#h05vvf) |
| `PRESETS.power_c13.linear_density.min` | 60 | g/m | 60 to 70 | [h05vvf](#h05vvf) |
| `PRESETS.power_c13.linear_density.max` | 70 | g/m | 60 to 70 | [h05vvf](#h05vvf) |
| `PRESETS.power_c13.youngs_modulus.min` | 60 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.power_c13.youngs_modulus.max` | 120 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.power_c13.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.power_c13.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.power_c13.lengths.1.5` | 1.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.power_c13.lengths.1.8` | 1.8 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.power_c13.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.power_c7.profile.d` | 3.2 | mm | 3.2 to 3.9 | [h03vvh2f](#h03vvh2f) |
| `PRESETS.power_c7.linear_density.min` | 32 | g/m | 32 to 40 | [h03vvh2f](#h03vvh2f) |
| `PRESETS.power_c7.linear_density.max` | 40 | g/m | 32 to 40 | [h03vvh2f](#h03vvh2f) |
| `PRESETS.power_c7.youngs_modulus.min` | 50 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.power_c7.youngs_modulus.max` | 100 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.power_c7.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.power_c7.lengths.1.5` | 1.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.power_c7.lengths.1.8` | 1.8 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.dc_barrel.profile.d` | 2.4 | mm |  | [thin_cord](#thin_cord) |
| `PRESETS.dc_barrel.linear_density.min` | 17 | g/m | to 28 | [thin_cord](#thin_cord) |
| `PRESETS.dc_barrel.linear_density.max` | 22 | g/m | to 28 | [thin_cord](#thin_cord) |
| `PRESETS.dc_barrel.youngs_modulus.min` | 50 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.dc_barrel.youngs_modulus.max` | 100 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.dc_barrel.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.dc_barrel.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.dc_barrel.lengths.1.5` | 1.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.dc_barrel.lengths.1.8` | 1.8 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_c.profile.d` | 4 | mm | 3.8 to 5.2 | [usb_c_cable](#usb_c_cable) |
| `PRESETS.usb_c.linear_density.min` | 20 | g/m | to 35.75 | [cable_weights](#cable_weights) |
| `PRESETS.usb_c.linear_density.max` | 30 | g/m | to 35.75 | [cable_weights](#cable_weights) |
| `PRESETS.usb_c.youngs_modulus.min` | 40 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.usb_c.youngs_modulus.max` | 90 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.usb_c.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.usb_c.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_c.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_c.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_micro.profile.d` | 3.5 | mm |  | [thin_cord](#thin_cord) |
| `PRESETS.usb_micro.linear_density.min` | 17 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.usb_micro.linear_density.max` | 23 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.usb_micro.youngs_modulus.min` | 40 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.usb_micro.youngs_modulus.max` | 90 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.usb_micro.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.usb_micro.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_micro.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_micro.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_a_to_c.profile.d` | 3.8 | mm |  | [thin_cord](#thin_cord) |
| `PRESETS.usb_a_to_c.linear_density.min` | 18 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.usb_a_to_c.linear_density.max` | 26 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.usb_a_to_c.youngs_modulus.min` | 40 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.usb_a_to_c.youngs_modulus.max` | 90 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.usb_a_to_c.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.usb_a_to_c.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.usb_a_to_c.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ethernet.profile.d` | 5.4 | mm | 5.2 to 5.6 | [telegaertner_cat6](#telegaertner_cat6) |
| `PRESETS.ethernet.linear_density.min` | 30 | g/m | 29.7 to 36.3 | [telegaertner_cat6](#telegaertner_cat6) |
| `PRESETS.ethernet.linear_density.max` | 36 | g/m | 29.7 to 36.3 | [telegaertner_cat6](#telegaertner_cat6) |
| `PRESETS.ethernet.youngs_modulus.min` | 80 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.ethernet.youngs_modulus.max` | 150 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.ethernet.tolerance` | 0.005 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.ethernet.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ethernet.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ethernet.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ethernet.lengths.3` | 3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.hdmi.profile.d` | 7.3 | mm | 7.1 to 7.5 | [hdmi_cable](#hdmi_cable) |
| `PRESETS.hdmi.linear_density.min` | 60 | g/m | to 75.67 | [cable_weights](#cable_weights) |
| `PRESETS.hdmi.linear_density.max` | 75 | g/m | to 75.67 | [cable_weights](#cable_weights) |
| `PRESETS.hdmi.youngs_modulus.min` | 80 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.hdmi.youngs_modulus.max` | 160 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.hdmi.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.hdmi.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.hdmi.lengths.1.5` | 1.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.hdmi.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.audio_jack.profile.d` | 3.5 | mm |  | [thin_cord](#thin_cord) |
| `PRESETS.audio_jack.linear_density.min` | 12 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.audio_jack.linear_density.max` | 20 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.audio_jack.youngs_modulus.min` | 30 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.audio_jack.youngs_modulus.max` | 70 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.audio_jack.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.audio_jack.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.audio_jack.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.audio_jack.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.xlr_mic.profile.d` | 6 | mm | 6 to 6.6 | [mic_cable](#mic_cable) |
| `PRESETS.xlr_mic.linear_density.min` | 40 | g/m | 40 to 56 | [mic_cable](#mic_cable) |
| `PRESETS.xlr_mic.linear_density.max` | 56 | g/m | 40 to 56 | [mic_cable](#mic_cable) |
| `PRESETS.xlr_mic.youngs_modulus.min` | 20 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.xlr_mic.youngs_modulus.max` | 50 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.xlr_mic.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.xlr_mic.lengths.3` | 3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.xlr_mic.lengths.5` | 5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.xlr_mic.lengths.10` | 10 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.speaker_wire.profile.d` | 3 | mm | 2.6 to 3 | [speaker_cable](#speaker_cable) |
| `PRESETS.speaker_wire.linear_density.min` | 34 | g/m | 33.3 to 40.7 | [speaker_cable](#speaker_cable) |
| `PRESETS.speaker_wire.linear_density.max` | 40 | g/m | 33.3 to 40.7 | [speaker_cable](#speaker_cable) |
| `PRESETS.speaker_wire.youngs_modulus.min` | 40 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.speaker_wire.youngs_modulus.max` | 90 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.speaker_wire.tolerance` | 0.02 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.speaker_wire.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.speaker_wire.lengths.3` | 3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.speaker_wire.lengths.5` | 5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.m12_sensor.profile.d` | 4.5 | mm | 4.275 to 4.725 | [murr_m12](#murr_m12) |
| `PRESETS.m12_sensor.linear_density.min` | 28 | g/m | 27.6 to 36.3 | [murr_m12](#murr_m12) |
| `PRESETS.m12_sensor.linear_density.max` | 36 | g/m | 27.6 to 36.3 | [murr_m12](#murr_m12) |
| `PRESETS.m12_sensor.youngs_modulus.min` | 50 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.m12_sensor.youngs_modulus.max` | 100 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.m12_sensor.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.m12_sensor.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.m12_sensor.lengths.5` | 5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ribbon_idc.profile.pitch` | 1.27 | mm |  | [3m_3365](#3m_3365) |
| `PRESETS.ribbon_idc.profile.thickness` | 0.89 | mm | 0.89 to 0.89 | [3m_3365](#3m_3365) |
| `PRESETS.ribbon_idc.linear_density.min` | 17 | g/m | 17 to 22 | [hookup_wire](#hookup_wire) |
| `PRESETS.ribbon_idc.linear_density.max` | 22 | g/m | 17 to 22 | [hookup_wire](#hookup_wire) |
| `PRESETS.ribbon_idc.youngs_modulus.min` | 150 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.ribbon_idc.youngs_modulus.max` | 300 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.ribbon_idc.tolerance` | 0.02 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.ribbon_idc.lengths.0.15` | 0.15 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ribbon_idc.lengths.0.3` | 0.3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.ribbon_idc.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.can_bus.profile.d` | 8.4 | mm | 8.1 to 8.7 | [can_cable](#can_cable) |
| `PRESETS.can_bus.linear_density.min` | 68 | g/m | 68 to 80 | [can_cable](#can_cable) |
| `PRESETS.can_bus.linear_density.max` | 80 | g/m | 68 to 80 | [can_cable](#can_cable) |
| `PRESETS.can_bus.youngs_modulus.min` | 60 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.can_bus.youngs_modulus.max` | 120 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.can_bus.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.can_bus.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.can_bus.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.can_bus.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.can_bus.lengths.5` | 5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.servo_lead.profile.pitch` | 1.05 | mm |  | [hookup_wire](#hookup_wire) |
| `PRESETS.servo_lead.profile.thickness` | 1.05 | mm |  | [hookup_wire](#hookup_wire) |
| `PRESETS.servo_lead.linear_density.min` | 6 | g/m |  | [hookup_wire](#hookup_wire) |
| `PRESETS.servo_lead.linear_density.max` | 7.5 | g/m |  | [hookup_wire](#hookup_wire) |
| `PRESETS.servo_lead.youngs_modulus.min` | 30 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.servo_lead.youngs_modulus.max` | 60 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.servo_lead.tolerance` | 0.02 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.servo_lead.lengths.0.15` | 0.15 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.servo_lead.lengths.0.3` | 0.3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.servo_lead.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.jumper_wire.profile.d` | 1.3 | mm |  | [hookup_wire](#hookup_wire) |
| `PRESETS.jumper_wire.linear_density.min` | 2.4 | g/m |  | [hookup_wire](#hookup_wire) |
| `PRESETS.jumper_wire.linear_density.max` | 2.9 | g/m |  | [hookup_wire](#hookup_wire) |
| `PRESETS.jumper_wire.youngs_modulus.min` | 30 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.jumper_wire.youngs_modulus.max` | 80 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.jumper_wire.tolerance` | 0.03 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.jumper_wire.lengths.0.1` | 0.1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.jumper_wire.lengths.0.2` | 0.2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.jumper_wire.lengths.0.3` | 0.3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.battery_lead.profile.d` | 4 | mm | 3.5 to 4.1 | [silicone_wire](#silicone_wire) |
| `PRESETS.battery_lead.linear_density.min` | 66 | g/m | 65.4 to 98.2 | [silicone_wire](#silicone_wire) |
| `PRESETS.battery_lead.linear_density.max` | 80 | g/m | 65.4 to 98.2 | [silicone_wire](#silicone_wire) |
| `PRESETS.battery_lead.youngs_modulus.min` | 10 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.battery_lead.youngs_modulus.max` | 25 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.battery_lead.tolerance` | 0.03 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.battery_lead.lengths.0.1` | 0.1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.battery_lead.lengths.0.15` | 0.15 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.battery_lead.lengths.0.3` | 0.3 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.balance_lead.profile.pitch` | 1.2 | mm |  | [hookup_wire](#hookup_wire) |
| `PRESETS.balance_lead.profile.thickness` | 1.2 | mm |  | [hookup_wire](#hookup_wire) |
| `PRESETS.balance_lead.linear_density.min` | 18 | g/m |  | [hookup_wire](#hookup_wire) |
| `PRESETS.balance_lead.linear_density.max` | 23 | g/m |  | [hookup_wire](#hookup_wire) |
| `PRESETS.balance_lead.youngs_modulus.min` | 10 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.balance_lead.youngs_modulus.max` | 25 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.balance_lead.tolerance` | 0.03 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.balance_lead.lengths.0.08` | 0.08 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.balance_lead.lengths.0.1` | 0.1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.balance_lead.lengths.0.15` | 0.15 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.bnc_coax.profile.d` | 4.95 | mm | 4.83 to 5.07 | [rg58](#rg58) |
| `PRESETS.bnc_coax.linear_density.min` | 36 | g/m | 36 to 40 | [rg58](#rg58) |
| `PRESETS.bnc_coax.linear_density.max` | 40 | g/m | 36 to 40 | [rg58](#rg58) |
| `PRESETS.bnc_coax.youngs_modulus.min` | 150 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.bnc_coax.youngs_modulus.max` | 250 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.bnc_coax.tolerance` | 0.01 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.bnc_coax.lengths.0.5` | 0.5 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.bnc_coax.lengths.1` | 1 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.bnc_coax.lengths.2` | 2 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.coiled_handset.profile.d` | 2.8 | mm |  | [thin_cord](#thin_cord) |
| `PRESETS.coiled_handset.linear_density.min` | 9 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.coiled_handset.linear_density.max` | 12 | g/m |  | [thin_cord](#thin_cord) |
| `PRESETS.coiled_handset.youngs_modulus.min` | 30 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.coiled_handset.youngs_modulus.max` | 60 | MPa |  | [stiffness](#stiffness) |
| `PRESETS.coiled_handset.tolerance` | 0.03 |  |  | [length_tolerance](#length_tolerance) |
| `PRESETS.coiled_handset.lengths.0.25` | 0.25 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.coiled_handset.lengths.0.35` | 0.35 | m |  | [retail_lengths](#retail_lengths) |
| `PRESETS.coiled_handset.coil.diameter` | 8.5 | mm |  | [coiled_cord](#coiled_cord) |
| `PRESETS.coiled_handset.coil.pitch` | 1.05 | × wire |  | [coiled_cord](#coiled_cord) |
| `PRESETS.coiled_handset.coil.leads.min` | 40 | mm |  | [coiled_cord](#coiled_cord) |
| `PRESETS.coiled_handset.coil.leads.max` | 80 | mm |  | [coiled_cord](#coiled_cord) |
| `POISSON` | 0.45 |  |  | [poisson](#poisson) |
| `JACKETS.pvc.friction` | 0.6 |  | 0.6 to 0.7 | [friction_table](#friction_table) |
| `JACKETS.pvc.restitution` | 0.1 |  |  | [restitution](#restitution) |
| `JACKETS.tpe.friction` | 0.7 |  | 0.6 to 0.7 | [friction_table](#friction_table) |
| `JACKETS.tpe.restitution` | 0.15 |  |  | [restitution](#restitution) |
| `JACKETS.pur.friction` | 0.5 |  | to 0.6 | [pur_friction](#pur_friction) |
| `JACKETS.pur.restitution` | 0.1 |  |  | [restitution](#restitution) |
| `JACKETS.lszh.friction` | 0.6 |  | 0.6 to 0.7 | [friction_table](#friction_table) |
| `JACKETS.lszh.restitution` | 0.1 |  |  | [restitution](#restitution) |
| `JACKETS.silicone.friction` | 0.9 |  | 0.85 to 0.95 | [friction_table](#friction_table) |
| `JACKETS.silicone.restitution` | 0.1 |  |  | [restitution](#restitution) |
| `CONNECTOR_FRICTION` | 0.4 |  | 0.3 to 0.4 | [friction_table](#friction_table) |
| `CONNECTOR_RESTITUTION` | 0.2 |  |  | [restitution](#restitution) |
| `cable.STRIP_INSULATION` | 12 | mm |  | [strip](#strip) |
| `cable.STRIP_COPPER` | 6 | mm |  | [strip](#strip) |
| `CONNECTORS.usb_c.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.usb_c.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.usb_c.clearance_width` | 0.045 | mm | 0.035 to 0.075 | [usb_c_receptacle](#usb_c_receptacle) |
| `CONNECTORS.usb_c.clearance_height` | 0.08 | mm | 0.06 to 0.1 | [usb_c_receptacle](#usb_c_receptacle) |
| `CONNECTORS.usb_a.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.usb_a.clearance` | 0.08 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.usb_a.clearance_width` | 0.25 | mm | 0.2 to 0.3 | [usb_a_interface](#usb_a_interface) |
| `CONNECTORS.usb_a.clearance_height` | 0.31 | mm | 0.26 to 0.36 | [usb_a_interface](#usb_a_interface) |
| `CONNECTORS.hdmi_a.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.hdmi_a.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.hdmi_a.clearance_width` | 0.05 | mm | 0.05 to 0.05 | [hdmi_interface](#hdmi_interface) |
| `CONNECTORS.hdmi_a.clearance_height` | 0.05 | mm | 0.05 to 0.05 | [hdmi_interface](#hdmi_interface) |
| `CONNECTORS.rj45.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.rj45.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.rj9.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.rj9.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.jack35.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.jack35.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.jack35.clearance_width` | 0.05 | mm | 0.05 to 0.05 | [jack35_socket](#jack35_socket) |
| `CONNECTORS.jack35.clearance_height` | 0.05 | mm | 0.05 to 0.05 | [jack35_socket](#jack35_socket) |
| `CONNECTORS.c13.density` | 1300 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.c13.clearance` | 0.2 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.c7.density` | 1300 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.c7.clearance` | 0.2 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.cee77.density` | 1200 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.cee77.clearance` | 0.3 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.cee716.density` | 1200 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.cee716.clearance` | 0.3 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.xlr3.density` | 2500 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.xlr3.clearance` | 0.2 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.m12a.density` | 2500 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.m12a.clearance` | 0.15 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.usb_micro.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.usb_micro.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.dc5521.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.dc5521.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.dc5525.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.dc5525.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.dc4017.density` | 1400 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.dc4017.clearance` | 0.05 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.idc10.density` | 1300 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.idc10.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.servo3.density` | 1300 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.servo3.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.pin_m.density` | 2500 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.pin_m.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.pin_f.density` | 1300 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.pin_f.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.batt35.density` | 2200 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.batt35.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.bal5.density` | 1300 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.bal5.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.dsub9.density` | 2200 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.dsub9.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |
| `CONNECTORS.bnc.density` | 4500 | kg/m³ |  | [connector_body](#connector_body) |
| `CONNECTORS.bnc.clearance` | 0.1 | mm |  | [connector_body](#connector_body) |

### Connector dimensions

| Family | Standard | Published figures used | Not from a source |
|---|---|---|---|
| `usb_c` | USB Type-C Cable and Connector Specification | receptacle opening 8.34 × 2.56, plug insertion length ≈ 6.65: https://www.accesscomms.com.au/usb-connector-dimensions/; receptacle opening 8.34 +0.06/−0.02 × 2.56 ± 0.04: GCT USB4900 drawing, https://www.mouser.lt/datasheet/3/1507/1/usb4900.pdf | plug inner cavity 6.95 × 1.00 (receptacle tongue); overmold 12 × 6.5 × 18 |
| `usb_a` | USB 2.0 Specification (Standard-A) | plug body length ≈ 12: https://www.accesscomms.com.au/usb-connector-dimensions/; plug shell 12.00 × 4.50, receptacle opening 12.50 × 5.12: Adam Tech USB-A drawings, https://dtsheet.com/doc/1419227/usb-connector; receptacle opening 12.50 ± 0.10 × 5.12 ± 0.10: TE Connectivity 108-1586, https://en.eeworld.com.cn/datasheet/view/3886042.html | inner cavity (receptacle tongue) 11.2 × 1.85, upper half |
| `hdmi_a` | HDMI Specification (Type A) | plug 13.9 × 4.45, receptacle 14 × 4.55: https://en.wikipedia.org/wiki/HDMI | bottom chamfers 1.3; insertion depth 9.5; inner cavity 10.9 × 1.5 |
| `rj45` | IEC 60603-7 (8-way modular) | plug 11.68 wide, 8.00 high with latch, 22.48 long; insertion height 6.60: https://en.wikipedia.org/wiki/Modular_connector | latch 4.2 wide; insertion depth 14; boot 13 × 10 × 16 |
| `rj9` | 4-way modular (handset) | plug width 7.7: https://en.wikipedia.org/wiki/Modular_connector | height 6.60 (modular insertion height); latch; insertion depth 10 |
| `jack35` | IEC 60603-11 (3.5 mm) | Ø3.5, length 15: https://en.wikipedia.org/wiki/Phone_connector_(audio); socket bore Ø3.60: Same Sky SJ3-35083D, https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/SJ3-35083D-TR/24627981 | overmold Ø6 × 18; insulator rings at 4.0–5.5 and 7.7–9.2 from the tip |
| `c13` | IEC 60320-1 | pin centres 14 mm across, 4 mm vertical offset: https://en.wikipedia.org/wiki/IEC_60320 | face 24.0 × 15.5 with 4.5 chamfers; blade holes 2.4 × 4.6; depth 13 |
| `c7` | IEC 60320-1 | pin centres 8.6 mm, C8 inlet 10 mm deep: https://en.wikipedia.org/wiki/IEC_60320 | lobes Ø9.2; pin holes Ø2.6 |
| `cee77` | CEE 7 | pins 4.8 × 19 mm, 19 mm apart; CEE 7/5 recess 15 mm deep: https://en.wikipedia.org/wiki/CEE_7 | plug face Ø36; socket without earth pin or clips; grip 40 × 38 × 30 |
| `cee716` | CEE 7 | pin length and spacing as CEE 7/6: https://en.wikipedia.org/wiki/CEE_7 | pins Ø4.0, parallel; body 35 × 13.5; recess 6 |
| `xlr3` | IEC 61076-2-103 | no published dimensions found; IEC 61076-2-103 not consulted | insert Ø19 with 2.6 key groove; pin positions; depth 11; male shell Ø23 |
| `m12a` | IEC 61076-2-101 | thread M12 × 1 (IEC 61076-2-101, not consulted) | insert Ø10; key 1.6; pins on Ø5; nut Ø15 / bore Ø12.6 |
| `usb_micro` | USB 2.0 Specification (Micro-B) | receptacle opening 6.85 × 1.8: https://www.accesscomms.com.au/usb-connector-dimensions/ | plug 6.80 × 1.75 with 0.75 chamfers; tongue cavity 5.6 × 0.62; insertion depth 5.6 |
| `dc5521` | IEC 60130-10 | 5.5 × 2.1 mm: IEC 60130-10 Type A, https://en.wikipedia.org/wiki/Coaxial_power_connector | plug length 9.5; overmold and jack body |
| `dc5525` | IEC 60130-10 | 5.5 × 2.5 mm: IEC 60130-10 Type A, https://en.wikipedia.org/wiki/Coaxial_power_connector | plug length 9.5; overmold and jack body |
| `dc4017` | EIAJ RC-5320A | 4 × 1.7 mm: EIAJ-02, https://en.wikipedia.org/wiki/Coaxial_power_connector; barrel length 9.5 (EIAJ-02): https://en.wikipedia.org/wiki/Coaxial_power_connector | overmold and jack body |
| `idc10` | IDC ribbon socket, 0.1 in pitch | 2.54 mm pin pitch (0.1 in) | socket 15.0 × 6.2 with key 4.6; box header 20.3 × 8.85; depth 6 |
| `servo3` | 3-way crimp housing, 0.1 in pitch (hobby servo) | 2.54 mm (0.1 in) pitch, 1 × 3: https://www.pololu.com/product/1902/specs; 0.64 mm square posts: https://mantech.co.za/datasheets/products/XH-JST.pdf | housing 7.6 × 2.6 with a 1.6 × 0.6 rib, 14.5 long; receiver slot 10 × 5; depth 6 |
| `pin_m` | 0.1 in pitch jumper wire | 2.54 mm pitch, 0.64 mm square posts: https://mantech.co.za/datasheets/products/XH-JST.pdf | housing 2.5 × 2.5 × 14; pin 6 long; breadboard block 7.62 square |
| `pin_f` | 0.1 in pitch jumper wire | 2.54 mm pitch, 0.64 mm square posts: https://mantech.co.za/datasheets/products/XH-JST.pdf | housing 2.5 × 2.5 × 14; post 6 above a 2.5 base |
| `batt35` | 2-pole battery connector, 3.5 mm bullets, 7.2 mm pitch | 7.2 mm pitch: https://altronics.cl/uploads/XT-60.pdf; 3.5 mm bullets | front 13.6 × 6.4 with 1.6 chamfers, body 15.8 × 8.2 with 2.0 chamfers; insertion depth 8 |
| `bal5` | 5-way wire-to-board housing, 2.5 mm pitch | header width 2.5 (n − 1) + 4.9, 0.64 mm posts: https://mantech.co.za/datasheets/products/XH-JST.pdf | housing 12.9 × 4.2 with two 1.2 ribs; header depth 6; insertion depth 6 |
| `dsub9` | IEC 60807-3 / MIL-DTL-24308, shell size E | male shell 16.92 × 8.36, flange 30.81 × 12.55: https://www.farnell.com/datasheets/2722993.pdf; 2.77 mm pitch: https://uk.rs-online.com/p/d-sub-connectors/2411334 | female D 16.30 × 7.80 (male shell 16.92 × 8.36 less its wall); row spacing 2.84; hood 31.5 × 15.5 × 32; engagement 6 |
| `bnc` | IEC 61169-8 | interface (barrel 9.78–9.91, sleeve ≥ 10.52 inside, pin 1.32–1.37, 1/4 turn): https://www.chipfind.net/static/pdf/amphenol/bnc_coaxial_connectors.pdf; coupling nut Ø14.50: https://www.milestek.com/media/descriptions/productspecs/MTCN0001.pdf | studs Ø2.1, 5.5 from the jack's front, out to Ø12.6; slot 2.4 wide, entry 4.95 deep; barrel 9.9 × 11.5; crimp ferrule Ø8.6 × 8, boot Ø7.2 × 14 |

### Sources

- <a id="h05vvf"></a>**h05vvf** (datasheet): H05VV-F 3G0.75 mm² (EN 50525-2-11), the cord of a C13 power lead: Helukabel 29453, outer Ø 6.0 to 7.6 mm, approx. 60 kg/km; Klaus Faber 030016, outer Ø approx. 6.50 mm, 70 kg/km. <https://shop.helukabel.com/cz-en/h05vv-f-05vv-f-m29450/29453>, <https://shop.faberkabel.de/en/Flexible-wires/Insulated-Cords/H05VV-F/030016.html>
- <a id="h03vvh2f"></a>**h03vvh2f** (datasheet): H03VVH2-F 2 × 0.75 mm², the flat figure-8 cord of a C7 lead: Sonepar sheet 3.2 × 5.2 to 3.8 × 6.3 mm, 37 kg/km; Klaus Faber 031049, 6.4 × 3.9 mm, 39 kg/km; Böhm, 32 kg/km; Letronic, 4.0 / 5.6 mm, 40 kg/km. Filaire's figure-8 is d high and 2 d wide. <https://res.cloudinary.com/sonepar-fr/raw/upload/s--s3hkfwIM--/v1/documents/49/H03VVH2-F.pdf>, <https://shop.faberkabel.de/out/downloads/uploads/EN/dbl_h03vvh2.pdf>, <https://www.icsgroup.ru/boehm-kabel/files/H03VVH2-F.pdf>, <https://letronic.de/en/produkte/datenblatt/679/h03vvh2-f>
- <a id="usb_c_cable"></a>**usb_c_cable** (datasheet): USB-C to USB-C cables: Delock 83867, cable diameter approx. 4.0 mm; Tripp Lite U040-C1M-C-5A, 3.8 mm; Eaton U420-01M-G25ARA, 5.2 mm. <https://www.tme.eu/Document/56902cdf7b045b7ebe7c3a5ed13f06f3/DELOCK-83867_EN.pdf>, <https://www.mouser.com/datasheet/2/411/u040c1mc5a-1717239.pdf>, <https://www.eaton.com/us/en-us/skuPage.U420-01M-G25ARA.html>
- <a id="telegaertner_cat6"></a>**telegaertner_cat6** (datasheet): Telegärtner Cat.6 U/UTP patch cable 4 × 2 × AWG24/7, PVC: outer diameter 5.4 ± 0.2 mm, weight 33 kg/km. <https://www.telegaertner.com/fileadmin/pdms_files/100013078_DST_EN.pdf>
- <a id="hdmi_cable"></a>**hdmi_cable** (datasheet): High Speed HDMI cables, 28 AWG: Delock 82583, cable diameter approx. 7.3 mm; Secomp 11.99.5740, OD 7.3 ± 0.2 mm. <https://www.tme.eu/Document/80c86638e858ac17d0910e7811f372ea/DELOCK-82583_EN.pdf>, <https://www.secomp.de/media/pdf/s11/11995740_en_data_scmp.pdf>
- <a id="mic_cable"></a>**mic_cable** (datasheet): 2 × 0.22 mm² microphone cables: Klotz MY206, Ø 6.0 mm, 0.04 kg/m; Sommer Stage 22 Highflex, Ø 6.40 mm, 47 g/m; Cordial CMK 222, 6.4 ± 0.2 mm, 53 g/m; Sommer Stage 22 Highflex VT, 6.5 mm, 56 g/m. <https://www.bax-shop.fr/downloads/products/9000-0143-3209/my206_e.pdf>, <https://cdn.shopify.com/s/files/1/0460/9785/8718/files/200-0001.pdf>, <https://www.thomann.de/be/cordial_cmk_222_sw.htm>, <https://www.thomann.de/be/sommer_cable_sc_stage_22_highflex_vt.htm>
- <a id="speaker_cable"></a>**speaker_cable** (datasheet): 2 × 1.5 mm² flat speaker cables: Helukabel 40025, 5.5 × 2.6 mm, approx. 37 kg/km; Prysmian (Draka) Speaker 2 × 1.5 mm² flat, 3.0 × 6.5 mm. Filaire's figure-8 is d high and 2 d wide. <https://shop.helukabel.com/at-en/speaker-cable-m40180/40025>, <https://mrcable.ru/upload/iblock/f5a/0lynreubljpvhg1e13rdt12gr7ekv1wz.pdf>
- <a id="murr_m12"></a>**murr_m12** (datasheet): Murrelektronik M12 sensor cables, PUR 4 × 0.34 mm²: outer diameter 4.5 mm ± 5 %, cable weight 27.6, 33 and 36.3 g/m (cable types 3 and 634). <https://www.mouser.lt/datasheet/3/5927/2/7004_12341_6342500_Product_PDF_en.pdf>, <https://www.mouser.lt/datasheet/3/5927/1/7000_40021_0340500_Product_PDF_en.pdf>, <https://static.chipdip.ru/lib/045/DOC045045007.pdf>
- <a id="3m_3365"></a>**3m_3365** (datasheet): 3M 3365/10 round-conductor flat cable: 10 conductors 28 AWG (7/36), pitch 1.27 mm, ribbon thickness 0.89 mm (0.035 in), width 12.70 mm. <https://azcus.digikey.com/en/products/detail/3m/3365-10-100/1107680>
- <a id="can_cable"></a>**can_cable** (datasheet): CAN bus cables 2 × 2 × 0.25 mm², PUR: Helukabel 801982, Ø 8.4 ± 0.3 mm, approx. 80 kg/km; Klaus Faber 101632, Ø 8.4 mm, 68 kg/km. <https://assets-cdn.helukabel.com/suppliers/Helukabel/documents/db/HELUKABEL_M801982_EN_GB.pdf>, <https://www.icsgroup.ru/faber/files/dbl_bus_can_pur.pdf>
- <a id="silicone_wire"></a>**silicone_wire** (datasheet): Lapp ÖLFLEX HEAT 180 SiF A, single silicone wire: 14 AWG Ø 3.5 mm, approx. 22 lbs/mft (32.7 kg/km); 12 AWG Ø 4.1 mm, approx. 33 lbs/mft (49.1 kg/km). A battery lead is two of them, of 14 or 12 AWG. <https://advantageelectricsupplystoragepublic.s3-us-west-1.amazonaws.com/PartAttachment/2093214/Datasheet.pdf>
- <a id="rg58"></a>**rg58** (datasheet): RG 58 C/U coaxial cable: Lapp 2170000, outer diameter 4.95 ± 0.12 mm, approx. 36 kg/km; Huber+Suhner RG_58_C/U, ø 4.95 mm, approx. 37 g/m; RG58 C/U LSF (RS), 4.95 ± 0.2 mm, 40 kg/km. <https://static.rapidonline.com/pdf/67-5860_v1.pdf>, <https://www.mouser.com/datasheet/3/1498/1/H_S_RG_58_CU_EN.PDF>, <https://nonprod.docs.rs-online.com/024f/0900766b80626139.pdf>
- <a id="friction_table"></a>**friction_table** (handbook): University of Florida, design lab: static friction on dry concrete and dry wood, soft rubber 0.85 and 0.95, soft plastic 0.6 and 0.7, hard plastic 0.3 and 0.4 (after Engineering ToolBox). <https://web.mae.ufl.edu/designlab/Class%20Projects/Background%20Information/Friction%20coefficients.htm>
- <a id="thin_cord"></a>**thin_cord** (estimate): diameter and weight of the thin cords no datasheet was found for (DC barrel, USB micro-B and A-to-C, 3.5 mm audio, coiled handset). Estimate: the weight is that of the cross-section: its copper (8.96 g/cm³, the cores and shield of the cable's kind) plus the rest in PVC or TPE (1.0 to 1.4 g/cm³); a DC cord lies under H03VVH2-F 2 × 0.5 mm² (3.0 × 4.9 mm, 28 kg/km); a USB 2.0 cable's diameter is that of USB-C cables of 3.5 to 4 mm.
- <a id="cable_weights"></a>**cable_weights** (estimate): weight of USB-C and HDMI cables, whose datasheets give the diameter only. Estimate: the weight of whole cables with their plugs bounds it from above: StarTech USB2CC4MBKE, a 4 m USB-C cable of 143 g (≤ 36 g/m), StarTech HDMM3MHS, a 3 m 28 AWG HDMI cable of 227 g (≤ 76 g/m); the lower end is the copper and PVC of the cross-section. <https://manuals.plus/m/dbbe6d8b0576cc227de6880275c7590ad513fa6616d5b2a5825dc9dfaac89c4e>, <https://www.farnell.com/datasheets/4813596.pdf>
- <a id="hookup_wire"></a>**hookup_wire** (estimate): diameter and weight of the hobby leads (servo, jumper, balance) and of a ribbon cable's PVC. Estimate: from the cross-section: 26 AWG cores in a 1.05 mm servo wire, 26 to 28 AWG in a 1.3 mm jumper wire, 22 AWG in a 1.2 mm balance wire, with copper (8.96 g/cm³) and PVC or silicone (1.1 to 1.4 g/cm³); for the ribbon, 22 g/m for its full section against 17.9 g/m (544 g per 30.48 m roll) from a dealer. <https://ibselectronics.in/products/3m/3365-10-100>
- <a id="stiffness"></a>**stiffness** (estimate): the effective Young's modulus of a whole cable (jacket, insulation, stranded copper). Estimate: no datasheet gives a cable's bending stiffness; set by kind (soft leads 10 to 25 MPa, cords 20 to 160 MPa, coax and ribbon 150 to 300 MPa) to the orders of magnitude of the published E·I (docs/physics.md, Checking a preset against a real cable). Not calibrated.
- <a id="poisson"></a>**poisson** (estimate): the Poisson ratio that gives a cable's torsional stiffness from its modulus. Estimate: close to 0.5, as for the rubbery polymers of jackets; the stranded copper inside does not carry torsion as a solid would.
- <a id="pur_friction"></a>**pur_friction** (estimate): friction of a PUR jacket. Estimate: under soft plastic's 0.6: PUR jackets are made low-adhesion for cable tracks (igus CFBUS.PUR). <https://komplekt-a.ru/image/catalog/pdf/cfbus.pur.pdf>
- <a id="restitution"></a>**restitution** (estimate): restitution of a jacket or a connector on the floor. Estimate: cables barely bounce: 0.1 for jackets, 0.15 for TPE, 0.2 for the harder connector bodies.
- <a id="length_tolerance"></a>**length_tolerance** (estimate): spread of a cable's length around its nominal length (relative standard deviation). Estimate: cable datasheets give length tolerances of 0.4 % to 2.5 % (USB-C 4000 ± 15 mm and 500 ± 15 mm, HDMI 7500 ± 80 mm); 0.5 % to 3 % of standard deviation, wider for hand-made hobby leads. <https://cdn.iceshop.nl/objects/mmo_114675195_1694772804_3444_50.pdf>, <https://www.secomp.de/media/pdf/s11/11995740_en_data_scmp.pdf>
- <a id="retail_lengths"></a>**retail_lengths** (estimate): nominal lengths of each kind of cable. Estimate: the lengths cables of the kind are commonly sold in; their weights are a choice, not a statistic.
- <a id="coiled_cord"></a>**coiled_cord** (estimate): coil diameter, pitch and straight leads of a coiled handset cord. Estimate: measured on photographs of handset cords: close-wound, about 8 to 9 mm across, 4 to 8 cm of straight cord at each end.
- <a id="usb_c_receptacle"></a>**usb_c_receptacle** (datasheet): USB Type-C receptacle opening 8.34 +0.06/−0.02 × 2.56 ± 0.04 mm (GCT USB4900); the plug's shell 8.25 × 2.40 mm. One manufacturer's tolerance: the plug's own is not included. <https://www.mouser.lt/datasheet/3/1507/1/usb4900.pdf>
- <a id="usb_a_interface"></a>**usb_a_interface** (datasheet): USB 2.0 Standard-A receptacle opening 12.50 ± 0.10 × 5.12 ± 0.10 mm (TE Connectivity 108-1586), plug shell 12.00 × 4.50 mm (Adam Tech). The receptacle's spring tabs, which take up part of this play on a real port, are not modelled. <https://en.eeworld.com.cn/datasheet/view/3886042.html>, <https://dtsheet.com/doc/1419227/usb-connector>
- <a id="hdmi_interface"></a>**hdmi_interface** (handbook): HDMI Type A plug 13.9 × 4.45 mm, receptacle 14 × 4.55 mm (nominal, no tolerance given). <https://en.wikipedia.org/wiki/HDMI>, <https://uk.rs-online.com/web/content/product-knowledge/computing-networking/display-video-technology/hdmi-connectors-guide>
- <a id="jack35_socket"></a>**jack35_socket** (datasheet): 3.5 mm socket bore Ø3.60 mm (Same Sky SJ3-35083D, Adam Tech ASJ series) for a Ø3.5 mm plug (nominal, no tolerance given). <https://www.digikey.com/en/products/detail/same-sky-formerly-cui-devices/SJ3-35083D-TR/24627981>, <https://zenode.ai/parts/pxm2n5epom>
- <a id="connector_body"></a>**connector_body** (estimate): effective density of a connector (plastic body with metal parts) and its clearance in its receptacle (where no opening is published: around the outline; else inside and at the tip). Estimate: between plastic (1.0 to 1.4 g/cm³) and brass or steel, by the share of metal: 1.2 to 1.4 g/cm³ for moulded plugs, 2.2 to 2.5 for metal-shelled ones, 4.5 for a BNC; clearances of 0.05 to 0.3 mm, tighter for the small precise connectors.
- <a id="strip"></a>**strip** (estimate): length of insulated core and of bare copper at a stripped end. Estimate: 12 mm of core out of the jacket and 6 mm of bare copper, as for a screw terminal.

### Numbers that are not physical values

- `PRESETS.*.lengths weights, layouts, ends, colors`: how often each nominal length, layout, end and colour is drawn: a choice, declared in docs/variation.md.
- `generator.DEFAULT_LENGTH`: the length generated when none is asked for (1 m): a choice.
- `cable.DAMPING_TIME`: the joints' damping as a time constant: a simulation setting (docs/physics.md).
- `physx.CONTACT_OFFSET, REST_OFFSET, POSITION_ITERATIONS, VELOCITY_ITERATIONS, MAX_DEPENETRATION_VELOCITY`: solver settings of the PhysX layer.
- `newton.ARMATURE_DT, ARMATURE_PERIOD`: the armature the Newton layer adds to each segment's inertia, sized as the MuJoCo model's (sim/mujoco_model.py): an engine setting.
- `newton.LIMIT`: the rotation limit the Newton layer adds between segments (±170°), wide enough never to be reached: an engine setting, not a property of the cable.
- `JACKETS.*.roughness, connectors colours, SHELL_WALL`: render appearance, not a physical property.
- `connectors.TWIST_STEP`: how finely a bayonet's turn is sampled to cut its receptacle.
- `declared.CLIP`: the length's normal draw is kept within ±2.5 standard deviations: a choice.
<!-- sources: end -->
