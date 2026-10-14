import json
import plistlib
from pathlib import Path

import pytest

from shortcut_forge import Shortcut, build_from_spec, lint_plist, var
from shortcut_forge.lint import summarize
from shortcut_forge.refs import tok
from shortcut_forge.templates import TEMPLATES

EX = Path(__file__).parent.parent / "examples"


def ids(sc):
    return [a["WFWorkflowActionIdentifier"].split(".")[-1] for a in sc.actions]


def errors(sc):
    return [f for f in sc.lint() if f.severity == "error"]


def test_fstring_ref_becomes_attachment():
    sc = Shortcut()
    name = sc.ask("name?")
    t = tok(f"Hi {name}!")
    assert t["Value"]["string"] == "Hi ￼!"
    (att,) = t["Value"]["attachmentsByRange"].values()
    assert att["OutputName"] == "Provided Input"


def test_utf16_offsets_with_emoji():
    t = tok("💛 {{x}}")
    assert list(t["Value"]["attachmentsByRange"]) == ["{3, 1}"]  # emoji = 2 code units + space


def test_storage_set_is_token_string():
    sc = Shortcut()
    sc.storage_set("k", var("x"))
    p = sc.actions[-1]["WFWorkflowActionParameters"]
    assert p["WFInput"]["WFSerializationType"] == "WFTextTokenString"


def test_storage_delete_is_guarded_and_lint_clean():
    sc = Shortcut()
    sc.storage_delete("k")
    assert ids(sc) == ["getstoredcontent", "conditional", "deletestoredcontent", "conditional"]
    assert not [f for f in sc.lint() if f.rule == "SF002"]


def test_health_mcg_converted_to_mg():
    sc = Shortcut()
    sc.health_log("Vitamin B12", "77.4")
    log = sc.actions[-1]["WFWorkflowActionParameters"]["WFQuantitySampleQuantity"]["Value"]
    assert log["Unit"] == "mg"
    assert "WFSerializationType" not in log["Magnitude"]  # raw ref, not a token string
    assert "math" in ids(sc)
    assert not errors(sc)


def test_text_if_wraps_left_side():
    sc = Shortcut()
    d = sc.dictionary({"a": "x"})
    v = sc.get_value(d, "a")
    with sc.if_(v, "is", "x"):
        sc.notify("ok")
    i = ids(sc).index("conditional")
    assert ids(sc)[i - 1] == "gettext"
    assert not [f for f in sc.lint() if f.rule == "SF005"]


def test_dotted_key_is_split():
    sc = Shortcut()
    d = sc.dictionary({"a": {"b": 1}})
    sc.get_value(d, "a.b")
    assert ids(sc).count("getvalueforkey") == 2


def test_reminders_complete_loops_with_guard():
    sc = Shortcut()
    r = sc.reminders_find(title_contains="x", completed=False)
    sc.reminders_complete(r)
    assert ids(sc)[1:] == ["count", "conditional", "each", "reminders", "each", "conditional"]
    assert not sc.lint() or all(f.rule != "SF007" for f in sc.lint())


def test_menu_fills_missing_cases():
    sc = Shortcut()
    with sc.menu("?", ["A", "B"]) as m:
        with m.case("A"):
            sc.notify("a")
    assert not [f for f in sc.lint() if f.rule in ("SF011", "SF000")]


def test_lint_catches_classic_mistakes():
    acts = [
        {"WFWorkflowActionIdentifier": "is.workflow.actions.setstoredcontent",
         "WFWorkflowActionParameters": {"WFStoredContentKey": "k",
                                        "WFInput": {"Value": {"Type": "Variable", "VariableName": "x"},
                                                    "WFSerializationType": "WFTextTokenAttachment"}}},
        {"WFWorkflowActionIdentifier": "is.workflow.actions.deletestoredcontent",
         "WFWorkflowActionParameters": {"WFStoredContentKey": "missing"}},
        {"WFWorkflowActionIdentifier": "is.workflow.actions.health.quantity.log",
         "WFWorkflowActionParameters": {"WFQuantitySampleType": "Vitamin D",
                                        "WFQuantitySampleQuantity": {"Value": {"Magnitude": tok("5"), "Unit": "mcg"}}}},
    ]
    rules = {f.rule for f in lint_plist({"WFWorkflowActions": acts})}
    assert {"SF001", "SF002", "SF003", "SF004", "SF010"} <= rules


@pytest.mark.parametrize("path", sorted(EX.glob("*.json")))
def test_examples_build_without_errors(path, tmp_path):
    sc = build_from_spec(json.loads(path.read_text()))
    out = tmp_path / "x.shortcut"
    sc.save(str(out))
    plistlib.loads(out.read_bytes())
    assert not errors(sc), summarize(sc.lint())


@pytest.mark.parametrize("name", list(TEMPLATES))
def test_templates_build_without_errors(name):
    mod = TEMPLATES[name]
    sc = mod.build(mod.EXAMPLE_CONFIG)
    assert len(sc.actions) > 10
    assert not errors(sc), summarize(sc.lint())


def test_supplement_template_korean_and_reminders_idempotent():
    mod = TEMPLATES["supplement-tracker"]
    cfg = dict(mod.EXAMPLE_CONFIG, lang="ko", word="영양제")
    sc = mod.build(cfg)
    titles = [a["WFWorkflowActionParameters"]["WFCalendarItemTitle"]["Value"]["string"]
              for a in sc.actions if a["WFWorkflowActionIdentifier"].endswith("addnewreminder")]
    # one creator per (user, recording slot, target slot) and each guarded by a find+count
    assert titles and all("영양제" in t for t in titles)
    assert ids(sc).count("reminders") >= len(titles)


def test_spec_error_message_is_helpful():
    from shortcut_forge.spec import SpecError
    with pytest.raises(SpecError, match="unknown step"):
        build_from_spec({"actions": [{"frobnicate": 1}]})
