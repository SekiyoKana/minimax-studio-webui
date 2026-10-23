import json
import threading
import tempfile
import time
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import HTTPException

import app.main as main_module
from app.engine import ComfyUIH3Engine
from app.jobs import JobManager, JobStore
from app.nodes import ComfyNodeConfig
from app.nodes import NodeRegistry
from app.settings import Settings
from app.workflows import WorkflowRegistry, validate_workflow_config


def sample_workflow():
    return {
        "1": {"class_type": "CLIPTextEncode", "inputs": {"text": "default"}},
        "2": {"class_type": "SaveVideo", "inputs": {"video": ["1", 0], "filename_prefix": "output"}},
    }


class WorkflowTests(unittest.TestCase):
    def test_preset_snapshot_keeps_the_turbo_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = Settings(root=root, comfy_output_dir=root / "remote-output")
            settings.ensure_directories()
            registry = WorkflowRegistry(
                root / "data" / "config.db",
                Path(__file__).resolve().parents[1] / "workflows",
            )
            preset = registry.get("preset-fl2va-turbo")
            snapshot = {
                "source": "preset",
                "workflow_json": deepcopy(preset["workflow_json"]),
                "media_type": "video",
            }
            job = {
                "id": "turbo-job",
                "workflow_snapshot": snapshot,
                "request": {
                    "prompt": "turbo",
                    "model_variant": "fl2va-fp8",
                    "execution_mode": "turbo-lora",
                    "width": 608,
                    "height": 352,
                    "duration": 5,
                    "num_frames": 124,
                    "steps": 8,
                    "seed": 1,
                    "references": [],
                },
                "input_paths": [],
            }
            engine = ComfyUIH3Engine(
                settings,
                ComfyNodeConfig("node", "Node", "http://comfy.test:8188"),
                workflow_registry=registry,
            )
            built = engine._build_workflow(job, ["first.png"])
            self.assertEqual(built["124"]["inputs"]["steps"], 8)
            self.assertEqual(
                built["142"]["inputs"]["lora_name"],
                "minimax_h3_fl2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors",
            )

    def test_engine_loads_preset_from_database_before_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = Settings(root=root, comfy_workflow=root / "missing.json")
            registry = WorkflowRegistry(
                root / "data" / "config.db",
                Path(__file__).resolve().parents[1] / "workflows",
            )
            engine = ComfyUIH3Engine(settings, workflow_registry=registry)
            workflow = engine._load_workflow("fl2va-fp8", "native")
            self.assertIn("92", workflow)
            self.assertEqual(workflow, registry.get("preset-fl2va-native")["workflow_json"])

    def test_slot_reference_limits_follow_media_type(self):
        workflow = {
            "reference_mappings": [
                {"type": "image", "index": 1, "node_id": "44", "input": "ref_images", "slot": True, "required": True},
                {"type": "video", "index": 1, "node_id": "44", "input": "ref_videos", "slot": True, "required": True},
                {"type": "audio", "index": 1, "node_id": "44", "input": "ref_audios", "slot": True, "required": True},
            ]
        }
        main_module.validate_custom_reference_mappings(
            workflow,
            ["image"] * 9 + ["video"] * 3 + ["audio"] * 3,
        )
        for kinds, detail in (
            (["image"] * 10, "9 份"),
            (["image"] * 1 + ["video"] * 4, "3 份"),
            (["image"] * 1 + ["audio"] * 4, "3 份"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                main_module.validate_custom_reference_mappings(workflow, kinds)
            self.assertIn(detail, str(ctx.exception.detail))

    def test_slot_binding_requires_one_file_per_family(self):
        workflow = {
            "reference_mappings": [
                {"type": "image", "index": 3, "node_id": "44", "input": "ref_images", "slot": True, "required": True}
            ]
        }
        main_module.validate_custom_reference_mappings(workflow, ["image"])
        with self.assertRaises(HTTPException) as ctx:
            main_module.validate_custom_reference_mappings(workflow, [])
        self.assertIn("至少 1 个 image", str(ctx.exception.detail))

    def test_mapping_validation_rejects_connected_inputs_and_accepts_static_values(self):
        graph = sample_workflow()
        config = validate_workflow_config(
            name="测试工作流",
            workflow_json=graph,
            field_mappings={"prompt": {"node_id": "1", "input": "text"}},
            reference_mappings=[],
            static_inputs={},
            result_node_id="2",
            media_type="video",
        )
        self.assertEqual(config["field_mappings"]["prompt"]["node_id"], "1")
        with self.assertRaisesRegex(ValueError, "已连接"):
            validate_workflow_config(
                name="错误工作流",
                workflow_json=graph,
                field_mappings={"prompt": {"node_id": "2", "input": "video"}},
                reference_mappings=[],
                static_inputs={},
                result_node_id="2",
                media_type="video",
            )

    def test_mapping_validation_accepts_ratio_and_megapixels(self):
        graph = sample_workflow()
        graph["1"]["inputs"].update({"ratio": "16:9", "megapixels": 0.4})
        config = validate_workflow_config(
            name="画幅工作流",
            workflow_json=graph,
            field_mappings={
                "prompt": {"node_id": "1", "input": "text"},
                "ratio": {"node_id": "1", "input": "ratio"},
                "megapixels": {"node_id": "1", "input": "megapixels"},
            },
            reference_mappings=[],
            static_inputs={},
            result_node_id="2",
            media_type="video",
        )
        self.assertEqual(config["field_mappings"]["ratio"]["input"], "ratio")
        self.assertEqual(config["field_mappings"]["megapixels"]["input"], "megapixels")
        with self.assertRaisesRegex(ValueError, "不支持的字段"):
            validate_workflow_config(
                name="未知字段工作流",
                workflow_json=graph,
                field_mappings={"guidance": {"node_id": "1", "input": "text"}},
                reference_mappings=[],
                static_inputs={},
                result_node_id="2",
                media_type="video",
            )

    def test_registry_seeds_presets_and_custom_crud_is_persistent(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "config.db"
            registry = WorkflowRegistry(database, Path(__file__).parents[1] / "workflows")
            self.assertEqual(len(registry.list()), 15)
            self.assertIsNone(registry.get("preset-fl2va-turbo-4step"))
            self.assertIsNone(registry.get("preset-ref2va-turbo-4step"))
            created = registry.create(
                validate_workflow_config(
                    name="自定义工作流",
                    workflow_json=sample_workflow(),
                    field_mappings={"prompt": {"node_id": "1", "input": "text"}},
                    reference_mappings=[],
                    static_inputs={},
                    result_node_id="2",
                    media_type="video",
                ),
                ["node-1"],
                True,
            )
            self.assertEqual(registry.get(created["id"])["source"], "custom")
            self.assertTrue(registry.set_preset_visibility("preset-fl2va-native", False))
            with self.assertRaisesRegex(ValueError, "不能删除"):
                registry.delete("preset-fl2va-native")
            reopened = WorkflowRegistry(database, Path(__file__).parents[1] / "workflows")
            self.assertFalse(reopened.get("preset-fl2va-native")["visible_in_composer"])
            self.assertEqual(reopened.get(created["id"])["name"], "自定义工作流")

    def test_sync_uploads_and_verifies_remote_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = WorkflowRegistry(Path(temp) / "config.db", Path(__file__).parents[1] / "workflows")
            created = registry.create(
                validate_workflow_config(
                    name="同步工作流",
                    workflow_json=sample_workflow(),
                    field_mappings={},
                    reference_mappings=[],
                    static_inputs={},
                    result_node_id="2",
                    media_type="video",
                ),
                ["node-1"],
                True,
            )
            payload = registry.workflow_bytes(created)
            response = MagicMock(status_code=200, content=payload)
            response.raise_for_status.return_value = None
            client = MagicMock()
            client.__enter__.return_value = client
            client.post.return_value = response
            client.get.return_value = response
            node = ComfyNodeConfig("node-1", "Node", "http://comfy.test:8188")
            with patch("app.workflows.httpx.Client", return_value=client):
                result = registry.synchronize(created["id"], node)
            self.assertEqual(result["status"], "synced")
            self.assertEqual(registry.sync_rows(created["id"])[0]["status"], "synced")

    def test_sync_url_percent_encodes_directory_separator(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = WorkflowRegistry(Path(temp) / "config.db", Path(__file__).parents[1] / "workflows")
            created = registry.create(
                validate_workflow_config(
                    name="编码路径工作流",
                    workflow_json=sample_workflow(),
                    field_mappings={},
                    reference_mappings=[],
                    static_inputs={},
                    result_node_id="2",
                    media_type="video",
                ),
                ["node-1"],
                True,
            )
            payload = registry.workflow_bytes(created)
            response = MagicMock(status_code=200, content=payload)
            response.raise_for_status.return_value = None
            client = MagicMock()
            client.__enter__.return_value = client
            client.post.return_value = response
            client.get.return_value = response
            client.delete.return_value = MagicMock(status_code=204)
            node = ComfyNodeConfig("node-1", "Node", "http://comfy.test:8188")
            filename = registry.remote_filename(created["id"])
            with patch("app.workflows.httpx.Client", return_value=client):
                registry.synchronize(created["id"], node)
                registry.remove_remote_copy(created["id"], node)
            expected = f"http://comfy.test:8188/userdata/workflows%2F{filename}"
            self.assertEqual(client.post.call_args[0][0], f"{expected}?overwrite=true")
            self.assertEqual(client.get.call_args[0][0], expected)
            self.assertEqual(client.delete.call_args[0][0], expected)

    def test_manual_sync_verification_records_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            registry = WorkflowRegistry(Path(temp) / "config.db", Path(__file__).parents[1] / "workflows")
            created = registry.create(
                validate_workflow_config(
                    name="手动校验工作流",
                    workflow_json=sample_workflow(),
                    field_mappings={},
                    reference_mappings=[],
                    static_inputs={},
                    result_node_id="2",
                    media_type="video",
                ),
                ["node-1"],
                True,
            )
            response = MagicMock(status_code=200, content=b"different workflow")
            response.raise_for_status.return_value = None
            client = MagicMock()
            client.__enter__.return_value = client
            client.get.return_value = response
            node = ComfyNodeConfig("node-1", "Node", "http://comfy.test:8188")
            with patch("app.workflows.httpx.Client", return_value=client):
                result = registry.synchronize(created["id"], node, confirm=True)
            client.post.assert_not_called()
            self.assertEqual(result["status"], "failed")
            self.assertIn("哈希不一致", result["error"])

    def test_job_manager_limits_custom_workflow_to_its_target_nodes(self):
        with tempfile.TemporaryDirectory() as temp:
            jobs_dir = Path(temp) / "jobs"
            jobs_dir.mkdir()
            store = JobStore(jobs_dir)
            store.create({
                "id": "targeted-job",
                "status": "queued",
                "request": {"comfy_node": "auto", "workflow_node_ids": ["node-a"]},
            })
            manager = JobManager(
                store,
                lambda node: object(),
                nodes=[
                    {"id": "node-a", "name": "A", "url": "http://a", "provider": "comfyui"},
                    {"id": "node-b", "name": "B", "url": "http://b", "provider": "comfyui"},
                ],
            )
            manager._order.append("targeted-job")
            result = {}
            def claim_disallowed_node():
                claimed = manager._claim_job("node-b", 0)
                if claimed:
                    result["claim"] = claimed

            thread = threading.Thread(target=claim_disallowed_node)
            thread.start()
            time.sleep(0.05)
            manager._stop_event.set()
            with manager._condition:
                manager._condition.notify_all()
            thread.join(timeout=1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result, {})

            manager._stop_event.clear()
            claimed = manager._claim_job("node-a", 0)
            self.assertEqual(claimed[0], "targeted-job")

    def test_custom_workflow_build_and_result_copy_use_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = Settings(
                root=root,
                comfy_output_dir=root / "remote-output",
            )
            settings.ensure_directories()
            graph = {
                "1": {"class_type": "TextEncoder", "inputs": {"text": "default"}},
                "2": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output", "video": ["1", 0]}},
            }
            snapshot = {
                "source": "custom",
                "workflow_json": graph,
                "field_mappings": {
                    "prompt": {"node_id": "1", "input": "text"},
                    "steps": {"node_id": "1", "input": "steps"},
                    "ratio": {"node_id": "1", "input": "ratio"},
                    "megapixels": {"node_id": "1", "input": "megapixels"},
                },
                "reference_mappings": [],
                "static_inputs": {"1": {"preset": "fixed"}},
                "result_node_id": "2",
                "media_type": "video",
            }
            snapshot["workflow_json"]["1"]["inputs"]["steps"] = 1
            job = {
                "id": "custom-job",
                "workflow_snapshot": snapshot,
                "request": {
                    "prompt": "custom prompt",
                    "steps": 24,
                    "ratio": "9:16",
                    "megapixels": 0.5,
                    "references": [],
                    "media_type": "video",
                },
                "input_paths": [],
            }
            engine = ComfyUIH3Engine(settings, ComfyNodeConfig("node", "Node", "http://comfy.test:8188"))
            built = engine._build_workflow(job, [])
            self.assertEqual(built["1"]["inputs"]["text"], "custom prompt")
            self.assertEqual(built["1"]["inputs"]["ratio"], "9:16")
            self.assertEqual(built["1"]["inputs"]["megapixels"], 0.5)
            self.assertEqual(built["1"]["inputs"]["steps"], 24)
            self.assertEqual(built["1"]["inputs"]["preset"], "fixed")
            self.assertEqual(built["2"]["inputs"]["filename_prefix"], "minimax-studio-webui/custom-job")
            self.assertEqual(graph["1"]["inputs"]["text"], "default")

            remote_dir = settings.comfy_output_dir / "custom"
            remote_dir.mkdir(parents=True)
            source = remote_dir / "result.mp4"
            source.write_bytes(b"video")
            history = {
                "status": {"completed": True, "status_str": "success"},
                "outputs": {"2": {"videos": [{"filename": "result.mp4", "subfolder": "custom", "type": "output"}] }},
            }
            output = engine._copy_result(job, history)
            self.assertEqual(output.read_bytes(), b"video")
            self.assertEqual(output.suffix, ".mp4")

    def test_custom_workflow_combo_tokens_match_declared_options(self):
        class StubResponse:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "ResolutionSelector": {
                        "input": {
                            "required": {
                                "aspect_ratio": [
                                    "COMBO",
                                    {"options": ["1:1 (Square)", "16:9 (Widescreen)", "9:16 (Portrait Widescreen)"]},
                                ],
                                "megapixels": ["FLOAT", {"default": 0.4}],
                            }
                        }
                    }
                }

        class StubClient:
            def __init__(self):
                self.paths = []

            def get(self, path):
                self.paths.append(path)
                return StubResponse()

        engine = ComfyUIH3Engine(Settings(), ComfyNodeConfig("node", "Node", "http://comfy.test:8188"))
        workflow = {
            "7": {
                "class_type": "ResolutionSelector",
                "inputs": {"aspect_ratio": "16:9", "megapixels": 0.4, "multiple": 32},
            }
        }
        snapshot = {
            "field_mappings": {
                "ratio": {"node_id": "7", "input": "aspect_ratio"},
                "megapixels": {"node_id": "7", "input": "megapixels"},
            }
        }
        client = StubClient()
        engine._align_workflow_combo_values(client, workflow, snapshot)
        self.assertEqual(workflow["7"]["inputs"]["aspect_ratio"], "16:9 (Widescreen)")
        self.assertEqual(workflow["7"]["inputs"]["megapixels"], 0.4)
        self.assertEqual(workflow["7"]["inputs"]["multiple"], 32)
        self.assertEqual(client.paths, ["/object_info/ResolutionSelector"])

    def test_custom_workflow_stages_derive_generic_labels(self):
        workflow = {
            "13": {"class_type": "BasicScheduler", "inputs": {"steps": 8}},
            "9": {"class_type": "KSampler", "inputs": {"model": ["13", 0]}},
            "125": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0]}},
            "92": {"class_type": "SaveVideo", "inputs": {"video": ["125", 0]}},
            "7": {"class_type": "ResolutionSelector", "inputs": {"aspect_ratio": "16:9 (Widescreen)"}},
        }
        stages = ComfyUIH3Engine._custom_workflow_stages(workflow)
        self.assertEqual(set(stages), set(workflow))
        labels = {node: stage[1] for node, stage in stages.items()}
        self.assertEqual(labels["13"], "采样")
        self.assertEqual(labels["9"], "采样")
        self.assertEqual(labels["125"], "VAE 编解码")
        self.assertEqual(labels["92"], "保存结果")
        self.assertEqual(labels["7"], "准备参数")
        self.assertNotIn("编码音乐描述与歌词", labels.values())
        self.assertLess(stages["13"][0], stages["92"][0])
        self.assertGreaterEqual(stages["7"][0], 6)
        self.assertLessEqual(stages["92"][0], 96)
        self.assertEqual(ComfyUIH3Engine._custom_workflow_stages({}), {})

    def test_custom_workflow_waits_with_generic_stages(self):
        class StubResponse:
            def __init__(self, payload):
                self.payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class StubClient:
            def get(self, path):
                return StubResponse({"p": {"status": {"completed": True, "status_str": "success"}}})

        class StubSocket:
            def __init__(self, messages):
                self.messages = list(messages)

            def recv(self, timeout=None):
                return self.messages.pop(0)

        events = [
            {"type": "execution_start", "data": {"prompt_id": "p"}},
            {"type": "executing", "data": {"prompt_id": "p", "node": "13"}},
            {"type": "progress", "data": {"prompt_id": "p", "node": "9", "value": 3, "max": 10}},
            {"type": "executing", "data": {"prompt_id": "p", "node": "92"}},
            {"type": "execution_success", "data": {"prompt_id": "p"}},
        ]
        stages = ComfyUIH3Engine._custom_workflow_stages(
            {
                "13": {"class_type": "BasicScheduler", "inputs": {}},
                "9": {"class_type": "KSampler", "inputs": {"model": ["13", 0]}},
                "92": {"class_type": "SaveVideo", "inputs": {"video": ["9", 0]}},
            }
        )
        engine = ComfyUIH3Engine(Settings(), ComfyNodeConfig("node", "Node", "http://comfy.test:8188"))
        calls = []
        history = engine._wait_for_finished(
            StubSocket([json.dumps(event) for event in events]),
            StubClient(),
            "p",
            lambda percent, message: calls.append((percent, message)),
            lambda: False,
            False,
            stage_map=stages,
        )
        self.assertTrue(history["status"]["completed"])
        messages = [message for _, message in calls]
        self.assertEqual(messages[0], "ComfyUI 自定义工作流开始执行")
        self.assertEqual(messages[1], "采样")
        self.assertEqual(messages[2], "采样 3/10")
        self.assertIn("保存结果", messages)
        self.assertFalse(any("Music3" in message or "音乐" in message for message in messages))

    def test_custom_workflow_reference_slots_build_loader_nodes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            settings = Settings(root=root, comfy_output_dir=root / "remote-output")
            settings.ensure_directories()
            graph = {
                "44": {
                    "class_type": "MiniMaxH3ReferenceToVideo",
                    "inputs": {
                        "prompt": "default",
                        "ref_images.ref_image_0": ["40", 0],
                        "ref_videos.ref_video_0": ["50", 0],
                        "ref_video_audios.ref_video_audio_0": ["50", 2],
                    },
                },
                "40": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
                "50": {"class_type": "VHS_LoadVideo", "inputs": {"video": "old.mp4"}},
                "9": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "output", "video": ["44", 0]}},
            }
            snapshot = {
                "source": "custom",
                "workflow_json": graph,
                "field_mappings": {"prompt": {"node_id": "44", "input": "prompt"}},
                "reference_mappings": [
                    {"type": "image", "index": 1, "node_id": "44", "input": "ref_images", "slot": True, "required": True},
                    {"type": "image", "index": 2, "node_id": "44", "input": "ref_images", "slot": True, "required": True},
                    {"type": "video", "index": 1, "node_id": "44", "input": "ref_videos", "slot": True, "required": False},
                ],
                "static_inputs": {},
                "result_node_id": "9",
                "media_type": "video",
            }
            job = {
                "id": "slot-job",
                "workflow_snapshot": snapshot,
                "request": {
                    "prompt": "slot prompt",
                    "references": [
                        {"type": "image", "path": "a.png"},
                        {"type": "image", "path": "b.png"},
                        {"type": "image", "path": "c.png"},
                        {"type": "video", "path": "d.mp4"},
                    ],
                },
                "input_paths": [],
            }
            engine = ComfyUIH3Engine(settings, ComfyNodeConfig("node", "Node", "http://comfy.test:8188"))
            built = engine._build_workflow(job, ["h3_ref_a.png", "h3_ref_b.png", "h3_ref_c.png", "h3_ref_d.mp4"])
            inputs = built["44"]["inputs"]
            first = inputs["ref_images.ref_image_0"]
            second = inputs["ref_images.ref_image_1"]
            extra = inputs["ref_images.ref_image_2"]
            video = inputs["ref_videos.ref_video_0"]
            self.assertEqual(len({first[0], second[0], extra[0], video[0]}), 4)
            self.assertEqual(built[extra[0]]["class_type"], "LoadImage")
            self.assertEqual(built[extra[0]]["inputs"]["image"], "h3_ref_c.png")
            self.assertNotEqual(first[0], second[0])
            self.assertEqual(built[first[0]]["class_type"], "LoadImage")
            self.assertEqual(built[first[0]]["inputs"]["image"], "h3_ref_a.png")
            self.assertEqual(built[second[0]]["inputs"]["image"], "h3_ref_b.png")
            self.assertEqual(built[video[0]]["class_type"], "VHS_LoadVideo")
            self.assertEqual(built[video[0]]["inputs"]["video"], "h3_ref_d.mp4")
            self.assertEqual(inputs["ref_video_audios.ref_video_audio_0"], [video[0], 2])
            self.assertEqual(built["40"]["inputs"]["image"], "old.png")
            self.assertEqual(graph["44"]["inputs"]["ref_images.ref_image_0"], ["40", 0])


class WorkflowRouteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.node_registry = NodeRegistry(self.root / "config.db")
        self.workflow_registry = WorkflowRegistry(self.root / "config.db", Path(__file__).parents[1] / "workflows")
        (self.root / "jobs").mkdir()
        self.store = JobStore(self.root / "jobs")
        self.stack = patch.multiple(
            main_module,
            node_registry=self.node_registry,
            workflow_registry=self.workflow_registry,
            store=self.store,
        )
        self.stack.start()
        self.accepts_node = patch.object(main_module.manager, "accepts_node", side_effect=lambda node_id: node_id in {"auto", "local"})
        self.node_provider = patch.object(main_module.manager, "node_provider", return_value="comfyui")
        self.workflow_profile = patch.object(main_module.manager, "workflow_profile", return_value=None)
        self.submit = patch.object(main_module.manager, "submit", return_value=None)
        self.queue_position = patch.object(main_module.manager, "queue_position", return_value=None)
        self.sync = patch.object(main_module, "synchronize_workflow", new=AsyncMock(return_value=[]))
        self.remote_cleanup = patch.object(self.workflow_registry, "remove_remote_copy", return_value=None)
        for active_patch in (self.accepts_node, self.node_provider, self.workflow_profile, self.submit, self.queue_position, self.sync, self.remote_cleanup):
            active_patch.start()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main_module.app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        for active_patch in (self.accepts_node, self.node_provider, self.workflow_profile, self.submit, self.queue_position, self.sync, self.remote_cleanup):
            active_patch.stop()
        self.stack.stop()
        self.temp.cleanup()

    async def test_workflow_api_crud_and_preset_protection(self):
        config = {
            "name": "Custom",
            "workflow_json": sample_workflow(),
            "field_mappings": {"prompt": {"node_id": "1", "input": "text"}},
            "reference_mappings": [],
            "static_inputs": {},
            "result_node_id": "2",
            "media_type": "video",
            "target_node_ids": ["local"],
            "visible_in_composer": True,
        }
        created = await self.client.post("/api/v1/workflows", json=config)
        self.assertEqual(created.status_code, 201, created.text)
        workflow_id = created.json()["id"]
        listed = await self.client.get("/api/v1/workflows")
        self.assertTrue(any(item["id"] == workflow_id for item in listed.json()["data"]))
        preset_update = await self.client.patch("/api/v1/workflows/preset-fl2va-native", json={"visible_in_composer": False})
        self.assertEqual(preset_update.status_code, 200)
        preset_edit = await self.client.patch("/api/v1/workflows/preset-fl2va-native", json={"name": "Changed"})
        self.assertEqual(preset_edit.status_code, 409)
        update = await self.client.patch(f"/api/v1/workflows/{workflow_id}", json={"name": "Renamed"})
        self.assertEqual(update.status_code, 200, update.text)
        self.assertEqual(update.json()["name"], "Renamed")
        deleted = await self.client.delete(f"/api/v1/workflows/{workflow_id}")
        self.assertTrue(deleted.json()["deleted"])

    async def test_generation_request_uses_custom_workflow_id_and_keeps_snapshot_private(self):
        config = validate_workflow_config(
            name="Custom video",
            workflow_json=sample_workflow(),
            field_mappings={"prompt": {"node_id": "1", "input": "text"}},
            reference_mappings=[],
            static_inputs={},
            result_node_id="2",
            media_type="video",
        )
        workflow = self.workflow_registry.create(config, ["local"], True)
        self.workflow_registry.set_sync(workflow["id"], "local", status="synced")
        response = await self.client.post(
            "/api/v1/generations",
            data={
                "prompt": "a sufficiently detailed prompt",
                "workflow_id": workflow["id"],
                "comfy_node": "local",
                "reference_manifest": "[]",
            },
        )
        self.assertEqual(response.status_code, 202, response.text)
        request = response.json()["request"]
        self.assertEqual(request["workflow_id"], workflow["id"])
        self.assertEqual(request["workflow_name"], "Custom video")
        self.assertEqual(request["workflow_node_ids"], ["local"])
        self.assertNotIn("workflow_snapshot", response.json())
        stored = self.store.get(response.json()["id"])
        self.assertEqual(stored["workflow_snapshot"]["workflow_json"], sample_workflow())


if __name__ == "__main__":
    unittest.main()
