import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

os.environ.setdefault("H3_ROOT", str(Path(tempfile.gettempdir()) / "minimax-h3-desktop-tests"))

import app.main as main_module
from app.engine import ComfyUIH3Engine, FakeEngine
from app.jobs import JobStore
from app.local_state import LocalStateStore
from app.peering import normalize_peer_url
from app.settings import Settings


class DesktopContractTests(TestCase):
    def test_ai_key_is_stored_in_sqlite_and_never_returned(self):
        with TemporaryDirectory() as temp:
            database = Path(temp) / "config.db"
            store = LocalStateStore(database)
            result = store.update_ai_config(
                enabled=True,
                base_url="https://api.example.com/v1",
                model="model-a",
                api_key="secret-key",
            )
            self.assertTrue(result["has_api_key"])
            self.assertNotIn("api_key", result)
            self.assertNotIn("api_key", store.ai_config())
            with sqlite3.connect(database) as connection:
                row = connection.execute(
                    "SELECT value FROM desktop_settings WHERE key = 'ai_api_key'"
                ).fetchone()
            self.assertEqual(row[0], "secret-key")

    def test_pairing_code_accepts_current_and_previous_period_only(self):
        with TemporaryDirectory() as temp:
            store = LocalStateStore(Path(temp) / "config.db")
            timestamp = 1_700_000_000.0
            current = store.pairing_code(timestamp)
            previous = store.pairing_code(timestamp - 30)
            future = store.pairing_code(timestamp + 30)
            self.assertTrue(store.verify_pairing_code(current, timestamp))
            self.assertTrue(store.verify_pairing_code(previous, timestamp))
            self.assertFalse(store.verify_pairing_code(future, timestamp))

    def test_peer_tokens_persist_and_revoke(self):
        with TemporaryDirectory() as temp:
            database = Path(temp) / "config.db"
            store = LocalStateStore(database)
            peer = store.upsert_peer(
                device_id="peer-device-1",
                name="Other device",
                base_url="http://192.168.1.20:38193",
                access_token="outbound-token",
                inbound_token="inbound-token",
            )
            self.assertEqual(peer["name"], "Other device")
            reopened = LocalStateStore(database)
            authenticated = reopened.authenticate_peer("inbound-token")
            self.assertEqual(authenticated["device_id"], "peer-device-1")
            self.assertNotIn("access_token", authenticated)
            self.assertNotIn("inbound_token_hash", authenticated)
            self.assertTrue(reopened.delete_peer("peer-device-1"))
            self.assertIsNone(reopened.authenticate_peer("inbound-token"))

    def test_peer_url_allows_private_and_tailscale_addresses(self):
        def resolve(host, port, **_):
            return [(2, 1, 6, "", (host, port))]

        with patch("app.peering.socket.getaddrinfo", side_effect=resolve):
            self.assertEqual(
                normalize_peer_url("http://192.168.1.20:38193/"),
                "http://192.168.1.20:38193",
            )
            self.assertEqual(
                normalize_peer_url("http://100.77.224.102:38193"),
                "http://100.77.224.102:38193",
            )
            with self.assertRaisesRegex(ValueError, "局域网"):
                normalize_peer_url("http://8.8.8.8:38193")

    def test_zero_reference_comfy_upload_does_not_call_remote_upload(self):
        with TemporaryDirectory() as temp:
            settings = Settings(root=Path(temp))
            engine = ComfyUIH3Engine(settings)
            client = MagicMock()
            result = engine._upload_inputs(
                client,
                {"id": "zero", "input_paths": [], "request": {"references": []}},
            )
            self.assertEqual(result, [])
            client.post.assert_not_called()

    def test_zero_reference_tts_runs_in_fake_engine(self):
        with TemporaryDirectory() as temp:
            settings = Settings(root=Path(temp))
            settings.ensure_directories()
            engine = FakeEngine(settings)
            output = engine.generate(
                {
                    "id": "zero-tts",
                    "input_paths": [],
                    "request": {"model_variant": "ref2va-fp8", "execution_mode": "tts"},
                },
                lambda *_: None,
                lambda: False,
            )
            self.assertEqual(output.suffix, ".wav")
            self.assertGreater(output.stat().st_size, 0)

    def test_general_settings_and_remote_record_protection(self):
        with TemporaryDirectory() as temp:
            store = LocalStateStore(Path(temp) / "config.db")
            settings = store.general_settings()
            self.assertTrue(settings["show_runtime_logs"])
            self.assertTrue(settings["show_peering"])
            self.assertFalse(settings["backup_outputs"])
            self.assertEqual(settings["remote_disconnect_policy"], "encrypt")
            store.put_remote_record(
                record_id="record-1",
                peer_device_id="peer-1",
                record_type="job",
                value={"id": "job-1"},
                encrypted=False,
            )
            store.protect_remote_records("peer-1")
            with sqlite3.connect(Path(temp) / "config.db") as connection:
                encrypted = connection.execute(
                    "SELECT encrypted FROM remote_records WHERE record_id = 'record-1'"
                ).fetchone()[0]
            self.assertEqual(encrypted, 1)
            self.assertEqual(store.consume_remote_records("peer-1"), [{"id": "job-1"}])

    def test_remote_records_key_accepts_unicode_and_requires_eight_characters(self):
        with TemporaryDirectory() as temp:
            store = LocalStateStore(Path(temp) / "config.db")
            valid_key = "密钥一二三四五六"
            store.update_general_settings(remote_records_key=valid_key)
            self.assertEqual(store.general_settings()["remote_records_key"], valid_key)
            with self.assertRaisesRegex(ValueError, "8 至 256"):
                store.update_general_settings(remote_records_key="1234567")
            with self.assertRaisesRegex(ValueError, "8 至 256"):
                store.update_general_settings(remote_records_key="x" * 257)

    def test_peer_key_encrypts_unlocks_and_invalidates_on_key_update(self):
        with TemporaryDirectory() as temp:
            store = LocalStateStore(Path(temp) / "config.db")
            peer_id = "peer-device-key-test"
            first_key = "第一组远程密钥123"
            second_key = "第二组远程密钥456"
            encrypted, nonce = store.encrypt_peer_bytes(b"protected", peer_id, first_key)
            self.assertEqual(
                store.decrypt_peer_bytes(encrypted, nonce, peer_id, first_key),
                b"protected",
            )
            with self.assertRaises(Exception):
                store.decrypt_peer_bytes(encrypted, nonce, peer_id, second_key)
            first_id = store.records_key_id(first_key)
            store.cache_unlocked_peer_key(peer_id, first_id, first_key)
            self.assertEqual(store.unlocked_peer_key(peer_id, first_id), first_key)
            store.upsert_peer(
                device_id=peer_id,
                name="Peer",
                base_url="http://192.168.1.20:38193",
                access_token="outbound-token",
                inbound_token="inbound-token",
                records_key=second_key,
            )
            self.assertIsNone(store.unlocked_peer_key(peer_id, first_id))

    def test_remote_records_delete_policy_and_asset_marker(self):
        with TemporaryDirectory() as temp:
            database = Path(temp) / "config.db"
            store = LocalStateStore(database)
            store.update_general_settings(
                remote_disconnect_policy="delete",
                remote_records_key=store.general_settings()["remote_records_key"],
            )
            store.put_remote_record(
                record_id="record-2",
                peer_device_id="peer-2",
                record_type="job",
                value={"id": "job-2"},
                encrypted=False,
            )
            store.protect_remote_records("peer-2")
            self.assertEqual(store.consume_remote_records("peer-2"), [])

    def test_peer_job_files_are_encrypted_and_restored(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            jobs_dir = root / "jobs"
            uploads_dir = root / "uploads" / "peer-job"
            outputs_dir = root / "outputs"
            jobs_dir.mkdir()
            uploads_dir.mkdir(parents=True)
            outputs_dir.mkdir()
            input_path = uploads_dir / "reference.png"
            result_path = outputs_dir / "peer-job.mp4"
            input_path.write_bytes(b"reference-data")
            result_path.write_bytes(b"result-data")
            store = JobStore(jobs_dir)
            store.create(
                {
                    "id": "peer-job",
                    "title": "Peer job",
                    "status": "completed",
                    "stage": "生成完成",
                    "progress": 100,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:00:00+00:00",
                    "request": {"proxy_source_device_id": "peer-1"},
                    "input_paths": [str(input_path)],
                    "result_path": str(result_path),
                }
            )
            encrypted = lambda value: (value, b"0123456789ab")
            snapshots = store.protect_peer_jobs(
                "peer-1", delete=False, encrypt_bytes=encrypted
            )
            self.assertEqual(len(snapshots), 1)
            self.assertFalse(input_path.exists())
            self.assertFalse(result_path.exists())
            self.assertTrue(Path(str(input_path) + ".h3enc").exists())
            self.assertTrue(Path(str(result_path) + ".h3enc").exists())
            self.assertIsNone(store.get("peer-job"))

            def decrypt(value, nonce):
                self.assertEqual(nonce, b"0123456789ab")
                return value

            restored = store.restore_protected_job(snapshots[0], decrypt)
            self.assertEqual(restored["id"], "peer-job")
            self.assertEqual(input_path.read_bytes(), b"reference-data")
            self.assertEqual(result_path.read_bytes(), b"result-data")
            self.assertFalse(Path(str(input_path) + ".h3enc").exists())
            self.assertFalse(Path(str(result_path) + ".h3enc").exists())

    def test_protected_local_assets_unlock_delete_and_restore(self):
        async def run_test(temp: str):
            root = Path(temp)
            data_dir = root / "data"
            jobs_dir = data_dir / "jobs"
            upload_dir = data_dir / "uploads" / "peer-job"
            output_dir = data_dir / "outputs"
            jobs_dir.mkdir(parents=True)
            upload_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            input_path = upload_dir / "reference.png"
            result_path = output_dir / "peer-job.mp4"
            input_path.write_bytes(b"reference-data")
            result_path.write_bytes(b"result-data")

            jobs = JobStore(jobs_dir)
            peer_state = LocalStateStore(data_dir / "config.db")
            peer_id = "peer-device-protected"
            records_key = "对方设备密钥1234"
            peer_state.upsert_peer(
                device_id=peer_id,
                name="编辑设备",
                base_url="http://192.168.1.20:38193",
                access_token="outbound-token",
                inbound_token="inbound-token",
                records_key=records_key,
            )
            jobs.create(
                {
                    "id": "peer-job",
                    "title": "Remote video",
                    "status": "completed",
                    "stage": "生成完成",
                    "progress": 100,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:00:00+00:00",
                    "request": {
                        "proxy_source_device_id": peer_id,
                        "media_type": "video",
                    },
                    "input_paths": [str(input_path)],
                    "result_path": str(result_path),
                }
            )
            route_settings = SimpleNamespace(
                api_key="",
                desktop_mode=False,
                data_dir=data_dir,
            )
            transport = httpx.ASGITransport(app=main_module.app)
            with (
                patch.object(main_module, "store", jobs),
                patch.object(main_module, "local_state", peer_state),
                patch.object(main_module, "settings", route_settings),
            ):
                await main_module.protect_peer_state(peer_id)
                self.assertFalse(input_path.exists())
                self.assertFalse(result_path.exists())
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    listed = await client.get("/api/v1/assets/local?page=1&page_size=10")
                    self.assertEqual(listed.status_code, 200)
                    asset = listed.json()["data"][0]
                    self.assertTrue(asset["encrypted"])
                    self.assertTrue(asset["locked"])
                    self.assertEqual(asset["owner_name"], "编辑设备")

                    wrong = await client.post(
                        "/api/v1/assets/local/unlock",
                        json={"owner_device_id": peer_id, "records_key": "错误设备密钥1234"},
                    )
                    self.assertEqual(wrong.status_code, 422)
                    unlocked = await client.post(
                        "/api/v1/assets/local/unlock",
                        json={"owner_device_id": peer_id, "records_key": records_key},
                    )
                    self.assertEqual(unlocked.status_code, 200)
                    preview = await client.get(
                        f"/api/v1/assets/local/protected/{peer_id}/peer-job/result"
                    )
                    self.assertEqual(preview.status_code, 200)
                    self.assertEqual(preview.content, b"result-data")

                    deleted = await client.post(
                        "/api/v1/assets/local/delete",
                        json={"asset_ids": [f"protected::{peer_id}::peer-job"]},
                    )
                    self.assertEqual(deleted.status_code, 200)
                    self.assertEqual(deleted.json()["deleted"], [f"protected::{peer_id}::peer-job"])
                    missing = await client.get(
                        f"/api/v1/assets/local/protected/{peer_id}/peer-job/result"
                    )
                    self.assertEqual(missing.status_code, 410)
                    listed_after_delete = await client.get(
                        "/api/v1/assets/local?page=1&page_size=10"
                    )
                    self.assertEqual(listed_after_delete.status_code, 200)
                    self.assertEqual(listed_after_delete.json()["data"], [])
                    self.assertEqual(listed_after_delete.json()["total"], 0)

                main_module.restore_peer_records(peer_id, records_key)
                restored = jobs.get("peer-job")
                self.assertTrue(restored["asset_deleted"])
                self.assertIsNone(restored["result_path"])
                self.assertEqual(input_path.read_bytes(), b"reference-data")
                self.assertFalse(result_path.exists())

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))

    def test_deleted_or_missing_artifacts_are_hidden_from_local_asset_manager(self):
        async def run_test(temp: str):
            root = Path(temp)
            data_dir = root / "data"
            jobs_dir = data_dir / "jobs"
            output_dir = data_dir / "outputs"
            jobs_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            available_path = output_dir / "available.mp4"
            available_path.write_bytes(b"video")

            jobs = JobStore(jobs_dir)
            base_job = {
                "status": "completed",
                "stage": "生成完成",
                "progress": 100,
                "created_at": "2026-08-19T00:00:00+00:00",
                "updated_at": "2026-08-19T00:00:00+00:00",
                "request": {"media_type": "video"},
                "input_paths": [],
            }
            jobs.create(
                {
                    **base_job,
                    "id": "available",
                    "title": "Available video",
                    "result_path": str(available_path),
                }
            )
            jobs.create(
                {
                    **base_job,
                    "id": "deleted",
                    "title": "Deleted video",
                    "result_path": None,
                    "asset_deleted": True,
                }
            )
            jobs.create(
                {
                    **base_job,
                    "id": "missing",
                    "title": "Missing video",
                    "result_path": str(output_dir / "missing.mp4"),
                }
            )
            local_state = LocalStateStore(data_dir / "config.db")
            route_settings = SimpleNamespace(
                api_key="",
                desktop_mode=False,
                data_dir=data_dir,
            )
            transport = httpx.ASGITransport(app=main_module.app)
            with (
                patch.object(main_module, "store", jobs),
                patch.object(main_module, "local_state", local_state),
                patch.object(main_module, "settings", route_settings),
            ):
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    listed = await client.get(
                        "/api/v1/assets/local?page=1&page_size=10"
                    )
                    self.assertEqual(listed.status_code, 200)
                    self.assertEqual(listed.json()["total"], 1)
                    self.assertEqual(
                        [item["job_id"] for item in listed.json()["data"]],
                        ["available"],
                    )

                    deleted = await client.post(
                        "/api/v1/assets/local/delete",
                        json={"asset_ids": ["job::available"]},
                    )
                    self.assertEqual(deleted.status_code, 200)
                    self.assertEqual(deleted.json()["deleted"], ["job::available"])
                    listed_after_delete = await client.get(
                        "/api/v1/assets/local?page=1&page_size=10"
                    )
                    self.assertEqual(listed_after_delete.json()["data"], [])
                    self.assertEqual(listed_after_delete.json()["total"], 0)
                    self.assertTrue(jobs.get("available")["asset_deleted"])

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))

    def test_settings_and_local_asset_frontend_contract(self):
        root = Path(__file__).resolve().parents[1]
        index = (root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (root / "static" / "app.js").read_text(encoding="utf-8")
        main = (root / "app" / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("fonts.googleapis.com", index)
        self.assertNotIn("总设置", index)
        self.assertIn('id="globalSettingsTitle">设置</h2>', index)
        self.assertIn('id="toggleRemoteRecordsKey"', index)
        self.assertIn('minlength="8" maxlength="256"', index)
        self.assertIn('id="localAssetsSelectAll"', index)
        self.assertIn('class="local-assets-grid"', index)
        self.assertIn('id="unlockAssetsModal"', index)
        self.assertIn('id="conversationFilterToggle"', index)
        self.assertIn('id="conversationFilterPanel"', index)
        self.assertIn('/api/v1/assets/local?page=', app_js)
        self.assertIn('/api/v1/assets/local/unlock', app_js)
        self.assertIn('data-unlock-owner', app_js)
        self.assertIn('data-local-asset-id', app_js)
        self.assertIn('id="localAssetPreviewModal"', index)
        self.assertIn('id="localAssetPreviewBody"', index)
        self.assertIn('function openLocalAssetPreview(asset)', app_js)
        self.assertIn('function closeLocalAssetPreview()', app_js)
        self.assertIn('<video src="${url}" controls playsinline autoplay preload="metadata"', app_js)
        self.assertIn('<audio src="${url}" controls autoplay preload="metadata"', app_js)
        self.assertNotIn('function openLocalAssetDetail(asset)', app_js)
        self.assertIn('conversationRevisionSignature', app_js)
        self.assertIn('conversationDeviceIds: new Set()', app_js)
        self.assertIn('function conversationMatchesCurrentView(job)', app_js)
        self.assertIn('|devices:${deviceFilterSignature}', app_js)
        self.assertIn('if (!el("showRuntimeLogs").checked) closeOpsWindow();', app_js)
        self.assertIn('opsPositionInitialized: false', app_js)
        self.assertNotIn('if (el("showRuntimeLogs").checked) openOpsWindow();', app_js)
        self.assertIn('localAssetsList").addEventListener("scroll"', app_js)
        self.assertIn('window.confirm(`确认删除选中的', app_js)
        self.assertIn('/api/v1/peering/export/events', main)
        self.assertIn('payload["nodes"] = exported_proxy_nodes()', main)
        self.assertIn('addEventListener("peer_snapshot"', app_js)
        self.assertIn('renderCombinedRuntime()', app_js)
        self.assertNotIn('await Promise.all([refreshSharedRuntime(), refreshConversation(), refreshProxyJobs()])', app_js)

    def test_desktop_packaging_contract(self):
        root = Path(__file__).resolve().parents[1]
        desktop = (root / "desktop.py").read_text(encoding="utf-8")
        builder = (root / "scripts" / "build_desktop.py").read_text(encoding="utf-8")
        requirements = (root / "requirements-desktop.txt").read_text(encoding="utf-8")
        self.assertIn("pywebview", requirements)
        self.assertIn("pyinstaller", requirements.lower())
        self.assertIn("H3_DEFAULT_COMFY_URL", desktop)
        self.assertIn("Application Support", desktop)
        self.assertIn("LOCALAPPDATA", desktop)
        self.assertIn("from app.main import app as api_app", desktop)
        self.assertNotIn("app_dir=", desktop)
        self.assertIn("--onedir", builder)
        self.assertIn("--add-data", builder)
        self.assertIn("h3-studio.icns", builder)
        self.assertIn("h3-studio.ico", builder)
        self.assertIn("hdiutil", builder)
        self.assertIn("/Applications", builder)
        self.assertIn("--exclude-module=torch", builder)

    def test_ai_key_frontend_uses_database_api(self):
        root = Path(__file__).resolve().parents[1]
        app_js = (root / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('/api/v1/settings/ai', app_js)
        self.assertNotIn("h3-ai-api-key", app_js)
        self.assertNotIn("sessionStorage", app_js)
        self.assertIn('node.owner_name ? ` · ${escapeHtml(t("owner"))}', app_js)
        self.assertIn('node.remote_proxy', app_js)
        self.assertIn('managed_remote: true', app_js)

    def test_proxy_result_backup_uses_remote_media_extension(self):
        class RemoteResponse:
            content = b"video-data"
            headers = {
                "content-type": "video/mp4",
                "content-disposition": 'attachment; filename="generated-video.mp4"',
            }

            @staticmethod
            def raise_for_status():
                return None

        class RemoteClient:
            def __init__(self, *_, **__):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            async def get(self, *_args, **_kwargs):
                return RemoteResponse()

        async def run_test(temp: str):
            root = Path(temp)
            (root / "jobs").mkdir()
            jobs = JobStore(root / "jobs")
            jobs.create(
                {
                    "id": "proxy-video",
                    "title": "Proxy video",
                    "status": "completed",
                    "stage": "生成完成",
                    "progress": 100,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:00:00+00:00",
                    "request": {"remote_proxy": True, "media_type": "video"},
                    "input_paths": [],
                    "proxy_peer_id": "peer-1",
                    "proxy_remote_job_id": "remote-1",
                }
            )
            peer_state = MagicMock()
            peer_state.peer.return_value = {
                "base_url": "http://192.168.1.20:38193",
                "access_token": "token",
            }
            peer_state.backup_outputs_enabled.return_value = True
            route_settings = SimpleNamespace(
                api_key="",
                desktop_mode=False,
                outputs_dir=root / "outputs",
            )
            transport = httpx.ASGITransport(app=main_module.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with (
                    patch.object(main_module, "store", jobs),
                    patch.object(main_module, "local_state", peer_state),
                    patch.object(main_module, "settings", route_settings),
                    patch.object(main_module.httpx, "AsyncClient", RemoteClient),
                ):
                    response = await client.get("/api/v1/generations/proxy-video/result")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "video/mp4")
            self.assertEqual(response.content, b"video-data")
            saved = jobs.get("proxy-video")
            self.assertTrue(str(saved["result_path"]).endswith("proxy-video.mp4"))
            self.assertEqual(Path(saved["result_path"]).read_bytes(), b"video-data")

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))

    def test_proxy_status_sync_updates_remote_node_owner(self):
        async def run_test(temp: str):
            root = Path(temp)
            (root / "jobs").mkdir()
            jobs = JobStore(root / "jobs")
            jobs.create(
                {
                    "id": "proxy-sync",
                    "title": "Proxy sync",
                    "status": "running",
                    "stage": "远程执行中",
                    "progress": 50,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:00:00+00:00",
                    "request": {
                        "remote_proxy": True,
                        "proxy_node_name": "Shared node",
                    },
                    "input_paths": [],
                    "proxy_peer_id": "peer-1",
                    "proxy_remote_job_id": "remote-1",
                }
            )
            peer_state = MagicMock()
            peer_state.peer.return_value = {
                "device_id": "peer-1",
                "name": "Peer device",
                "base_url": "http://192.168.1.20:38193",
                "access_token": "token",
            }
            remote = {
                "status": "completed",
                "stage": "生成完成",
                "progress": 100,
                "completed_at": "2026-08-19T00:01:00+00:00",
                "result_url": "/api/v1/generations/remote-1/result",
            }
            with (
                patch.object(main_module, "store", jobs),
                patch.object(main_module, "local_state", peer_state),
                patch.object(main_module, "peer_json", AsyncMock(return_value=remote)),
            ):
                synced = await main_module.sync_proxy_generation("proxy-sync")
            self.assertEqual(synced["status"], "completed")
            self.assertEqual(synced["assigned_node"]["name"], "Shared node")
            self.assertEqual(synced["assigned_node"]["owner_name"], "Peer device")
            self.assertEqual(synced["result_url"], "/api/v1/generations/proxy-sync/result")

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))

    def test_proxy_echo_is_filtered_from_shared_conversations_and_events(self):
        async def run_test(temp: str):
            root = Path(temp)
            (root / "jobs").mkdir()
            jobs = JobStore(root / "jobs")
            jobs.create(
                {
                    "id": "remote-actual",
                    "title": "Remote execution",
                    "status": "completed",
                    "stage": "生成完成",
                    "progress": 100,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:01:00+00:00",
                    "request": {
                        "proxy_source_device_id": "peer-1",
                        "media_type": "video",
                    },
                    "input_paths": [],
                }
            )
            proxy_echo = {
                "id": "proxy-local",
                "title": "Remote execution",
                "status": "completed",
                "created_at": "2026-08-19T00:00:00+00:00",
                "updated_at": "2026-08-19T00:01:00+00:00",
                "request": {
                    "remote_proxy": True,
                    "proxy_remote_job_id": "remote-actual",
                },
                "proxy_remote_job_id": "remote-actual",
            }
            peer = {
                "device_id": "peer-1",
                "name": "Request device",
                "base_url": "http://192.168.1.20:38193",
                "access_token": "token",
            }
            peer_state = MagicMock()
            peer_state.device_id = "executor-device"
            peer_state.machine_name = "Executor device"
            peer_state.peers.return_value = [peer]
            payload = {
                "data": [proxy_echo],
                "store_revision": 4,
            }
            with (
                patch.object(main_module, "store", jobs),
                patch.object(main_module, "local_state", peer_state),
                patch.object(main_module, "peer_json", AsyncMock(return_value=payload)),
            ):
                conversations = await main_module.list_shared_conversations(
                    page=1,
                    page_size=20,
                    status_filter=None,
                    query=None,
                    device_ids=None,
                )
                snapshot = main_module.decorate_peer_event_snapshot(
                    {
                        "revision": "4:1",
                        "store_revision": 4,
                        "jobs": [proxy_echo],
                        "queue": [proxy_echo],
                        "logs": [
                            {
                                "job_id": "proxy-local",
                                "timestamp": "2026-08-19T00:01:00+00:00",
                                "message": "生成完成",
                            }
                        ],
                        "deleted_job_ids": [],
                    },
                    peer,
                )
            self.assertEqual([item["id"] for item in conversations["data"]], ["remote-actual"])
            self.assertEqual(conversations["total"], 1)
            self.assertEqual(snapshot["jobs"], [])
            self.assertEqual(snapshot["queue"], [])
            self.assertEqual(snapshot["logs"], [])

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))

    def test_peer_proxy_delete_requires_owner_and_removes_remote_files(self):
        async def run_test(temp: str):
            root = Path(temp)
            data_dir = root / "data"
            jobs_dir = data_dir / "jobs"
            output_dir = data_dir / "outputs"
            jobs_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            result_path = output_dir / "remote-actual.mp4"
            result_path.write_bytes(b"video-data")
            jobs = JobStore(jobs_dir)
            jobs.create(
                {
                    "id": "remote-actual",
                    "title": "Remote execution",
                    "status": "completed",
                    "stage": "生成完成",
                    "progress": 100,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:01:00+00:00",
                    "request": {"proxy_source_device_id": "peer-owner"},
                    "input_paths": [],
                    "result_path": str(result_path),
                }
            )
            peer_state = LocalStateStore(data_dir / "config.db")
            peer_state.update_desktop_settings(sharing_enabled=True)
            peer_state.upsert_peer(
                device_id="peer-owner",
                name="Owner device",
                base_url="http://192.168.1.20:38193",
                access_token="owner-outbound",
                inbound_token="owner-inbound",
            )
            peer_state.upsert_peer(
                device_id="peer-other",
                name="Other device",
                base_url="http://192.168.1.21:38193",
                access_token="other-outbound",
                inbound_token="other-inbound",
            )
            manager = MagicMock()
            transport = httpx.ASGITransport(app=main_module.app)
            with (
                patch.object(main_module, "store", jobs),
                patch.object(main_module, "local_state", peer_state),
                patch.object(main_module, "manager", manager),
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    forbidden = await client.delete(
                        "/api/v1/peering/proxy/generations/remote-actual",
                        headers={"Authorization": "Bearer other-inbound"},
                    )
                    self.assertEqual(forbidden.status_code, 403)
                    deleted = await client.delete(
                        "/api/v1/peering/proxy/generations/remote-actual",
                        headers={"Authorization": "Bearer owner-inbound"},
                    )
            self.assertEqual(deleted.status_code, 200)
            self.assertIsNone(jobs.get("remote-actual"))
            self.assertFalse(result_path.exists())
            manager.remove.assert_called_once_with("remote-actual")

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))

    def test_local_proxy_delete_removes_remote_and_local_records(self):
        class RemoteResponse:
            status_code = 200
            text = '{"status":"deleted"}'

            @staticmethod
            def json():
                return {"status": "deleted"}

        class RemoteClient:
            def __init__(self, *_, **__):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return None

            async def delete(self, path):
                self.path = path
                return RemoteResponse()

        async def run_test(temp: str):
            root = Path(temp)
            jobs_dir = root / "jobs"
            output_dir = root / "outputs"
            jobs_dir.mkdir()
            output_dir.mkdir()
            backup_path = output_dir / "proxy-local.mp4"
            backup_path.write_bytes(b"backup")
            jobs = JobStore(jobs_dir)
            jobs.create(
                {
                    "id": "proxy-local",
                    "title": "Remote execution",
                    "status": "completed",
                    "stage": "生成完成",
                    "progress": 100,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "updated_at": "2026-08-19T00:01:00+00:00",
                    "request": {"remote_proxy": True},
                    "input_paths": [],
                    "result_path": str(backup_path),
                    "proxy_peer_id": "peer-1",
                    "proxy_remote_job_id": "remote-actual",
                }
            )
            peer_state = MagicMock()
            peer_state.peer.return_value = {
                "base_url": "http://192.168.1.20:38193",
                "access_token": "token",
            }
            route_settings = SimpleNamespace(api_key="", desktop_mode=False)
            manager = MagicMock()
            transport = httpx.ASGITransport(app=main_module.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                with (
                    patch.object(main_module, "store", jobs),
                    patch.object(main_module, "local_state", peer_state),
                    patch.object(main_module, "settings", route_settings),
                    patch.object(main_module, "manager", manager),
                    patch.object(main_module.httpx, "AsyncClient", RemoteClient),
                ):
                    response = await client.delete("/api/v1/generations/proxy-local")
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(jobs.get("proxy-local"))
            self.assertFalse(backup_path.exists())
            manager.remove.assert_called_once_with("proxy-local")

        with TemporaryDirectory() as temp:
            asyncio.run(run_test(temp))
