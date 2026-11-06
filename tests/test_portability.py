import importlib.util
from pathlib import Path

from nj_switch.direct_browser import chrome_executable
from nj_switch.registry import PROJECT_ROOT, REGISTRY, load_registry


def load_catalog_tool():
    path = PROJECT_ROOT / "tools/build_current_offer_catalog.py"
    spec = importlib.util.spec_from_file_location("build_current_offer_catalog", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_project_resources_do_not_depend_on_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    assert PROJECT_ROOT == Path(__file__).resolve().parents[1]
    assert REGISTRY.is_file()
    assert len(load_registry()) == 84


def test_catalog_defaults_are_anchored_to_project_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    catalog = load_catalog_tool()

    assert catalog.DEFAULT_RUNS == PROJECT_ROOT / "data/runs"
    assert catalog.REGISTRY == PROJECT_ROOT / "src/TPSCompilation/master_third_party_supplier_list.csv"


def test_chrome_override_accepts_a_nonstandard_install(monkeypatch, tmp_path):
    executable = tmp_path / "custom chrome.exe"
    executable.touch()
    monkeypatch.setenv("NJ_SWITCH_CHROME", str(executable))

    assert chrome_executable() == executable.resolve()


def test_python_sources_do_not_contain_developer_home_path():
    developer_home = "C:" + "\\Users\\" + "brian"
    source_files = [
        *PROJECT_ROOT.glob("src/**/*.py"),
        *PROJECT_ROOT.glob("tools/**/*.py"),
    ]

    offenders = [
        path.relative_to(PROJECT_ROOT)
        for path in source_files
        if developer_home.casefold() in path.read_text(encoding="utf-8").casefold()
    ]
    assert offenders == []
