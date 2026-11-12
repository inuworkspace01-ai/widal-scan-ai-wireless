# WIDAL-SCAN Automated Analyzer — Hardware Concept Rev 0.1

> Concept design only. Not a manufactured device, not validated for clinical testing, and not a medical diagnosis system.

## 1. Key workflow correction

The Widal tube agglutination procedure reacts **patient serum** with the relevant antigen suspension. It does not simply put untreated whole blood directly onto the O/H reagents. The first prototype should accept pre-separated, clear serum in a labelled tube. Whole-blood processing would require an additional validated clotting/centrifugation workflow and is intentionally out of scope for the first build.

## 2. Process architecture

1. Register the sample ID, sample type, reagent-kit lot and the exact IFU/SOP revision.
2. Load a clear serum tube into the sample rack.
3. Aspirate serum with a calibrated pipetting module and a fresh disposable tip.
4. Prepare the saline dilution series. Maintain separate, traceable O and H reaction rows and reserve negative/positive controls according to the kit's IFU.
5. Dispense O and H antigen suspensions into their corresponding reaction positions.
6. Mix using the precise technique defined by the selected kit IFU. A generic high-speed orbital shake must not be assumed safe for every protocol.
7. Incubate at the IFU-defined temperature and duration; monitor and log temperature continuously.
8. Capture each tube/well with a fixed-focus camera, diffuse fixed illumination, fixed background and position calibration.
9. Produce an image/measurement candidate for ATLM review. Store the image, reagent lot, dilution map, temperature trace, timestamps, device ID and operator approval.
10. Close the run, dispose of single-use tips and reaction consumables in the designated biohazard waste stream, and clean reusable surfaces per laboratory SOP.

### Dilution example

Two-fold dilution ladders are common, but starting dilution and reaction volumes vary across methods and commercial IFUs. One IFU describes final dilutions from 1:20 through 1:1280 with incubation at 37 °C overnight; another published protocol describes a different starting point and incubation conditions. Therefore the app must select a versioned kit-specific recipe. It must not hard-code 1:80, a universal incubation temperature, or a universal duration.

Sources:
- VITAL Widal Antigen IFU: https://tulipgroup.com/PDFs/Serology/IFU/VITAL-WIDAL-IFU.pdf
- Astam Widal Test Insert: https://www.astamdiagno.com/wp-content/uploads/2025/07/WIDAL-TEST-INSERT.pdf
- Tube agglutination procedure review: https://link.springer.com/article/10.1186/1476-0711-10-7

## 3. Recommended modules

| Module | Candidate components | Purpose |
|---|---|---|
| Frame / enclosure | Aluminium extrusion or sheet-metal frame, opaque outer shell, transparent interlocked service door | Rigidity, light shielding, splash containment |
| Sample rack | Removable tube rack, QR/barcode reader, tube-presence sensor | Traceable sample positioning |
| Liquid handling | Stepper-driven syringe pump, precision linear axis, pipette holder, disposable tips, tip ejector, liquid-level detection | Controlled aspiration/dispensing and reduced carry-over |
| Diluent/reagent bays | Dedicated saline reservoir, separate O and H reagent holders, level/lot labels | Maintain separate reagent identities |
| Reaction rack | Numbered microtubes or a validated microplate carrier | Repeatable dilution and reaction positions |
| Mixing | Speed-controlled microplate/tube shaker or gentle motion stage, encoder feedback | Controlled protocol-specific mixing |
| Incubation | Insulated chamber, heater, circulation fan, calibrated RTD/thermistor, independent thermal fuse | Stable, logged temperature |
| Optical reader | USB macro camera or machine-vision camera, fixed lens/focus, diffuse LED, white/black reference | Standardized images and glare control |
| Motion control | ESP32-S3 or STM32 controller, stepper drivers, limit switches, motor current monitoring | Local deterministic actuator control |
| Safety | Emergency stop, door interlock, leak sensor, waste-level sensor, over-temperature cut-out, sealed waste bottle | Prevent unsafe motion, spills and exposure |
| Host / connectivity | Windows PC, Python FastAPI bridge, authenticated local Wi-Fi link | AI image capture, job record and dashboard connection |

The generated app concept shows the benchtop enclosure, a separate O/H reagent bay, central liquid-handling area, rack, optical reader and display. It is a layout reference, not a dimensioned CAD drawing.

## 4. Prototype build stages

### Stage A — optical proof of concept (recommended first)
- Keep all specimen handling manual and use pre-prepared, approved training/demo material.
- Build a sealed camera box with fixed camera, lens, diffuse LEDs, background and a repeatable rack.
- Validate repeatable capture, focus, illumination and image storage.
- Add ESP32/PC Wi-Fi telemetry only; do not actuate fluid handling yet.

### Stage B — controlled liquid-handling bench prototype
- Use non-clinical coloured water / safe surrogate liquid to validate pipette repeatability, dilution accuracy, carry-over controls and waste handling.
- Add calibrated syringe pump, disposable tips, rack positioning and sensors.
- Compare gravimetric volume checks with acceptance limits set by the engineering/ATLM team.
- Do not use patient specimens until the workflow passes bench verification and local biosafety review.

### Stage C — integrated research prototype
- Add kit-specific recipe configuration, O/H separate lanes, controlled mixing/incubation, optical capture, full audit trail and ATLM review.
- Validate with approved specimens and independent reference readings; document failures and uncertainty.
- Do not auto-release or auto-promote model predictions.

### Optional Stage D — whole-blood loading
- Only after Stage C: add a validated clotting timer and enclosed centrifuge module, tube balance check, lid lock and rotor speed feedback.
- This increases mass, vibration, maintenance and biosafety complexity. It should not be included in the first prototype.

## 5. Application and firmware boundaries

- Next.js dashboard is a monitoring, configuration and review surface.
- Windows FastAPI bridge owns a local authenticated job queue and stores local capture artifacts.
- ESP32-S3/STM32 controls motors and sensors locally; it must enforce interlocks independently of the browser.
- Web app must never directly drive motors or heaters.
- Reject jobs when the door is open, emergency stop is active, leak is detected, temperature is out of range, waste is full, or homing has not completed.
- Log device ID, firmware version, recipe version, operator, reagent lot, timestamps, temperature trace and image hashes.
- Do not upload patient identifiers or raw clinical images to a public repository.

## 6. Important limitations

Widal is a serological test with substantial clinical limitations. The CDC states that blood culture is the mainstay of diagnosis and that Widal serology is not recommended because of false positives: https://www.cdc.gov/typhoid-fever/hcp/clinical-guidance/index.html

The automated instrument and AI reader must be presented as a research/technical prototype only until independently validated and cleared under applicable local requirements. ATLM review remains mandatory; the display must not claim that an image classifier diagnoses typhoid.
