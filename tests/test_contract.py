import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

os.environ.setdefault("H3_ROOT", str(Path(tempfile.gettempdir()) / "minimax-h3-api-tests"))

from fastapi import HTTPException

from app.engine import (
    ComfyUIH3Engine,
    RemoteTaskUnavailableError,
    RunningHubH3Engine,
    create_engine,
    probe_node,
    probe_runninghub_node,
    runninghub_account_profile,
    runninghub_billing_delta,
)
from app.jobs import JobManager, JobStore, runninghub_target
from app.main import align_frames, validate_execution_mode, validate_generation, validate_references
from app.music_prompts import MUSIC3_ARRANGEMENT_SYSTEM_PROMPT, MUSIC3_LYRICS_SYSTEM_PROMPT
from app.nodes import ComfyNodeConfig, NodeRegistry, parse_runninghub_resource_url
from app.prompts import FL2VA_SYSTEM_PROMPT
from app.ref2va_prompts import REF2VA_SYSTEM_PROMPT
from app.tts_prompts import TTS_SYSTEM_PROMPT
from app.runninghub import assign_media_fields, build_ai_app_schema, build_workflow_schema, normalize_parameters
from app.settings import Settings


RUNNINGHUB_AI_APP_ID = "2086401261143273474"


class ContractTests(unittest.TestCase):
    def test_active_remote_checkpoint_is_restored_without_progress_reset(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "jobs"
            jobs_dir.mkdir()
            checkpoint = {
                "provider": "comfyui",
                "node_id": "gpu-2",
                "remote_id": "prompt-123",
                "submitted_at": "2026-08-19T00:00:00+00:00",
            }
            (jobs_dir / "resume.json").write_text(
                json.dumps(
                    {
                        "id": "resume",
                        "status": "running",
                        "stage": "联合音视频采样 4/10",
                        "progress": 47,
                        "created_at": "2026-08-19T00:00:00+00:00",
                        "request": {"comfy_node": "auto"},
                        "remote_checkpoint": checkpoint,
                    }
                ),
                encoding="utf-8",
            )

            restored = JobStore(jobs_dir).get("resume")

            self.assertEqual(restored["status"], "queued")
            self.assertEqual(restored["progress"], 47)
            self.assertEqual(restored["remote_checkpoint"], checkpoint)
            self.assertIn("重新连接远端任务", restored["stage"])

    def test_legacy_active_job_without_checkpoint_keeps_existing_restore_behavior(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "jobs"
            jobs_dir.mkdir()
            (jobs_dir / "legacy.json").write_text(
                json.dumps(
                    {
                        "id": "legacy",
                        "status": "running",
                        "stage": "旧任务执行中",
                        "progress": 47,
                        "created_at": "2026-08-19T00:00:00+00:00",
                        "request": {"comfy_node": "auto"},
                    }
                ),
                encoding="utf-8",
            )

            restored = JobStore(jobs_dir).get("legacy")

            self.assertEqual(restored["status"], "queued")
            self.assertEqual(restored["progress"], 0)
            self.assertNotIn("remote_checkpoint", restored)

    def test_job_manager_resumes_checkpoint_on_original_node_and_clears_it(self):
        class ResumeEngine:
            calls = []

            def __init__(self, node_id, output):
                self.node_id = node_id
                self.output = output

            def generate(
                self,
                job,
                progress,
                cancelled,
                checkpoint=None,
                checkpoint_callback=None,
            ):
                self.calls.append((self.node_id, checkpoint))
                progress(75, "恢复查询")
                return self.output

        with TemporaryDirectory() as temp:
            root = Path(temp)
            jobs_dir = root / "jobs"
            jobs_dir.mkdir()
            output = root / "result.mp4"
            output.write_bytes(b"video")
            store = JobStore(jobs_dir)
            checkpoint = {
                "provider": "comfyui",
                "node_id": "gpu-b",
                "remote_id": "prompt-456",
                "submitted_at": "2026-08-19T00:00:00+00:00",
            }
            store.create(
                {
                    "id": "resume-node",
                    "status": "queued",
                    "stage": "等待恢复",
                    "progress": 52,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "request": {"comfy_node": "auto"},
                    "input_paths": [],
                    "remote_checkpoint": checkpoint,
                }
            )
            nodes = (
                ComfyNodeConfig("gpu-a", "GPU A", "http://gpu-a:8188"),
                ComfyNodeConfig("gpu-b", "GPU B", "http://gpu-b:8188"),
            )
            ResumeEngine.calls = []
            manager = JobManager(
                store,
                lambda node: ResumeEngine(node.id, output),
                nodes=nodes,
            )
            manager.start()
            try:
                for _ in range(100):
                    if store.get("resume-node")["status"] == "completed":
                        break
                    import time

                    time.sleep(0.02)
                completed = store.get("resume-node")
                self.assertEqual(completed["status"], "completed")
                self.assertIsNone(completed["remote_checkpoint"])
                self.assertEqual(ResumeEngine.calls, [("gpu-b", checkpoint)])
            finally:
                manager.stop()

    def test_transient_remote_failure_requeues_existing_checkpoint(self):
        class RetryEngine:
            calls = 0

            def __init__(self, output):
                self.output = output

            def generate(
                self,
                job,
                progress,
                cancelled,
                checkpoint=None,
                checkpoint_callback=None,
            ):
                self.__class__.calls += 1
                if self.calls == 1:
                    raise RemoteTaskUnavailableError("temporary query failure")
                return self.output

        with TemporaryDirectory() as temp:
            root = Path(temp)
            jobs_dir = root / "jobs"
            jobs_dir.mkdir()
            output = root / "result.mp4"
            output.write_bytes(b"video")
            store = JobStore(jobs_dir)
            checkpoint = {
                "provider": "comfyui",
                "node_id": "gpu-a",
                "remote_id": "prompt-retry",
            }
            store.create(
                {
                    "id": "retry-remote",
                    "status": "queued",
                    "stage": "等待恢复",
                    "progress": 63,
                    "created_at": "2026-08-19T00:00:00+00:00",
                    "request": {"comfy_node": "gpu-a"},
                    "input_paths": [],
                    "remote_checkpoint": checkpoint,
                }
            )
            RetryEngine.calls = 0
            manager = JobManager(
                store,
                lambda node: RetryEngine(output),
                nodes=(
                    ComfyNodeConfig(
                        "gpu-a", "GPU A", "http://gpu-a:8188"
                    ),
                ),
            )
            manager.start()
            try:
                for _ in range(100):
                    if store.get("retry-remote")["status"] == "completed":
                        break
                    import time

                    time.sleep(0.02)
                completed = store.get("retry-remote")
                self.assertEqual(completed["status"], "completed")
                self.assertEqual(RetryEngine.calls, 2)
                self.assertIsNone(completed["remote_checkpoint"])
            finally:
                manager.stop()

    @patch("app.engine.ComfyUIH3Engine._release_vram")
    @patch("websockets.sync.client.connect")
    @patch("httpx.Client")
    def test_comfyui_submission_persists_prompt_checkpoint(
        self, client_class, connect, _release_vram
    ):
        settings = Settings()
        node = ComfyNodeConfig("gpu-1", "GPU 1", "http://gpu-1:8188")
        engine = ComfyUIH3Engine(settings, node)
        client = client_class.return_value.__enter__.return_value
        stats = MagicMock()
        stats.json.return_value = {"devices": [{"type": "cuda", "index": 0}]}
        submit = MagicMock()
        submit.json.return_value = {"prompt_id": "prompt-checkpoint"}
        client.get.return_value = stats
        client.post.return_value = submit
        connect.return_value.__enter__.return_value = MagicMock()
        checkpoints = []
        history = {
            "status": {"completed": True, "status_str": "success"},
            "outputs": {},
        }
        with (
            patch.object(engine, "_upload_inputs", return_value=["input.png"]),
            patch.object(engine, "_build_workflow", return_value={"1": {}}),
            patch.object(engine, "_wait_for_finished", return_value=history),
            patch.object(engine, "_copy_result", return_value=Path("result.mp4")),
        ):
            engine.generate(
                {"id": "job", "request": {}, "input_paths": []},
                lambda *_: None,
                lambda: False,
                checkpoint_callback=checkpoints.append,
            )

        self.assertEqual(checkpoints[0]["provider"], "comfyui")
        self.assertEqual(checkpoints[0]["node_id"], "gpu-1")
        self.assertEqual(checkpoints[0]["remote_id"], "prompt-checkpoint")
        self.assertTrue(checkpoints[0]["client_id"].startswith("minimax-h3-api-"))

    @patch("app.engine.ComfyUIH3Engine._release_vram")
    @patch("httpx.Client")
    def test_comfyui_recovery_queries_original_prompt_without_submission(
        self, client_class, _release_vram
    ):
        engine = ComfyUIH3Engine(
            Settings(),
            ComfyNodeConfig("gpu-1", "GPU 1", "http://gpu-1:8188"),
        )
        client = client_class.return_value.__enter__.return_value
        history = {
            "status": {"completed": True, "status_str": "success"},
            "outputs": {},
        }
        checkpoint = {
            "provider": "comfyui",
            "node_id": "gpu-1",
            "remote_id": "prompt-existing",
        }
        with (
            patch.object(engine, "_poll_until_finished", return_value=history) as poll,
            patch.object(engine, "_upload_inputs") as upload,
            patch.object(engine, "_copy_result", return_value=Path("result.mp4")),
        ):
            engine.generate(
                {"id": "job", "request": {}, "input_paths": []},
                lambda *_: None,
                lambda: False,
                checkpoint=checkpoint,
            )

        upload.assert_not_called()
        client.post.assert_not_called()
        self.assertTrue(poll.call_args.kwargs["recovering"])

    @patch("httpx.Client")
    def test_runninghub_submission_persists_task_checkpoint(self, client_class):
        node = ComfyNodeConfig(
            "rh-1",
            "RunningHub",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            "workflow-1",
            1,
            runninghub_schema={"fields": [], "output_types": ["video"]},
        )
        engine = RunningHubH3Engine(Settings(), node)
        checkpoints = []
        with (
            patch.object(engine, "_account_status", return_value={}),
            patch.object(engine, "_upload_inputs", return_value=[]),
            patch.object(engine, "_node_info_list", return_value=[]),
            patch.object(
                engine,
                "_request_json",
                return_value={"data": {"taskId": "task-checkpoint"}},
            ),
            patch.object(
                engine,
                "_poll",
                return_value={"results": [{"url": "https://example.com/result.mp4"}]},
            ),
            patch.object(engine, "_download_result", return_value=Path("result.mp4")),
        ):
            engine.generate(
                {"id": "job", "request": {"runninghub_schema": {"fields": []}}},
                lambda *_: None,
                lambda: False,
                checkpoint_callback=checkpoints.append,
            )

        self.assertEqual(checkpoints[0]["provider"], "runninghub")
        self.assertEqual(checkpoints[0]["node_id"], "rh-1")
        self.assertEqual(checkpoints[0]["remote_id"], "task-checkpoint")

    @patch("httpx.Client")
    def test_runninghub_recovery_skips_upload_and_submission(self, client_class):
        node = ComfyNodeConfig(
            "rh-1",
            "RunningHub",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            "workflow-1",
            1,
            runninghub_schema={"fields": [], "output_types": ["video"]},
        )
        engine = RunningHubH3Engine(Settings(), node)
        checkpoint = {
            "provider": "runninghub",
            "node_id": "rh-1",
            "remote_id": "task-existing",
        }
        with (
            patch.object(engine, "_account_status", return_value={}),
            patch.object(engine, "_upload_inputs") as upload,
            patch.object(engine, "_request_json") as request_json,
            patch.object(
                engine,
                "_poll",
                return_value={"results": [{"url": "https://example.com/result.mp4"}]},
            ) as poll,
            patch.object(engine, "_download_result", return_value=Path("result.mp4")),
        ):
            engine.generate(
                {"id": "job", "request": {"runninghub_schema": {"fields": []}}},
                lambda *_: None,
                lambda: False,
                checkpoint=checkpoint,
            )

        upload.assert_not_called()
        request_json.assert_not_called()
        self.assertEqual(poll.call_args.args[1], "task-existing")

    def test_desktop_chat_layout_keeps_composer_inside_viewport(self):
        project_root = Path(__file__).resolve().parents[1]
        styles = (project_root / "static" / "styles.css").read_text(encoding="utf-8")
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn("grid-template-rows: minmax(0, 1fr)", styles)
        self.assertRegex(
            styles,
            r"\.conversation-column \{[^}]*height: 100%;[^}]*overflow: hidden;",
        )
        self.assertIn('/assets/styles.css?v=42', index)

    def test_settings_popover_is_outside_horizontal_scroll_container(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")

        toolbar_left = index.index('<div class="toolbar-left">')
        toolbar_actions = index.index('<div class="toolbar-actions">')
        settings = index.index('<details class="settings-popover"')
        self.assertGreater(settings, toolbar_actions)
        self.assertGreater(toolbar_actions, toolbar_left)

    def test_comfy_nodes_and_health_interval_are_stored_in_sqlite(self):
        with TemporaryDirectory() as temp:
            registry = NodeRegistry(Path(temp) / "config.db")
            self.assertEqual(registry.configs()[0].url, "http://127.0.0.1:8188")
            self.assertEqual(registry.configs()[0].provider, "comfyui")
            registry.create("gpu-2", "GPU 2", "http://10.0.0.12:8188/")
            self.assertEqual(len(registry.configs()), 2)
            self.assertEqual(registry.get("gpu-2")["url"], "http://10.0.0.12:8188")
            self.assertEqual(registry.set_health_interval(90), 90)
            self.assertEqual(registry.health_interval(), 90)

    def test_all_inference_nodes_can_be_deleted_without_recreation(self):
        with TemporaryDirectory() as temp:
            database = Path(temp) / "config.db"
            registry = NodeRegistry(database)
            self.assertTrue(registry.delete("local"))
            self.assertEqual(registry.configs(), ())
            reopened = NodeRegistry(database)
            self.assertEqual(reopened.configs(), ())

            jobs_dir = Path(temp) / "jobs"
            jobs_dir.mkdir()
            manager = JobManager(JobStore(jobs_dir), lambda node: None, nodes=())
            self.assertEqual(manager.node_ids, set())
            self.assertEqual(manager.nodes_public(), [])
            manager.reconfigure([], 60)
            self.assertEqual(manager.node_ids, set())

    def test_runninghub_nodes_store_secrets_privately_and_allow_shared_base_urls(self):
        with TemporaryDirectory() as temp:
            registry = NodeRegistry(Path(temp) / "config.db")
            first = registry.create(
                "rh-1",
                "RunningHub 1",
                "https://www.runninghub.ai/",
                "runninghub",
                "secret-one",
                "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474",
                3,
            )
            registry.create(
                "rh-2",
                "RunningHub 2",
                "https://www.runninghub.ai",
                "runninghub",
                "secret-two",
                "https://www.runninghub.ai/zh-cn/workflow/1904136902449209347",
                2,
            )

            self.assertNotIn("api_key", first)
            self.assertTrue(first["has_api_key"])
            self.assertEqual(first["max_concurrency"], 3)
            configs = {node.id: node for node in registry.configs()}
            self.assertEqual(configs["rh-1"].api_key, "secret-one")
            self.assertEqual(configs["rh-1"].workflow_id, RUNNINGHUB_AI_APP_ID)
            self.assertEqual(configs["rh-1"].runninghub_resource_type, "ai-app")
            self.assertEqual(configs["rh-2"].workflow_id, "1904136902449209347")
            updated = registry.update(
                "rh-1",
                "RunningHub 1",
                "https://www.runninghub.ai",
                True,
                "runninghub",
                "",
                "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474",
                4,
            )
            self.assertTrue(updated["has_api_key"])
            self.assertEqual(
                {node.id: node for node in registry.configs()}["rh-1"].api_key,
                "secret-one",
            )

    def test_runninghub_resource_url_is_normalized_and_classified(self):
        url, resource_id, resource_type = parse_runninghub_resource_url(
            "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474/?from=share"
        )
        self.assertEqual(
            url,
            "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474",
        )
        self.assertEqual(resource_id, RUNNINGHUB_AI_APP_ID)
        self.assertEqual(resource_type, "ai-app")
        with self.assertRaisesRegex(ValueError, "RunningHub 官方 HTTPS 地址"):
            parse_runninghub_resource_url(
                "https://example.com/zh-cn/ai-detail/2086401261143273474"
            )

    def test_node_provider_change_requires_or_clears_api_key(self):
        with TemporaryDirectory() as temp:
            registry = NodeRegistry(Path(temp) / "config.db")
            registry.create(
                "remote",
                "Remote ComfyUI",
                "https://comfy.example.com",
                "comfyui",
                "comfy-secret",
            )
            with self.assertRaisesRegex(ValueError, "必须填写 API Key"):
                registry.update(
                    "remote",
                    "RunningHub",
                    "https://www.runninghub.ai",
                    True,
                    "runninghub",
                    "",
                    "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474",
                    1,
                )
            registry.update(
                "remote",
                "RunningHub",
                "https://www.runninghub.ai",
                True,
                "runninghub",
                "runninghub-secret",
                "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474",
                2,
            )
            registry.update(
                "remote",
                "Remote ComfyUI",
                "https://comfy.example.com",
                True,
                "comfyui",
                "",
                "",
                1,
            )
            config = {node.id: node for node in registry.configs()}["remote"]
            self.assertEqual(config.provider, "comfyui")
            self.assertEqual(config.api_key, "")

    def test_legacy_node_table_migrates_without_unique_url_constraint(self):
        with TemporaryDirectory() as temp:
            database = Path(temp) / "config.db"
            with sqlite3.connect(database) as connection:
                connection.executescript(
                    """
                    CREATE TABLE comfy_nodes (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL UNIQUE,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE TABLE service_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    INSERT INTO comfy_nodes VALUES (
                        'local', 'Local', 'http://127.0.0.1:8188', 1, 'now', 'now'
                    );
                    """
                )
            registry = NodeRegistry(database)
            self.assertEqual(registry.get("local")["provider"], "comfyui")
            registry.create("local-2", "Local 2", "http://127.0.0.1:8188")
            self.assertEqual(len(registry.configs()), 2)

    def test_runninghub_capacity_creates_multiple_scheduler_slots(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "jobs"
            jobs_dir.mkdir()
            manager = JobManager(
                JobStore(jobs_dir),
                lambda node: None,
                nodes=(
                    ComfyNodeConfig(
                        "rh",
                        "RunningHub",
                        "https://www.runninghub.ai",
                        "runninghub",
                        "secret",
                        "workflow",
                        3,
                    ),
                ),
            )
            self.assertEqual(manager.parallel_capacity, 3)
            self.assertEqual(manager.nodes_public()[0]["capacity"], 3)
            manager.start()
            try:
                self.assertEqual(len(manager._threads), 3)
            finally:
                manager.stop()

    def test_runninghub_schema_drives_workflow_selection(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "jobs"
            jobs_dir.mkdir()
            schema = {
                "version": 1,
                "resource_type": "workflow",
                "resource_id": "workflow-1",
                "name": "Generic Workflow",
                "fields": [
                    {
                        "key": "10.text",
                        "node_id": "10",
                        "field_name": "text",
                        "field_type": "STRING",
                        "default": "",
                        "editable": True,
                        "media_kind": None,
                    }
                ],
                "primary_text_key": "10.text",
                "output_types": ["video"],
            }
            node = ComfyNodeConfig(
                "rh",
                "H3 Ref2VA 8 Step",
                "https://www.runninghub.ai",
                "runninghub",
                "secret",
                "workflow-1",
                2,
                "https://www.runninghub.ai/workflow/workflow-1",
                "workflow",
                "Generic Workflow",
                schema,
            )
            manager = JobManager(
                JobStore(jobs_dir),
                lambda config: None,
                nodes=(node,),
                health_probe=lambda config: {
                    "workflow_name": "Generic Workflow",
                    "runninghub_schema": schema,
                    "account_balance_coins": 1200,
                    "account_balance_money": 12.5,
                    "account_currency": "CNY",
                    "account_current_tasks": 1,
                },
            )
            manager.refresh_node_health()
            self.assertEqual(
                manager.workflow_profile("rh"),
                {
                    "provider": "runninghub",
                    "runninghub_resource_type": "workflow",
                    "workflow_id": "workflow-1",
                    "workflow_url": "https://www.runninghub.ai/workflow/workflow-1",
                    "workflow_name": "Generic Workflow",
                    "runninghub_schema": schema,
                },
            )
            self.assertEqual(manager.workflow_profile("auto"), manager.workflow_profile("rh"))
            workflow_target = runninghub_target("workflow-1")
            self.assertTrue(manager.accepts_node(workflow_target))
            self.assertEqual(manager.node_provider(workflow_target), "runninghub")
            self.assertEqual(
                manager.workflow_profile(workflow_target),
                manager.workflow_profile("rh"),
            )
            public = manager.nodes_public()[0]
            self.assertEqual(public["workflow_name"], "Generic Workflow")
            self.assertEqual(public["workflow_id"], "workflow-1")
            self.assertEqual(public["account_balance_coins"], 1200)
            self.assertEqual(public["account_balance_money"], 12.5)
            self.assertEqual(public["account_currency"], "CNY")
            manager.health_probe = MagicMock(
                return_value={
                    "account_balance_coins": 1100,
                    "account_current_tasks": 0,
                    "workflow_error": "RunningHub 读取工作流失败：WORKFLOW_NOT_EXISTS",
                }
            )
            manager.refresh_node_health()
            public = manager.nodes_public()[0]
            self.assertEqual(public["account_balance_coins"], 1100)
            self.assertIsNone(public["error"])
            self.assertIn("WORKFLOW_NOT_EXISTS", public["workflow_error"])
            self.assertEqual(
                manager.workflow_profile("rh"),
                {
                    "provider": "runninghub",
                    "runninghub_resource_type": "workflow",
                    "workflow_id": "workflow-1",
                    "workflow_url": "https://www.runninghub.ai/workflow/workflow-1",
                    "workflow_name": "Generic Workflow",
                    "runninghub_schema": schema,
                },
            )
            manager.health_probe = MagicMock(side_effect=RuntimeError("balance unavailable"))
            manager.refresh_node_health()
            public = manager.nodes_public()[0]
            self.assertTrue(public["healthy"])
            self.assertEqual(public["account_balance_coins"], 1100)
            self.assertIn("balance unavailable", public["account_error"])

    def test_runninghub_account_balance_and_call_cost_are_parsed(self):
        before = runninghub_account_profile(
            {
                "data": {
                    "remainCoins": "99999",
                    "currentTaskCounts": "1",
                    "remainMoney": "999.5",
                    "currency": "cny",
                }
            }
        )
        after = runninghub_account_profile(
            {
                "data": {
                    "remainCoins": "99849",
                    "currentTaskCounts": "0",
                    "remainMoney": "998",
                    "currency": "CNY",
                }
            }
        )
        billing = runninghub_billing_delta(before, after)
        self.assertEqual(before["account_current_tasks"], 1)
        self.assertEqual(billing["consumed_coins"], 150)
        self.assertEqual(billing["consumed_money"], 1.5)
        self.assertEqual(billing["account_currency"], "CNY")

    def test_runninghub_probe_result_is_forwarded_to_scheduler(self):
        node = ComfyNodeConfig(
            "rh",
            "RunningHub",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            "workflow",
            1,
        )
        expected = {"account_balance_coins": 500}
        with patch("app.engine.probe_runninghub_node", return_value=expected):
            self.assertEqual(probe_node(node), expected)

    def test_runninghub_probe_keeps_account_profile_when_workflow_is_unavailable(self):
        node = ComfyNodeConfig(
            "rh",
            "RunningHub",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            "workflow",
            1,
        )
        account_response = MagicMock()
        account_response.json.return_value = {
            "code": 0,
            "data": {"remainCoins": 4644, "currentTaskCounts": 0},
        }
        workflow_response = MagicMock()
        workflow_response.json.return_value = {
            "code": 1,
            "msg": "WORKFLOW_NOT_EXISTS",
        }
        client = MagicMock()
        client.__enter__.return_value = client
        client.post.side_effect = [account_response, workflow_response]

        with patch("httpx.Client", return_value=client):
            profile = probe_runninghub_node(node)

        self.assertEqual(profile["account_balance_coins"], 4644)
        self.assertEqual(profile["account_current_tasks"], 0)
        self.assertIn("WORKFLOW_NOT_EXISTS", profile["workflow_error"])

    def test_prompt_optimizers_require_simplified_chinese(self):
        self.assertIn("必须使用简体中文", FL2VA_SYSTEM_PROMPT)
        self.assertIn("必须使用简体中文", REF2VA_SYSTEM_PROMPT)

    def test_asset_listing_excludes_incognito_by_default(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "data" / "jobs"
            jobs_dir.mkdir(parents=True)
            store = JobStore(jobs_dir)
            visible = {
                "id": "visible",
                "title": "visible",
                "status": "completed",
                "created_at": "2026-08-05T00:00:00+00:00",
                "request": {"prompt": "visible prompt", "incognito": False},
            }
            hidden = {
                "id": "hidden",
                "title": "hidden",
                "status": "completed",
                "created_at": "2026-08-05T00:01:00+00:00",
                "request": {"prompt": "hidden prompt", "incognito": True},
            }
            store.create(visible)
            store.create(hidden)

            items, total = store.list(1, 20)
            self.assertEqual(total, 1)
            self.assertEqual([item["id"] for item in items], ["visible"])
            items, total = store.list(1, 20, include_incognito=True)
            self.assertEqual(total, 2)
            self.assertEqual({item["id"] for item in items}, {"visible", "hidden"})

            items, total = store.list(1, 20, scope="incognito")
            self.assertEqual(total, 1)
            self.assertEqual([item["id"] for item in items], ["hidden"])
            items, total = store.list(1, 20, scope="normal")
            self.assertEqual(total, 1)
            self.assertEqual([item["id"] for item in items], ["visible"])

    def test_job_store_exposes_incremental_public_changes(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "data" / "jobs"
            jobs_dir.mkdir(parents=True)
            store = JobStore(jobs_dir)
            cursor = store.revision
            store.create(
                {
                    "id": "visible",
                    "status": "queued",
                    "created_at": "2026-08-14T00:00:00+00:00",
                    "request": {"prompt": "visible", "incognito": False},
                }
            )
            store.create(
                {
                    "id": "restricted",
                    "status": "queued",
                    "created_at": "2026-08-14T00:01:00+00:00",
                    "request": {"prompt": "restricted", "incognito": True},
                }
            )

            changes = store.changes_since(cursor)
            self.assertEqual([job["id"] for job in changes["jobs"]], ["visible"])
            cursor = changes["revision"]
            store.delete("visible")
            changes = store.changes_since(cursor)
            self.assertEqual(changes["deleted_job_ids"], ["visible"])

    def test_node_manager_and_incremental_sse_frontend_contract(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")
        styles = (project_root / "static" / "styles.css").read_text(encoding="utf-8")
        main = (project_root / "app" / "main.py").read_text(encoding="utf-8")

        self.assertIn('id="openNodeManager"', index)
        self.assertIn('id="nodeEditor"', index)
        self.assertNotIn('id="nodeId"', index)
        self.assertIn('id="nodeProvider"', index)
        self.assertIn('value="runninghub"', index)
        self.assertIn('id="nodeApiKey"', index)
        self.assertIn('id="nodeWorkflowUrl"', index)
        self.assertIn('name="workflow_url"', index)
        self.assertIn('id="nodeMaxConcurrency"', index)
        self.assertIn('id="runningHubWorkflowControl"', index)
        self.assertIn('api("/api/v1/comfy/nodes")', app_js)
        self.assertIn("当前没有可用推理节点，请添加推理节点", main)
        self.assertIn('node_id = f"node-{secrets.token_hex(4)}"', main)
        self.assertIn('function syncNodeProviderFields()', app_js)
        self.assertIn('running_count', app_js)
        self.assertIn('function selectedRunningHubNode()', app_js)
        self.assertIn('const RUNNINGHUB_TARGET_PREFIX = "rh:";', app_js)
        self.assertIn("runningHubGroups", app_js)
        self.assertIn('el("modelControl").hidden = Boolean(runningHubNode);', app_js)
        self.assertIn('function renderRunningHubParameters()', app_js)
        self.assertIn('runninghub_parameters', app_js)
        self.assertIn('function runningHubBalanceLabel(node)', app_js)
        self.assertIn('function runningHubCostLabel(node)', app_js)
        self.assertIn('node-accounting', app_js)
        self.assertIn('account_balance_money', main + app_js)
        self.assertIn("prepare_runninghub_request", main)
        self.assertIn("runninghub_resource_id", main)
        self.assertIn('function applyJobUpsert(job)', app_js)
        self.assertIn('request.headers.get("last-event-id"', main)
        self.assertIn(".modal-overlay.node-modal", styles)

    def test_asset_detail_infinite_scroll_reuse_and_locale_contract(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")
        styles = (project_root / "static" / "styles.css").read_text(encoding="utf-8")
        main = (project_root / "app" / "main.py").read_text(encoding="utf-8")

        self.assertIn('id="assetDetailModal"', index)
        self.assertIn('id="downloadAssetDetail"', index)
        self.assertIn('id="regenerateAssetDetail"', index)
        self.assertIn('id="languageToggle"', index)
        self.assertIn('id="apiDocsLink"', index)
        self.assertNotIn('id="previousAssetPage"', index)
        self.assertNotIn('id="nextAssetPage"', index)
        self.assertIn('conversationPageSize: 10', app_js)
        self.assertIn('state.conversationReady && movingUp && currentTop < 72', app_js)
        self.assertIn('function openAssetDetail(jobId)', app_js)
        self.assertIn('async function backfillJob(jobId)', app_js)
        self.assertIn('download.href = downloadable ? job.result_url : "#"', app_js)
        self.assertIn('function mediaDownloadLabel(mediaType)', app_js)
        self.assertIn('data-job-action="regenerate"', app_js)
        self.assertIn('window.confirm(t("regenerateConfirm"))', app_js)
        self.assertIn('async function regenerateJob(jobId)', app_js)
        self.assertIn('"/api/v1/generations/{job_id}/regenerate"', main)
        self.assertIn("shutil.copy2(source, destination)", main)
        self.assertIn('data-job-action="reuse"', app_js)
        self.assertIn('loadAssets({ reset: true })', app_js)
        self.assertIn('grid.scrollHeight - grid.scrollTop - grid.clientHeight < 180', app_js)
        self.assertIn('.asset-detail-dialog', styles)

    def test_public_references_have_view_urls(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "data" / "jobs"
            jobs_dir.mkdir(parents=True)
            store = JobStore(jobs_dir)
            store.create(
                {
                    "id": "media-job",
                    "status": "queued",
                    "created_at": "2026-08-05T00:00:00+00:00",
                    "request": {"references": [{"type": "image", "name": "frame.png"}]},
                    "input_paths": [str(Path(temp) / "data" / "uploads" / "media-job" / "01_image.png")],
                }
            )
            public = store.public("media-job")
            self.assertEqual(
                public["request"]["references"][0]["url"],
                "/api/v1/generations/media-job/references/0",
            )

    def test_public_job_defaults_to_native_and_reports_elapsed_seconds(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "data" / "jobs"
            jobs_dir.mkdir(parents=True)
            store = JobStore(jobs_dir)
            store.create(
                {
                    "id": "timed-job",
                    "status": "completed",
                    "created_at": "2026-08-05T00:00:00+00:00",
                    "updated_at": "2026-08-05T00:02:03.4+00:00",
                    "request": {"references": []},
                }
            )

            public = store.public("timed-job")
            self.assertEqual(public["request"]["execution_mode"], "native")
            self.assertEqual(public["elapsed_seconds"], 123.4)

    def test_generation_workflows_remain_available(self):
        project_root = Path(__file__).resolve().parents[1]
        workflow_dir = project_root / "workflows"
        configured = Settings()

        def local_or_configured(name: str, configured_path: Path) -> Path:
            local_path = workflow_dir / name
            return local_path if local_path.exists() else configured_path

        settings = Settings(
            comfy_workflow=local_or_configured(
                "minimax_h3_fl2va_fp8_720p_15s_api.json",
                configured.comfy_workflow,
            ),
            comfy_ref2va_workflow=local_or_configured(
                "minimax_h3_ref2va_fp8_scaled_api.json",
                configured.comfy_ref2va_workflow,
            ),
            comfy_turbo_workflow=local_or_configured(
                "minimax_h3_fl2va_fp8_turbo_lora_api.json",
                configured.comfy_turbo_workflow,
            ),
            comfy_ref2va_turbo_workflow=local_or_configured(
                "minimax_h3_ref2va_fp8_turbo_lora_api.json",
                configured.comfy_ref2va_turbo_workflow,
            ),
            comfy_nsfw_workflow=local_or_configured(
                "minimax_h3_ref2va_fp8_nsfw_lora_api.json",
                configured.comfy_nsfw_workflow,
            ),
            comfy_digital_human_workflow=local_or_configured(
                "minimax_h3_ref2va_fp8_digital_human_api.json",
                configured.comfy_digital_human_workflow,
            ),
            comfy_music3_workflow=local_or_configured(
                "minimax_music3_int8_api.json",
                configured.comfy_music3_workflow,
            ),
        )
        engine = ComfyUIH3Engine(settings)

        for variant in ("fl2va-fp8", "ref2va-fp8"):
            native = engine._load_workflow(variant, "native")
            self.assertNotIn("140", native)

            turbo = engine._load_workflow(variant, "turbo-lora")
            self.assertEqual(turbo["123"]["class_type"], "KSamplerSelect")
            self.assertEqual(turbo["123"]["inputs"]["sampler_name"], "res_multistep")
            self.assertEqual(turbo["124"]["inputs"]["scheduler"], "simple")
            self.assertEqual(turbo["142"]["class_type"], "LoraLoaderModelOnly")
            self.assertEqual(
                turbo["142"]["inputs"]["lora_name"],
                "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
            )
            self.assertEqual(turbo["142"]["inputs"]["strength_model"], 1.0)
            self.assertEqual(turbo["143"]["class_type"], "MiniMaxH3SigmaShift")
            self.assertEqual(turbo["143"]["inputs"]["shift_video"], 12.0)
            self.assertEqual(turbo["143"]["inputs"]["shift_audio"], 3.0)
            self.assertEqual(turbo["143"]["inputs"]["model"], ["142", 0])
            self.assertEqual(turbo["124"]["inputs"]["model"], ["143", 0])
            self.assertEqual(turbo["124"]["inputs"]["steps"], 8)
            self.assertEqual(turbo["126"]["inputs"]["model"], ["143", 0])
            expected_model = (
                "minimax_h3_fl2va_pruned_fp8_scaled.safetensors"
                if variant == "fl2va-fp8"
                else "minimax_h3_ref2va_pruned_fp8_scaled.safetensors"
            )
            self.assertEqual(turbo["127"]["inputs"]["unet_name"], expected_model)

        with self.assertRaises(ValueError):
            engine._load_workflow("ref2va-fp8", "speed-cache")

        nsfw = engine._load_workflow("ref2va-fp8", "h3-nsfw")
        self.assertEqual(nsfw["141"]["class_type"], "LoraLoaderBypass")
        self.assertEqual(
            nsfw["141"]["inputs"]["lora_name"],
            "NaughtyTimes-lora-MINIMAXH3.safetensors",
        )
        self.assertEqual(nsfw["141"]["inputs"]["strength_model"], 0.5)
        self.assertEqual(nsfw["141"]["inputs"]["strength_clip"], 0.0)
        self.assertEqual(nsfw["124"]["inputs"]["model"], ["141", 0])
        self.assertEqual(nsfw["126"]["inputs"]["model"], ["141", 0])
        self.assertEqual(nsfw["136"]["inputs"]["clip"], ["141", 1])

        digital_human = engine._load_workflow("ref2va-fp8", "digital-human")
        self.assertEqual(digital_human["172"]["class_type"], "VRGDG_MiniMaxH3AudioDrive")
        self.assertEqual(digital_human["125"]["inputs"]["latent_image"], ["172", 0])
        self.assertEqual(digital_human["130"]["inputs"]["audio"], ["172", 1])
        self.assertNotIn("121", digital_human)

        music3 = engine._load_workflow("music3-int8", "music3")
        self.assertEqual(music3["6"]["inputs"]["unet_name"], "minimax_music3_dit_int8_convrot.safetensors")
        self.assertEqual(music3["3"]["class_type"], "CLIPLoaderMultiGPU")
        self.assertEqual(music3["3"]["inputs"]["type"], "minimax")
        self.assertEqual(music3["3"]["inputs"]["device"], "cuda:0")
        self.assertEqual(music3["9"]["inputs"]["steps"], 30)
        self.assertEqual(music3["42"]["class_type"], "VAEDecodeAudioTiled")
        self.assertEqual(music3["92"]["class_type"], "SaveAudio")

    def test_runninghub_engine_maps_job_parameters_to_node_info_list(self):
        workflow = {
            "10": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "default prompt", "clip": ["1", 0]},
                "_meta": {"title": "Prompt"},
            },
            "11": {
                "class_type": "LoadImage",
                "inputs": {"image": "default.png"},
                "_meta": {"title": "Reference"},
            },
            "12": {
                "class_type": "KSampler",
                "inputs": {"steps": 20, "seed": 1, "model": ["1", 0]},
                "_meta": {"title": "Sampler"},
            },
        }
        schema = build_workflow_schema(
            "1904136902449209346",
            "https://www.runninghub.ai/workflow/1904136902449209346",
            workflow,
            "Generic image workflow",
        )
        node = ComfyNodeConfig(
            "rh",
            "RunningHub",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            "1904136902449209346",
            2,
            "https://www.runninghub.ai/workflow/1904136902449209346",
            "workflow",
            "Generic image workflow",
            schema,
        )
        engine = RunningHubH3Engine(Settings(), node)
        manifest = assign_media_fields(schema, [{"type": "image"}])
        parameters = normalize_parameters(
            schema,
            {"10.text": "test prompt", "12.steps": 30, "12.seed": 123},
        )
        job = {
            "id": "runninghub-job",
            "request": {
                "runninghub_schema": schema,
                "runninghub_parameters": parameters,
                "references": manifest,
            },
        }
        uploaded = ["api/input.png"]
        node_info = engine._node_info_list(job, uploaded)
        mapped = {
            (item["nodeId"], item["fieldName"]): item["fieldValue"]
            for item in node_info
        }

        self.assertEqual(mapped[("10", "text")], "test prompt")
        self.assertEqual(mapped[("11", "image")], "api/input.png")
        self.assertEqual(mapped[("12", "steps")], 30)
        self.assertEqual(mapped[("12", "seed")], 123)
        self.assertIsInstance(create_engine(Settings(), node), RunningHubH3Engine)

    def test_runninghub_ai_app_schema_maps_dynamic_inputs(self):
        schema = build_ai_app_schema(
            RUNNINGHUB_AI_APP_ID,
            f"https://www.runninghub.ai/zh-cn/ai-detail/{RUNNINGHUB_AI_APP_ID}",
            {
                "webappName": "Generic AI App",
                "nodeInfoList": [
                    {
                        "nodeId": "39",
                        "fieldName": "value",
                        "fieldType": "STRING",
                        "fieldValue": "",
                        "description": "Prompt",
                    },
                    {
                        "nodeId": "36",
                        "fieldName": "image",
                        "fieldType": "IMAGE",
                        "description": "Reference image",
                    },
                    {
                        "nodeId": "37",
                        "fieldName": "steps",
                        "fieldType": "INTEGER",
                        "fieldValue": 20,
                        "description": "Steps",
                    },
                ],
            },
            {},
        )
        node = ComfyNodeConfig(
            "rh-app",
            "Ref2VA-bf16-Full",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            RUNNINGHUB_AI_APP_ID,
            1,
            "https://www.runninghub.ai/zh-cn/ai-detail/2086401261143273474",
            "ai-app",
            "Generic AI App",
            schema,
        )
        engine = RunningHubH3Engine(Settings(), node)
        manifest = assign_media_fields(schema, [{"type": "image"}])
        job = {
            "id": "runninghub-ai-app-job",
            "request": {
                "runninghub_schema": schema,
                "runninghub_parameters": normalize_parameters(
                    schema, {"39.value": "test prompt", "37.steps": 8}
                ),
                "references": manifest,
            },
        }
        node_info = engine._node_info_list(job, ["uploaded-image.png"])
        mapped = {
            (item["nodeId"], item["fieldName"]): item["fieldValue"]
            for item in node_info
        }

        self.assertTrue(engine.is_ai_app)
        self.assertEqual(mapped[("39", "value")], "test prompt")
        self.assertEqual(mapped[("36", "image")], "uploaded-image.png")
        self.assertEqual(mapped[("37", "steps")], 8)
        self.assertEqual(schema["name"], "Generic AI App")

    def test_runninghub_schema_locks_model_fields_and_validates_required_inputs(self):
        schema = build_ai_app_schema(
            RUNNINGHUB_AI_APP_ID,
            f"https://www.runninghub.ai/zh-cn/ai-detail/{RUNNINGHUB_AI_APP_ID}",
            {
                "webappName": "Required input app",
                "nodeInfoList": [
                    {
                        "nodeId": "1",
                        "nodeName": "Checkpoint Loader",
                        "fieldName": "ckpt_name",
                        "fieldType": "STRING",
                        "fieldValue": "locked.safetensors",
                    },
                    {
                        "nodeId": "2",
                        "fieldName": "prompt",
                        "fieldType": "STRING",
                        "description": "Prompt",
                        "required": True,
                    },
                    {
                        "nodeId": "3",
                        "fieldName": "image",
                        "fieldType": "IMAGE",
                        "description": "Image",
                        "required": True,
                    },
                ],
            },
            {},
        )
        fields = {field["key"]: field for field in schema["fields"]}
        self.assertFalse(fields["1.ckpt_name"]["editable"])
        with self.assertRaisesRegex(ValueError, "2.prompt"):
            normalize_parameters(schema, {})
        parameters = normalize_parameters(schema, {"2.prompt": "test"})
        with self.assertRaisesRegex(ValueError, "3.image"):
            assign_media_fields(schema, [])
        manifest = assign_media_fields(schema, [{"type": "image"}])
        self.assertEqual(parameters["2.prompt"], "test")
        self.assertEqual(manifest[0]["field_key"], "3.image")

    def test_runninghub_client_errors_are_not_retried(self):
        node = ComfyNodeConfig(
            "rh",
            "RunningHub",
            "https://www.runninghub.ai",
            "runninghub",
            "secret",
            "workflow",
            1,
        )
        engine = RunningHubH3Engine(Settings(), node)
        client = MagicMock()
        response = MagicMock(status_code=401, is_error=True)
        response.json.return_value = {"msg": "unauthorized"}
        client.request.return_value = response

        with self.assertRaisesRegex(RuntimeError, "unauthorized"):
            engine._request_json(
                client,
                "POST",
                "/task/openapi/create",
                json_data={"apiKey": "secret"},
                action="提交任务",
            )
        client.request.assert_called_once()

        with TemporaryDirectory() as temp:
            source = Path(temp) / "input.png"
            source.write_bytes(b"image")
            client.post.reset_mock()
            client.post.return_value = response
            with self.assertRaisesRegex(RuntimeError, "unauthorized"):
                engine._upload_inputs(
                    client,
                    {
                        "input_paths": [str(source)],
                        "request": {"references": [{"type": "image"}]},
                    },
                )
            client.post.assert_called_once()

    def test_nsfw_mode_requires_incognito_ref2va(self):
        validate_execution_mode("h3-nsfw", "ref2va-fp8", True)
        validate_execution_mode("turbo-lora", "fl2va-fp8", False)
        validate_execution_mode("turbo-lora", "ref2va-fp8", False)
        with self.assertRaises(HTTPException) as normal_context:
            validate_execution_mode("h3-nsfw", "ref2va-fp8", False)
        self.assertEqual(normal_context.exception.status_code, 403)
        with self.assertRaises(HTTPException) as fl2va_context:
            validate_execution_mode("h3-nsfw", "fl2va-fp8", True)
        self.assertEqual(fl2va_context.exception.status_code, 422)
        with self.assertRaises(HTTPException) as retired_context:
            validate_execution_mode("speed-cache", "ref2va-fp8", False)
        self.assertEqual(retired_context.exception.status_code, 422)

    def test_digital_human_mode_requires_ref2va(self):
        validate_execution_mode("digital-human", "ref2va-fp8", False)
        with self.assertRaises(HTTPException) as fl2va_context:
            validate_execution_mode("digital-human", "fl2va-fp8", False)
        self.assertEqual(fl2va_context.exception.status_code, 422)

    def test_music3_mode_requires_music3_model(self):
        validate_execution_mode("music3", "music3-int8", False)
        with self.assertRaises(HTTPException):
            validate_execution_mode("music3", "fl2va-fp8", False)
        with self.assertRaises(HTTPException):
            validate_execution_mode("native", "music3-int8", False)

    def test_speed_cache_is_removed_from_frontend_and_service(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")
        service = (project_root / "deploy" / "minimax-h3-api.service.in").read_text(encoding="utf-8")
        environment = (project_root / ".env.example").read_text(encoding="utf-8")
        deployment = service + environment

        self.assertNotIn('option value="speed-cache"', index)
        self.assertNotIn("H3_COMFY_SPEED_WORKFLOW", deployment)
        self.assertNotIn("H3_COMFY_REF2VA_SPEED_WORKFLOW", deployment)
        self.assertIn('option value="turbo-lora"', index)
        self.assertIn('option value="turbo-lora">8-step LoRA · 1.0', index)
        self.assertIn('const accelerated = selectedExecutionMode() === "turbo-lora";', app_js)
        self.assertIn('accelerated ? "8"', app_js)
        self.assertIn('music3 || accelerated || digitalHuman', app_js)
        self.assertIn('selectedExecutionMode() === "turbo-lora" ? 8', app_js)
        self.assertIn("H3_COMFY_TURBO_WORKFLOW", deployment)
        self.assertIn("H3_COMFY_REF2VA_TURBO_WORKFLOW", deployment)

    def test_digital_human_frontend_contract(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")
        environment = (project_root / ".env.example").read_text(encoding="utf-8")

        self.assertIn('option value="digital-human">数字人 · 音频驱动', index)
        self.assertIn('/assets/app.js?v=54', index)
        self.assertIn('return { image: 1, video: 0, audio: 1 };', app_js)
        self.assertIn('el("duration").disabled = digitalHuman;', app_js)
        self.assertIn('durationControl.classList.toggle("digital-human", digitalHuman);', app_js)
        self.assertIn('视频长度由驱动音频长度决定', index)
        self.assertIn('class="control-tooltip"', index)
        self.assertIn('el("durationHint").hidden = !digitalHuman;', app_js)
        self.assertIn('music3 || accelerated || digitalHuman', app_js)
        self.assertIn("H3_COMFY_DIGITAL_HUMAN_WORKFLOW", environment)

    def test_tts_frontend_and_prompt_contract(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('option value="tts">H3 TTS · 人物语音', index)
        self.assertIn('setText(\'#executionMode option[value="tts"]\', "H3 TTS · character voice")', app_js)
        self.assertIn('const [width, height] = isTTS() ? [32, 32] : getDimensions();', app_js)
        self.assertIn('return { image: 0, video: 0, audio: 3 };', app_js)
        self.assertIn('data-asset-input', app_js)
        self.assertIn('data-job-action="input"', app_js)
        self.assertIn('application/x-h3-asset-job', app_js)
        self.assertIn('id="reuseOutputAssetDetail"', index)
        for heading in (
            "subject_definitions:",
            "summary:",
            "retention_analysis:",
            "detailed_description:",
            "overall_soundscape:",
            "non_diegetic_music:",
        ):
            self.assertIn(heading, TTS_SYSTEM_PROMPT)
        self.assertIn("<Audio N>", TTS_SYSTEM_PROMPT)
        self.assertIn("<d>[语言]", TTS_SYSTEM_PROMPT)

    def test_tts_workflow_is_audio_only(self):
        engine = ComfyUIH3Engine(Settings())
        workflow = engine._load_workflow("ref2va-fp8", "tts")
        self.assertEqual(workflow["92"]["class_type"], "SaveAudio")
        self.assertEqual(workflow["92"]["inputs"]["audio"], ["121", 0])
        self.assertEqual(workflow["121"]["class_type"], "VAEDecodeAudio")
        self.assertNotIn("122", workflow)
        self.assertNotIn("130", workflow)
        job = {
            "id": "tts-test",
            "request": {
                "model_variant": "ref2va-fp8",
                "execution_mode": "tts",
                "prompt": "A warm adult voice speaks a short dialogue.",
                "width": 864,
                "height": 480,
                "num_frames": 124,
                "steps": 20,
                "seed": 789,
                "references": [{"type": "audio"}, {"type": "audio"}],
            },
        }
        built = engine._build_workflow(
            job,
            [
                "minimax-h3-api/tts-test/01_audio.wav",
                "minimax-h3-api/tts-test/02_audio.wav",
            ],
        )
        self.assertEqual(built["136"]["inputs"]["width"], 32)
        self.assertEqual(built["136"]["inputs"]["height"], 32)
        self.assertEqual(built["136"]["inputs"]["ref_audios.ref_audio_0"], ["200", 0])
        self.assertEqual(built["136"]["inputs"]["ref_audios.ref_audio_1"], ["201", 0])
        zero_sample_job = {
            "id": "tts-zero-sample-test",
            "request": {
                **job["request"],
                "prompt": "Generate an adult female voice from the described traits.",
                "references": [],
            },
        }
        zero_sample = engine._build_workflow(zero_sample_job, [])
        self.assertEqual(zero_sample["136"]["inputs"]["width"], 32)
        self.assertFalse(any(key.startswith("ref_audios.") for key in zero_sample["136"]["inputs"]))

    def test_music3_frontend_contract(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('option value="music3-int8"', index)
        self.assertIn('option value="music3" id="music3ExecutionOption"', index)
        self.assertIn('id="lyrics"', index)
        self.assertIn("MUSIC3_DURATIONS = [30, 60, 120, 180, 240, 300]", app_js)
        self.assertIn('data.append("lyrics"', app_js)
        self.assertIn('<option value="music3-int8">Music3 INT8</option>', index)
        self.assertIn('id="comfyNode"', index)
        self.assertIn('data.append("comfy_node"', app_js)
        self.assertIn('new EventSource(`/api/v1/events?since=', app_js)
        self.assertIn('function applyJobUpsert(job)', app_js)
        self.assertNotIn('await Promise.all([loadAssets(), refreshConversation(), checkHealth()])', app_js)
        self.assertIn('id="writeLyrics"', index)
        self.assertIn('id="optimizePromptLabel"', index)
        self.assertIn('music3 ? "优化曲风" : tts ? "优化 TTS 对话提示词" : "优化提示词"', app_js)
        self.assertIn('id="mentionTrigger"', index)
        self.assertIn('data-mention-reference', app_js)
        self.assertIn('insertReferenceMention', app_js)
        self.assertIn('function textareaCaretRect(textarea)', app_js)
        self.assertIn('function handleMentionKeydown(event)', app_js)
        self.assertIn('max-height: min(320px, 48dvh)', (project_root / "static" / "styles.css").read_text(encoding="utf-8"))
        self.assertIn('async function assistMusic(task)', app_js)
        self.assertIn('fetch("/api/v1/music/assist"', app_js)
        self.assertIn('assistMusic("arrangement")', app_js)
        self.assertIn('assistMusic("lyrics")', app_js)

    def test_music3_assistant_prompts_follow_caption_contract(self):
        arrangement = MUSIC3_ARRANGEMENT_SYSTEM_PROMPT
        lyrics = MUSIC3_LYRICS_SYSTEM_PROMPT
        for heading in ("### Global Metadata", "### Vocal Details", "### Arrangement"):
            self.assertIn(heading, arrangement)
        self.assertIn("Never quote, paraphrase, summarize, translate, or reproduce lyric lines", arrangement)
        self.assertIn("For an instrumental request, return only [Instrumental]", lyrics)
        self.assertIn("[Verse]", lyrics)
        self.assertIn("[Chorus]", lyrics)
        self.assertNotIn("### Arrangement", lyrics)

    def test_nsfw_frontend_option_is_incognito_only(self):
        project_root = Path(__file__).resolve().parents[1]
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('value="h3-nsfw" id="nsfwExecutionOption" hidden disabled', index)
        self.assertIn('nsfwOption.hidden = !state.incognito;', app_js)
        self.assertIn('nsfwOption.disabled = !state.incognito;', app_js)

    def test_frontend_keeps_prompt_assets_and_hides_optimization_messages(self):
        project_root = Path(__file__).resolve().parents[1]
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("state.optimizations", app_js)
        self.assertNotIn("renderOptimization", app_js)
        self.assertIn("if (state.editingJobId) resetComposer();", app_js)
        self.assertIn('class="message-asset"', app_js)
        self.assertIn("scope: jobScope()", app_js)

    def test_expired_incognito_job_is_removed_during_restore(self):
        with TemporaryDirectory() as temp:
            data_dir = Path(temp) / "data"
            jobs_dir = data_dir / "jobs"
            upload_dir = data_dir / "uploads" / "expired"
            output_dir = data_dir / "outputs"
            jobs_dir.mkdir(parents=True)
            upload_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            upload = upload_dir / "01_image.png"
            result = output_dir / "expired.mp4"
            sidecar = result.with_suffix(".json")
            upload.write_bytes(b"image")
            result.write_bytes(b"video")
            sidecar.write_text("{}", encoding="utf-8")
            job_path = jobs_dir / "expired.json"
            job_path.write_text(
                """{
  "id": "expired",
  "status": "completed",
  "request": {"prompt": "secret prompt", "incognito": true},
  "input_paths": ["%s"],
  "result_path": "%s",
  "expires_at": "2000-01-01T00:00:00+00:00"
}""" % (upload, result),
                encoding="utf-8",
            )

            store = JobStore(jobs_dir)

            self.assertIsNone(store.get("expired"))
            self.assertFalse(job_path.exists())
            self.assertFalse(upload_dir.exists())
            self.assertFalse(result.exists())
            self.assertFalse(sidecar.exists())

    def test_cancelled_incognito_job_receives_expiry(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "data" / "jobs"
            jobs_dir.mkdir(parents=True)
            store = JobStore(jobs_dir)
            store.create(
                {
                    "id": "cancel-secret",
                    "title": "secret",
                    "status": "queued",
                    "stage": "queued",
                    "progress": 0,
                    "created_at": "2026-08-05T00:00:00+00:00",
                    "request": {"prompt": "secret prompt", "incognito": True},
                }
            )
            manager = JobManager(store, lambda: None)
            manager.submit("cancel-secret")
            try:
                self.assertTrue(manager.cancel("cancel-secret"))
                job = store.get("cancel-secret")
                self.assertEqual(job["status"], "cancelled")
                self.assertIsNotNone(job.get("expires_at"))
            finally:
                manager.stop()

    def test_incognito_activity_is_anonymous_in_logs_and_queue(self):
        with TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "data" / "jobs"
            jobs_dir.mkdir(parents=True)
            store = JobStore(jobs_dir)
            store.create(
                {
                    "id": "public-job",
                    "title": "public title",
                    "status": "queued",
                    "stage": "等待执行",
                    "progress": 0,
                    "created_at": "2026-08-05T00:00:00+00:00",
                    "request": {"prompt": "public prompt", "incognito": False},
                }
            )
            store.create(
                {
                    "id": "secret-job",
                    "title": "secret title",
                    "status": "queued",
                    "stage": "等待执行",
                    "progress": 0,
                    "created_at": "2026-08-05T00:01:00+00:00",
                    "request": {
                        "prompt": "secret prompt",
                        "execution_mode": "h3-nsfw",
                        "incognito": True,
                    },
                }
            )
            store.update(
                "secret-job",
                status="running",
                stage="包含隐私信息的内部执行阶段",
                progress=47,
            )

            public_logs = store.logs(100)
            serialized_logs = str(public_logs)
            self.assertNotIn("secret-job", serialized_logs)
            self.assertNotIn("secret prompt", serialized_logs)
            self.assertNotIn("h3-nsfw", serialized_logs)
            self.assertNotIn("包含隐私信息的内部执行阶段", serialized_logs)
            self.assertEqual(public_logs[-1]["message"], "有任务正在运行中")
            self.assertNotIn("job_id", public_logs[-1])
            self.assertNotIn("progress", public_logs[-1])

            manager = JobManager(store, lambda: None)
            manager._running_job_id = "secret-job"
            snapshot = manager.queue_snapshot()
            self.assertEqual(len(snapshot), 1)
            self.assertEqual(snapshot[0]["status"], "running")
            self.assertEqual(snapshot[0]["stage"], "有任务正在运行中")
            self.assertEqual(snapshot[0]["queue_position"], 0)
            self.assertIsInstance(snapshot[0]["elapsed_seconds"], float)
            self.assertNotIn("id", snapshot[0])
            self.assertNotIn("title", snapshot[0])
            self.assertNotIn("request", snapshot[0])
            self.assertNotIn("progress", snapshot[0])

            with patch("app.jobs.logger.info") as log_info:
                self.assertTrue(store.delete("secret-job"))
            log_info.assert_not_called()

    def test_frontend_renders_anonymous_activity_without_details(self):
        project_root = Path(__file__).resolve().parents[1]
        app_js = (project_root / "static" / "app.js").read_text(encoding="utf-8")
        index = (project_root / "static" / "index.html").read_text(encoding="utf-8")
        run_sh = (project_root / "run.sh").read_text(encoding="utf-8")

        self.assertIn("function isAnonymousQueueJob(job)", app_js)
        self.assertIn('"有任务正在运行中"', app_js)
        self.assertIn('const progress = item.progress == null ? ""', app_js)
        self.assertIn('/assets/app.js?v=54', index)
        self.assertIn('/assets/styles.css?v=42', index)
        self.assertIn('id="steps" name="steps" type="number"', index)
        self.assertIn('min="4" max="50" step="1" value="10"', index)
        self.assertNotIn('<select id="steps"', index)
        styles = (project_root / "static" / "styles.css").read_text(encoding="utf-8")
        self.assertIn('input[type="number"]::-webkit-inner-spin-button', styles)
        self.assertIn("--no-access-log", run_sh)

    def test_frame_alignment(self):
        for duration in range(1, 16):
            frames = align_frames(duration)
            self.assertGreaterEqual(frames, round(duration * 24))
            self.assertEqual(frames % 17, 5)

    def test_comfy_workflow_parameters_and_optional_last_frame(self):
        project_root = Path(__file__).resolve().parents[1]
        local_workflow = (
            project_root.parent.parent
            / "minimax-h3-comfyui"
            / "minimax_h3_fl2va_fp8_720p_15s_api.json"
        )
        workflow_path = local_workflow if local_workflow.exists() else Settings().comfy_workflow
        engine = ComfyUIH3Engine(Settings(comfy_workflow=workflow_path))
        job = {
            "id": "test-job",
            "request": {
                "model_variant": "fl2va-fp8",
                "prompt": "test prompt",
                "width": 864,
                "height": 480,
                "num_frames": 124,
                "steps": 30,
                "seed": 123,
            },
        }

        first_frame = engine._build_workflow(job, ["minimax-h3-api/test-job/01.png"])
        self.assertNotIn("last_frame", first_frame["136"]["inputs"])
        self.assertEqual(first_frame["124"]["inputs"]["steps"], 30)
        self.assertEqual(first_frame["129"]["inputs"]["noise_seed"], 123)
        self.assertEqual(first_frame["136"]["inputs"]["length"], 124)

        first_last = engine._build_workflow(
            job,
            ["minimax-h3-api/test-job/01.png", "minimax-h3-api/test-job/02.png"],
        )
        self.assertEqual(first_last["136"]["inputs"]["last_frame"], ["139", 0])
        self.assertEqual(
            first_last["139"]["inputs"]["image"],
            "minimax-h3-api/test-job/02.png",
        )

    def test_ref2va_workflow_supports_all_reference_types(self):
        project_root = Path(__file__).resolve().parents[1]
        local_workflow = (
            project_root.parent.parent
            / "minimax-h3-comfyui"
            / "minimax_h3_ref2va_fp8_scaled_api.json"
        )
        workflow_path = (
            local_workflow
            if local_workflow.exists()
            else Settings().comfy_ref2va_workflow
        )
        engine = ComfyUIH3Engine(Settings(comfy_ref2va_workflow=workflow_path))
        job = {
            "id": "ref2va-test",
            "request": {
                "model_variant": "ref2va-fp8",
                "prompt": "use every supplied reference",
                "width": 864,
                "height": 480,
                "num_frames": 22,
                "steps": 20,
                "seed": 456,
                "references": [
                    {"type": "image"},
                    {"type": "video", "has_audio": True},
                    {"type": "video", "has_audio": False},
                    {"type": "audio"},
                ],
            },
        }
        names = [
            "minimax-h3-api/ref2va-test/01_image.png",
            "minimax-h3-api/ref2va-test/02_video.mp4",
            "minimax-h3-api/ref2va-test/03_video.mp4",
            "minimax-h3-api/ref2va-test/04_audio.wav",
        ]

        workflow = engine._build_workflow(job, names)
        inputs = workflow["136"]["inputs"]
        self.assertEqual(workflow["127"]["inputs"]["unet_name"], "minimax_h3_ref2va_pruned_fp8_scaled.safetensors")
        self.assertEqual(inputs["ref_images.ref_image_0"], ["200", 0])
        self.assertEqual(inputs["ref_videos.ref_video_0"], ["201", 0])
        self.assertEqual(inputs["ref_video_audios.ref_video_audio_0"], ["201", 2])
        self.assertEqual(inputs["ref_videos.ref_video_1"], ["202", 0])
        self.assertNotIn("ref_video_audios.ref_video_audio_1", inputs)
        self.assertEqual(inputs["ref_audios.ref_audio_0"], ["203", 0])
        self.assertEqual(workflow["201"]["inputs"]["force_rate"], 24)
        self.assertEqual(workflow["201"]["inputs"]["frame_load_cap"], 360)

    def test_digital_human_workflow_uses_source_audio(self):
        engine = ComfyUIH3Engine(Settings())
        job = {
            "id": "digital-human-test",
            "request": {
                "model_variant": "ref2va-fp8",
                "execution_mode": "digital-human",
                "prompt": "人物面对镜头自然说话，保持固定机位。",
                "width": 864,
                "height": 480,
                "num_frames": 209,
                "steps": 20,
                "seed": 789,
                "references": [{"type": "audio"}, {"type": "image"}],
            },
        }
        names = [
            "minimax-h3-api/digital-human-test/01_audio.wav",
            "minimax-h3-api/digital-human-test/02_image.png",
        ]

        workflow = engine._build_workflow(job, names)

        self.assertEqual(workflow["137"]["inputs"]["image"], names[1])
        self.assertEqual(workflow["171"]["inputs"]["audio"], names[0])
        self.assertEqual(workflow["136"]["inputs"]["ref_images.ref_image_0"], ["137", 0])
        self.assertEqual(workflow["136"]["inputs"]["ref_audios.ref_audio_0"], ["171", 0])
        self.assertIn("<Picture 1>", workflow["136"]["inputs"]["prompt"])
        self.assertIn("<Audio 1>", workflow["136"]["inputs"]["prompt"])
        self.assertIn(job["request"]["prompt"], workflow["136"]["inputs"]["prompt"])
        self.assertEqual(workflow["172"]["inputs"]["source_audio"], ["171", 0])
        self.assertEqual(workflow["130"]["inputs"]["audio"], ["172", 1])

    def test_music3_workflow_uses_description_lyrics_and_duration(self):
        engine = ComfyUIH3Engine(Settings())
        job = {
            "id": "music3-test",
            "request": {
                "model_variant": "music3-int8",
                "execution_mode": "music3",
                "prompt": "Mandarin synth-pop with bright female vocals.",
                "lyrics": "[Verse]\nCity lights\n\n[Chorus]\nRun into dawn",
                "duration": 120,
                "steps": 30,
                "seed": 1234,
                "references": [],
            },
            "input_paths": [],
        }

        workflow = engine._build_workflow(job, [], "cuda:1")

        self.assertEqual(workflow["13"]["inputs"]["caption"], job["request"]["prompt"])
        self.assertEqual(workflow["13"]["inputs"]["lyrics"], job["request"]["lyrics"])
        self.assertEqual(workflow["13"]["inputs"]["max_duration"], 120)
        self.assertTrue(workflow["13"]["inputs"]["force_duration"])
        self.assertEqual(workflow["13"]["inputs"]["seed"], 1234)
        self.assertEqual(workflow["9"]["inputs"]["seed"], 1234)
        self.assertEqual(workflow["92"]["inputs"]["filename_prefix"], "minimax-h3-api/music3-test")
        self.assertEqual(workflow["3"]["inputs"]["device"], "cuda:1")

    def test_music3_uses_cuda_device_reported_by_selected_comfy_node(self):
        stats = {
            "devices": [
                {"name": "cuda:1 NVIDIA GeForce RTX 4090", "type": "cuda", "index": 1}
            ]
        }
        self.assertEqual(ComfyUIH3Engine._comfy_cuda_device(stats), "cuda:1")
        with self.assertRaisesRegex(RuntimeError, "未报告 CUDA 设备"):
            ComfyUIH3Engine._comfy_cuda_device(
                {"devices": [{"name": "cpu", "type": "cpu", "index": 0}]}
            )

    def test_generation_and_reference_limits(self):
        for duration in (1, 15):
            for steps in (4, 10, 50):
                validate_generation(608, 352, duration, steps)
        for duration in (0.99, 15.01):
            with self.assertRaises(HTTPException):
                validate_generation(608, 352, duration, 20)
        for steps in (3, 51):
            with self.assertRaises(HTTPException):
                validate_generation(608, 352, 5, steps)
        validate_generation(608, 352, 5, 8, "turbo-lora")
        for steps in (4, 10, 50):
            with self.assertRaises(HTTPException):
                validate_generation(608, 352, 5, steps, "turbo-lora")
        validate_generation(608, 352, 5, 20, "digital-human")
        for steps in (8, 19, 21):
            with self.assertRaises(HTTPException):
                validate_generation(608, 352, 5, steps, "digital-human")
        validate_generation(0, 0, 300, 30, "music3")
        for duration, steps in ((0.99, 30), (300.01, 30), (60, 29)):
            with self.assertRaises(HTTPException):
                validate_generation(0, 0, duration, steps, "music3")
        validate_references("music3-int8", [], "music3")
        with self.assertRaises(HTTPException):
            validate_references("music3-int8", ["audio"], "music3")
        validate_references("ref2va-fp8", [], "tts")
        validate_references("ref2va-fp8", ["audio"] * 3, "tts")
        with self.assertRaises(HTTPException):
            validate_references("ref2va-fp8", ["audio"] * 4, "tts")
        validate_references(
            "ref2va-fp8",
            ["image"] * 9 + ["video"] * 3 + ["audio"] * 3,
        )
        for kinds in (["image"] * 10, ["video"] * 4, ["audio"] * 4):
            with self.assertRaises(HTTPException):
                validate_references("ref2va-fp8", kinds)
        validate_references("fl2va-fp8", ["image"])
        validate_references("fl2va-fp8", ["image", "image"])
        with self.assertRaises(HTTPException):
            validate_references("fl2va-fp8", ["video"])
        validate_references("ref2va-fp8", ["image", "audio"], "digital-human")
        validate_references("ref2va-fp8", ["audio", "image"], "digital-human")
        for variant, kinds in (
            ("fl2va-fp8", ["image", "audio"]),
            ("ref2va-fp8", ["image"]),
            ("ref2va-fp8", ["image", "audio", "audio"]),
        ):
            with self.assertRaises(HTTPException):
                validate_references(variant, kinds, "digital-human")

    def test_comfy_result_becomes_api_managed_artifact(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "api"
            comfy_output = Path(temp) / "comfy-output"
            source = comfy_output / "minimax-h3-api" / "test-job_00001_.mp4"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"test-video")
            settings = Settings(root=root, comfy_output_dir=comfy_output)
            settings.ensure_directories()
            engine = ComfyUIH3Engine(settings)
            history = {
                "status": {"completed": True, "status_str": "success"},
                "outputs": {
                    "92": {
                        "images": [
                            {
                                "filename": source.name,
                                "subfolder": "minimax-h3-api",
                                "type": "output",
                            }
                        ]
                    }
                },
            }

            result = engine._copy_result(
                {"id": "test-job", "request": {"prompt": "test prompt"}},
                history,
            )

            self.assertEqual(result.read_bytes(), b"test-video")
            self.assertFalse(source.exists())

    def test_music3_result_becomes_api_managed_flac(self):
        with TemporaryDirectory() as temp:
            root = Path(temp) / "api"
            comfy_output = Path(temp) / "comfy-output"
            source = comfy_output / "minimax-h3-api" / "music3-test_00001_.flac"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"test-flac")
            settings = Settings(root=root, comfy_output_dir=comfy_output)
            settings.ensure_directories()
            engine = ComfyUIH3Engine(settings)
            history = {
                "status": {"completed": True, "status_str": "success"},
                "outputs": {
                    "92": {
                        "audio": [
                            {
                                "filename": source.name,
                                "subfolder": "minimax-h3-api",
                                "type": "output",
                            }
                        ]
                    }
                },
            }
            job = {
                "id": "music3-test",
                "request": {"model_variant": "music3-int8", "prompt": "test"},
            }

            result = engine._copy_result(job, history)

            self.assertEqual(result.suffix, ".flac")
            self.assertEqual(result.read_bytes(), b"test-flac")
            self.assertFalse(source.exists())
            self.assertTrue(result.with_suffix(".json").exists())

    def test_comfy_engine_releases_vram_after_each_job(self):
        engine = ComfyUIH3Engine(Settings(comfy_url="http://comfy.test:8188"))

        with patch("httpx.Client") as client_class:
            client = client_class.return_value.__enter__.return_value
            engine._release_vram()

        client_class.assert_called_once()
        client.post.assert_called_once_with(
            "/free",
            json={"unload_models": True, "free_memory": True},
        )
        client.post.return_value.raise_for_status.assert_called_once_with()

        with (
            patch("httpx.Client", side_effect=RuntimeError("connection failed")),
            patch("app.engine.logger.exception") as log_exception,
        ):
            engine._release_vram()
        log_exception.assert_called_once_with("ComfyUI VRAM 释放失败")

        with (
            patch.object(engine, "_upload_inputs", side_effect=RuntimeError("prepare failed")),
            patch("httpx.Client") as client_class,
            patch.object(engine, "_release_vram") as release_vram,
            self.assertRaisesRegex(RuntimeError, "prepare failed"),
        ):
            client = client_class.return_value.__enter__.return_value
            client.get.return_value.json.return_value = {}
            engine.generate(
                {"id": "failed-job"},
                lambda _percent, _stage: None,
                lambda: False,
            )
        release_vram.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
