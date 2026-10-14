# iOS 26/27 features shortcut-forge uses

Status legend: **verified** = ran on an iPhone (iOS 27.0, Oct 2026); **modelled** = emitted in the documented
plist shape but not yet confirmed by a device run (reports welcome).

| Feature | Action identifier | Status | Notes |
|---|---|---|---|
| Stored Content (get/set/delete) | `getstoredcontent`, `setstoredcontent`, `deletestoredcontent` | verified | Per-shortcut key/value storage. Values must be text tokens. Replaces iCloud-JSON hacks. `WFStoredContentGlobalValue=true` shares across shortcuts. |
| Use Model | `askllm` | verified | `WFLLMModel`: "Apple Intelligence" (on-device / Private Cloud Compute). Needs Apple Intelligence enabled. |
| Find / set Reminders | `filter.reminders`, `setters.reminders` | verified | Content predicate filters on Title / Is Completed. |
| Add New Reminder with alert | `addnewreminder` | verified | `WFAlertCondition="At Time"`, `WFAlertCustomTime` as text. |
| Log Health Sample | `health.quantity.log` | verified (nutrients) | Dietary nutrient types verified. Water / body metrics are modelled. |
| Choose from List / Menu / If / Repeat | core | verified | |

Minimum client version written to the file is 900 (the app upgrades it on import).
Signing requires macOS 12+ with `shortcuts` CLI; tested on macOS 27.0.1.
