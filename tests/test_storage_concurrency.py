"""Controlled real-file races across stores, processes and HTTP requests."""
import hashlib
import json
import multiprocessing
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.server import LabHTTPServer
from network_core.storage import ProjectConflictError, ProjectStore
from test_model import example


def changed(label):
    document = example()
    document["nodes"][0]["label"] = label
    return document


def process_save(directory, label, expected, start, ready, at_replace, results):
    """Independent interpreter; align old implementations at replace()."""
    store = ProjectStore(Path(directory))
    real_replace = os.replace

    def aligned_replace(source, target):
        try:
            at_replace.wait(timeout=3)
        except threading.BrokenBarrierError:
            pass  # A correct lock lets only the first writer reach replace.
        return real_replace(source, target)

    ready.put(label)
    start.wait(timeout=8)
    try:
        with patch("network_core.storage.os.replace", side_effect=aligned_replace):
            saved = store.save("lab", changed(label), expected)
        results.put((label, "saved", saved["sha256"]))
    except ProjectConflictError as error:
        results.put((label, "conflict", error.actual_hash))


class ConcurrentStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def assert_single_winner(self, outcomes):
        self.assertEqual(sorted(outcome[1] for outcome in outcomes),
                         ["conflict", "saved"])
        winner = next(outcome for outcome in outcomes if outcome[1] == "saved")
        loser = next(outcome for outcome in outcomes if outcome[1] == "conflict")
        raw = (self.directory / "lab.yadilab").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), winner[2])
        self.assertEqual(loser[2], winner[2])
        self.assertEqual(json.loads(raw), changed(winner[0]))

    def test_two_store_instances_threads_share_one_project_lock(self):
        first, second = ProjectStore(self.directory), ProjectStore(self.directory)
        old = first.save("lab", example())["sha256"]
        at_replace = threading.Barrier(2)
        begin = threading.Barrier(3)
        real_replace = os.replace
        outcomes = []

        def aligned_replace(source, target):
            try:
                at_replace.wait(timeout=3)
            except threading.BrokenBarrierError:
                pass
            return real_replace(source, target)

        def writer(store, label):
            begin.wait()
            try:
                saved = store.save("lab", changed(label), old)
                outcomes.append((label, "saved", saved["sha256"]))
            except ProjectConflictError as error:
                outcomes.append((label, "conflict", error.actual_hash))

        with patch("network_core.storage.os.replace", side_effect=aligned_replace):
            threads = [threading.Thread(target=writer, args=(store, label))
                       for store, label in ((first, "first"), (second, "second"))]
            for thread in threads:
                thread.start()
            begin.wait()
            for thread in threads:
                thread.join(timeout=8)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assert_single_winner(outcomes)

    def run_process_race(self, expected):
        context = multiprocessing.get_context("spawn")
        start = context.Event()
        ready, results = context.Queue(), context.Queue()
        at_replace = context.Barrier(2)
        processes = [context.Process(target=process_save,
                                     args=(str(self.directory), label, expected,
                                           start, ready, at_replace, results))
                     for label in ("first", "second")]
        for process in processes:
            process.start()
        self.assertEqual({ready.get(timeout=8), ready.get(timeout=8)},
                         {"first", "second"})
        start.set()
        outcomes = [results.get(timeout=12), results.get(timeout=12)]
        for process in processes:
            process.join(timeout=8)
            self.assertEqual(process.exitcode, 0)
        self.assert_single_winner(outcomes)

    def test_separate_processes_conflict_on_old_hash(self):
        old = ProjectStore(self.directory).save("lab", example())["sha256"]
        self.run_process_race(old)

    def test_separate_processes_conflict_on_create_only(self):
        self.run_process_race(None)

    def test_failed_replace_preserves_file_and_releases_lock(self):
        first = ProjectStore(self.directory)
        old = first.save("lab", example())["sha256"]
        original = first.path("lab").read_bytes()
        with patch("network_core.storage.os.replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(OSError, "replace failed"):
                first.save("lab", changed("failed"), old)
        self.assertEqual(first.path("lab").read_bytes(), original)
        self.assertEqual(list(self.directory.glob(".pending-*")), [])
        second = ProjectStore(self.directory)
        saved = second.save("lab", changed("recovered"), old)
        self.assertEqual(second.read("lab")["sha256"], saved["sha256"])


class ConcurrentHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self.tmp.name)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.directory))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.tmp.cleanup()

    def test_competing_posts_return_one_success_one_conflict(self):
        old = self.server.store.save("lab", example())["sha256"]
        at_replace = threading.Barrier(2)
        begin = threading.Barrier(3)
        real_replace = os.replace
        outcomes = []

        def aligned_replace(source, target):
            try:
                at_replace.wait(timeout=3)
            except threading.BrokenBarrierError:
                pass
            return real_replace(source, target)

        def post(label):
            begin.wait()
            payload = json.dumps({"filename": "lab", "project": changed(label),
                                  "expectedSha256": old}).encode()
            request = Request(f"http://127.0.0.1:{self.server.server_port}/api/save",
                              data=payload, headers={"Content-Type": "application/json"})
            try:
                with urlopen(request, timeout=8) as response:
                    outcomes.append((label, response.status, json.loads(response.read())))
            except HTTPError as error:
                outcomes.append((label, error.code, json.loads(error.read())))

        with patch("network_core.storage.os.replace", side_effect=aligned_replace):
            threads = [threading.Thread(target=post, args=(label,))
                       for label in ("first", "second")]
            for thread in threads:
                thread.start()
            begin.wait()
            for thread in threads:
                thread.join(timeout=10)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(row[1] for row in outcomes), [200, 409])
        success = next(row for row in outcomes if row[1] == 200)
        conflict = next(row for row in outcomes if row[1] == 409)
        self.assertEqual(conflict[2]["error"], "CONFLICT")
        self.assertEqual(conflict[2]["currentSha256"], success[2]["sha256"])
        self.assertEqual(self.server.store.read("lab")["project"], changed(success[0]))
