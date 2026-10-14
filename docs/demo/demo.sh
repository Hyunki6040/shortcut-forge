#!/bin/zsh
# Reproducible terminal demo used for docs/assets/demo.gif (run from the repo root on a Mac).
printf '\e[8;26;104t'; clear
type_() { local s="$1"; for ((i=1;i<=${#s};i++)); do printf '%s' "${s[i]}"; sleep 0.025; done; echo; }
say() { printf '\e[38;5;245m'; type_ "# $1"; printf '\e[0m'; sleep 0.6; }
run() { printf '\e[38;5;75m$\e[0m '; type_ "$1"; eval "$1"; sleep 1.6; }
mkdir -p out; D=out
shortcut-forge() { uv run --quiet shortcut-forge "$@"; }

say 'You → Claude/Codex: "block 50 minutes on my calendar for deep work, as an iPhone shortcut"'
say 'The MCP tool writes a JSON spec. Same thing from the CLI:'
run "shortcut-forge build library/focus-block/shortcut.json -o 'out/Focus Block.unsigned.shortcut' --sign"
say 'Signed (AEA1) → AirDrop / iCloud Drive → tap on iPhone. Now a plist a generic LLM wrote:'
python3 - out/llm.unsigned.shortcut <<'PY'
import plistlib, sys
A = lambda i, **p: {"WFWorkflowActionIdentifier": "is.workflow.actions." + i, "WFWorkflowActionParameters": p}
att = {"Value": {"Type": "Variable", "VariableName": "dose"}, "WFSerializationType": "WFTextTokenAttachment"}
acts = [A("setvariable", WFVariableName="dose", WFInput=att),
        A("setstoredcontent", WFStoredContentKey="log", WFInput=att),
        A("health.quantity.log", WFQuantitySampleType="Vitamin B12",
          WFQuantitySampleQuantity={"Value": {"Magnitude": "77.4", "Unit": "mcg"}}),
        A("deletestoredcontent", WFStoredContentKey="yesterday")]
plistlib.dump({"WFWorkflowActions": acts}, open(sys.argv[1], "wb"))
PY
run "shortcut-forge lint 'out/llm.unsigned.shortcut' | grep -E '\"(rule|symptom)\"' | head -8"
say 'It would have imported fine and failed on the phone. Ours opens straight in Shortcuts:'
run "open -a Shortcuts 'out/Focus Block.shortcut'"
sleep 6
