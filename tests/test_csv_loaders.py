import pytest

pytest.importorskip("pandas")

from helpers import deployment_package as dp


class _FakeFs:
    def __init__(self, head_map):
        self._head_map = head_map

    def head(self, path, _max_bytes):
        if path in self._head_map:
            return self._head_map[path]
        raise Exception(f"File not found: {path}")


class _FakeDbutils:
    def __init__(self, head_map):
        self.fs = _FakeFs(head_map)


def _patch_dbutils(monkeypatch, head_map):
    fake = _FakeDbutils(head_map)
    monkeypatch.setattr("helpers.dbutils_helper.get_dbutils", lambda: fake)
    return fake


def test_load_permissions_from_csv_parses_rows(monkeypatch):
    export_path = "/Volumes/vol/exported"
    csv_content = (
        "dashboard_id,dashboard_name,principal,principal_type,permission_level\n"
        "dash1,Sales,user@example.com,user,CAN_VIEW\n"
        "dash1,Sales,group-1,group,CAN_MANAGE\n"
    )
    head_map = {f"{export_path}/all_permissions.csv": csv_content}

    _patch_dbutils(monkeypatch, head_map)

    permissions = dp.load_permissions_from_csv(export_path)

    assert "dash1" in permissions
    assert len(permissions["dash1"]["permissions"]) == 2
    assert permissions["dash1"]["permissions"][0]["principal"] == "user@example.com"


def test_load_permissions_from_csv_missing_raises(monkeypatch):
    export_path = "/Volumes/vol/exported"
    head_map = {}

    _patch_dbutils(monkeypatch, head_map)

    with pytest.raises(FileNotFoundError) as excinfo:
        dp.load_permissions_from_csv(export_path)

    assert "all_permissions.csv not found" in str(excinfo.value)


def test_load_schedules_from_csv_parses_subscriptions(monkeypatch):
    export_path = "/Volumes/vol/exported"
    csv_content = (
        "dashboard_id,schedule_id,cron_expression,timezone,paused,subscriptions_json\n"
        "dash1,schedule-12345,0 0 8 * * ?,UTC,0,"
        "\"[{\"\"subscriber\"\": {\"\"user_id\"\": 123}, \"\"subject\"\": \"\"Daily\"\"}]\"\n"
    )
    head_map = {f"{export_path}/all_schedules.csv": csv_content}

    _patch_dbutils(monkeypatch, head_map)

    schedules = dp.load_schedules_from_csv(export_path)

    assert "dash1" in schedules
    sched_list = schedules["dash1"]["schedules"]
    assert len(sched_list) == 1
    assert sched_list[0]["display_name"] == "Schedule_schedule"
    assert sched_list[0]["pause_status"] == "UNPAUSED"
    assert sched_list[0]["subscriptions"][0]["subscriber"]["user_id"] == 123
