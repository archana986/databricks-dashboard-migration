from types import SimpleNamespace

from helpers import deployment_package as dp


class _FakeFs:
    def __init__(self, files_by_path, head_map):
        self._files_by_path = files_by_path
        self._head_map = head_map

    def ls(self, path):
        return self._files_by_path.get(path, [])

    def head(self, path, _max_bytes):
        if path in self._head_map:
            return self._head_map[path]
        raise Exception(f"File not found: {path}")


class _FakeDbutils:
    def __init__(self, files_by_path, head_map):
        self.fs = _FakeFs(files_by_path, head_map)


def _patch_dbutils(monkeypatch, files_by_path, head_map):
    fake = _FakeDbutils(files_by_path, head_map)
    monkeypatch.setattr("helpers.dbutils_helper.get_dbutils", lambda: fake)
    return fake


def test_to_dict_serializes_subscriptions():
    package = dp.DashboardDeploymentPackage(
        dashboard_id="dash1",
        dashboard_name="Sales",
        dashboard_json={"serialized_dashboard": "{}"},
        permissions=[
            dp.PermissionDefinition(
                principal="user@example.com",
                principal_type="user",
                level="CAN_VIEW",
            )
        ],
        schedules=[
            dp.ScheduleDefinition(
                display_name="Daily",
                quartz_cron_expression="0 0 8 * * ?",
                timezone_id="UTC",
                pause_status="UNPAUSED",
                subscriptions=[
                    dp.SubscriptionDefinition(user_id=123, subject="Daily Update"),
                    dp.SubscriptionDefinition(destination_id="dest-1", subject="Webhook"),
                ],
            )
        ],
    )

    data = package.to_dict()

    assert data["permissions"][0]["principal"] == "user@example.com"
    subs = data["schedules"][0]["subscriptions"]
    assert subs[0]["user_id"] == 123
    assert subs[1]["destination_id"] == "dest-1"


def test_build_deployment_packages_happy_path(monkeypatch):
    transformed_path = "/Volumes/cat/schema/dashboard_migration/transformed"
    file_path = f"{transformed_path}/dashboard_abc123_Sales_Dash_transformed.json"
    files = {
        transformed_path: [
            SimpleNamespace(
                name="dashboard_abc123_Sales_Dash_transformed.json",
                path=file_path,
            )
        ]
    }
    head_map = {file_path: '{"display_name": "Sales Dash"}'}

    _patch_dbutils(monkeypatch, files, head_map)

    permissions_map = {
        "abc123": {
            "permissions": [
                {
                    "principal": "user@example.com",
                    "principal_type": "user",
                    "level": "CAN_VIEW",
                }
            ]
        }
    }
    schedules_map = {
        "abc123": {
            "schedules": [
                {
                    "display_name": "Daily",
                    "cron_schedule": {
                        "quartz_cron_expression": "0 0 8 * * ?",
                        "timezone_id": "UTC",
                    },
                    "pause_status": "UNPAUSED",
                    "subscriptions": [
                        {"subscriber": {"user_id": 123}, "subject": "Daily Update"}
                    ],
                }
            ]
        }
    }

    packages = dp.build_deployment_packages(
        transformed_path,
        permissions_map=permissions_map,
        schedules_map=schedules_map,
    )

    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.dashboard_id == "abc123"
    assert pkg.dashboard_name == "Sales_Dash"
    assert pkg.permissions[0].principal == "user@example.com"
    assert pkg.schedules[0].subscriptions[0].user_id == 123
    assert pkg.dashboard_json["serialized_dashboard"] == head_map[file_path]


def test_build_deployment_packages_fallback_to_json(monkeypatch):
    transformed_path = "/Volumes/cat/schema/dashboard_migration/transformed"
    file_path = f"{transformed_path}/dashboard_idonly.json"
    files = {
        transformed_path: [
            SimpleNamespace(
                name="dashboard_idonly.json",
                path=file_path,
            )
        ]
    }
    head_map = {
        file_path: '{"dashboard_id": "id123", "display_name": "Revenue"}'
    }

    _patch_dbutils(monkeypatch, files, head_map)

    packages = dp.build_deployment_packages(transformed_path)

    assert len(packages) == 1
    pkg = packages[0]
    assert pkg.dashboard_id == "id123"
    assert pkg.dashboard_name == "Revenue"
